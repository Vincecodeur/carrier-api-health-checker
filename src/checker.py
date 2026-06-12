# ============================================================================
# FICHIER : src/checker.py
# RESPONSABILITÉ : logique de health check HTTP
# MODIFICATION : retry automatique avec backoff exponentiel dans check_carrier()
# ============================================================================

import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def check_carrier(carrier, default_retries=2):
    """
    Envoie une requête HTTP à l'endpoint d'un transporteur et analyse la réponse.
    En cas d'échec, retente automatiquement avec un délai croissant (backoff).

    Paramètres :
        carrier (dict)        : dictionnaire du transporteur (issu de carriers.json)
        default_retries (int) : nombre de retries par défaut si non spécifié dans le carrier

    Retourne :
        dict : résultat du health check enrichi de 'attempts' et 'expected_status'
    """

    # ---- DÉTERMINER LE NOMBRE DE RETRIES ----
    #
    # Priorité : la valeur dans carriers.json > la valeur du CLI (default_retries)
    #
    # carrier.get("retries") retourne :
    #   - La valeur du JSON si la clé "retries" existe (ex: 3)
    #   - None si la clé n'existe pas
    #
    # Si None → on utilise default_retries (qui vient du CLI --retries)
    #
    # C'est un pattern courant : config spécifique > config globale > valeur par défaut
    max_retries = carrier.get("retries")
    if max_retries is None:
        max_retries = default_retries

    # Nombre total de tentatives = 1 (premier essai) + max_retries
    # Ex : max_retries=2 → 3 tentatives au total (1 initiale + 2 retries)
    max_attempts = max_retries + 1

    # ---- STRUCTURE DE RÉSULTAT ----
    result = {
        "name": carrier["name"],
        "url": carrier["url"],
        "status_code": None,
        "response_time_ms": None,
        "is_healthy": False,
        "error": None,
        "expected_status": carrier.get("expected_status", []),
        # NOUVEAU : nombre de tentatives effectuées
        # 1 = réussi du premier coup, 2 = 1 retry, 3 = 2 retries...
        "attempts": 0,
    }

    # ---- DÉLAI DE BACKOFF ----
    #
    # Le backoff_factor détermine la progression du délai entre les tentatives :
    #   Tentative 1 → échec → attente = 1.0 * 1 = 1.0s
    #   Tentative 2 → échec → attente = 1.0 * 2 = 2.0s
    #   Tentative 3 → échec → abandon
    #
    # Formule : delay = backoff_factor * attempt_number
    #
    # 1.0 seconde est un bon point de départ :
    #   - Assez long pour laisser le serveur se rétablir
    #   - Assez court pour ne pas ralentir excessivement le script
    backoff_factor = 1.0

    # ---- BOUCLE DE RETRY ----
    #
    # On utilise une boucle for avec range() au lieu d'un while True.
    # Avantage : pas de risque de boucle infinie, le nombre max est garanti.
    #
    # range(1, max_attempts + 1) produit : 1, 2, 3 (pour max_attempts=3)
    # 'attempt' est le numéro de la tentative courante (1-based, plus lisible dans les logs)
    for attempt in range(1, max_attempts + 1):

        result["attempts"] = attempt

        logger.debug(
            f"Attempt {attempt}/{max_attempts} for {carrier['name']} "
            f"— {carrier['url']} (timeout: {carrier.get('timeout', 10)}s)"
        )

        try:
            start = time.time()

            response = requests.get(
                carrier["url"],
                timeout=carrier.get("timeout", 10),
                headers={"User-Agent": "Anchanto-HealthChecker/1.0"}
            )

            elapsed_ms = round((time.time() - start) * 1000, 2)

            result["status_code"] = response.status_code
            result["response_time_ms"] = elapsed_ms
            result["is_healthy"] = response.status_code in carrier["expected_status"]
            result["error"] = None  # Reset de l'erreur en cas de succès après retry

            logger.debug(f"Response: HTTP {response.status_code} in {elapsed_ms} ms")

            # ---- SUCCÈS → ON SORT DE LA BOUCLE ----
            #
            # 'break' interrompt la boucle for immédiatement.
            # On ne retente PAS si la requête a abouti, même si le status code
            # est inattendu (ex: 404). Le retry ne concerne que les erreurs
            # RÉSEAU (timeout, connexion), pas les erreurs HTTP.
            #
            # Pourquoi ? Un serveur qui retourne 404 ou 500 est JOIGNABLE.
            # Le retenter ne changera rien — il retournera la même chose.
            # Le retry ne sert qu'à gérer l'instabilité RÉSEAU.
            break

        except requests.exceptions.Timeout:
            result["error"] = "TIMEOUT"
            logger.warning(
                f"Attempt {attempt}/{max_attempts} TIMEOUT for {carrier['name']} "
                f"(after {carrier.get('timeout', 10)}s)"
            )

        except requests.exceptions.ConnectionError:
            result["error"] = "CONNECTION_ERROR"
            logger.warning(
                f"Attempt {attempt}/{max_attempts} CONNECTION_ERROR for {carrier['name']}"
            )

        except requests.exceptions.RequestException as e:
            result["error"] = f"REQUEST_ERROR: {str(e)}"
            logger.warning(
                f"Attempt {attempt}/{max_attempts} error for {carrier['name']}: {e}"
            )

        # ---- FAUT-IL RETENTER ? ----
        #
        # On arrive ici SEULEMENT si une exception a été levée (le break n'a pas été atteint).
        #
        # Si c'est la dernière tentative → on ne retente pas, on log l'échec final.
        # Sinon → on attend avant de retenter (backoff).
        if attempt < max_attempts:
            # Calcul du délai : backoff_factor × numéro de tentative
            delay = backoff_factor * attempt
            logger.info(
                f"Retrying {carrier['name']} in {delay}s "
                f"(attempt {attempt + 1}/{max_attempts})..."
            )
            # time.sleep() met le thread courant en PAUSE pendant 'delay' secondes.
            # En mode parallèle, seul CE thread est en pause — les autres continuent.
            # C'est un avantage des threads : le sleep d'un carrier n'impacte pas les autres.
            time.sleep(delay)
        else:
            # Dernière tentative échouée → échec définitif
            logger.error(
                f"All {max_attempts} attempts failed for {carrier['name']} "
                f"— last error: {result['error']}"
            )

    return result


def run_health_checks(carriers, verbose=False, workers=5, default_retries=2):
    """
    Exécute le health check sur tous les transporteurs.

    Paramètres :
        carriers (list)         : liste de dicts transporteurs
        verbose (bool)          : mode détaillé
        workers (int)           : nombre de threads parallèles
        default_retries (int)   : nombre de retries par défaut

    Retourne :
        tuple : (results, total_time_ms)
    """

    logger.info(
        f"Starting health checks for {len(carriers)} carriers "
        f"(workers: {workers}, default retries: {default_retries})"
    )

    total_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:

        future_to_carrier = {}

        for carrier in carriers:
            # On passe default_retries à check_carrier() pour que chaque
            # carrier puisse utiliser soit sa valeur spécifique (JSON),
            # soit la valeur globale (CLI).
            future = executor.submit(check_carrier, carrier, default_retries)
            future_to_carrier[future] = carrier
            logger.debug(f"Submitted check for {carrier['name']}")

        for future in as_completed(future_to_carrier):

            carrier = future_to_carrier[future]

            try:
                result = future.result()
            except Exception as e:
                logger.error(f"Unexpected error checking {carrier['name']}: {e}")
                result = {
                    "name": carrier["name"],
                    "url": carrier["url"],
                    "status_code": None,
                    "response_time_ms": None,
                    "is_healthy": False,
                    "error": f"UNEXPECTED: {str(e)}",
                    "expected_status": carrier.get("expected_status", []),
                    "attempts": 0,
                }

            results.append(result)

            # Logging technique
            if result["error"]:
                pass  # Déjà loggé dans check_carrier()
            elif result["is_healthy"]:
                logger.info(f"  ✓ {carrier['name']} — HTTP {result['status_code']} in {result['response_time_ms']} ms")
            else:
                logger.warning(
                    f"  ✗ {carrier['name']} — HTTP {result['status_code']} "
                    f"(expected: {carrier['expected_status']})"
                )

            # Feedback temps réel (console)
            # NOUVEAU : on ajoute le nombre de tentatives si > 1
            attempts_info = f" [attempt {result['attempts']}]" if result["attempts"] > 1 else ""

            if result["error"]:
                print(f"  ✗ {carrier['name']} — {result['error']}{attempts_info}")
            elif result["is_healthy"]:
                print(f"  ✓ {carrier['name']} ({result['response_time_ms']} ms){attempts_info}")
            else:
                print(f"  ✗ {carrier['name']} — HTTP {result['status_code']} UNHEALTHY ({result['response_time_ms']} ms){attempts_info}")

    # Réordonner les résultats
    carrier_order = {c["name"]: i for i, c in enumerate(carriers)}
    results = sorted(results, key=lambda r: carrier_order.get(r["name"], 999))

    total_time_ms = round((time.time() - total_start) * 1000, 2)

    healthy = sum(1 for r in results if r["is_healthy"])
    logger.info(f"Health checks complete: {healthy}/{len(results)} carriers healthy in {total_time_ms} ms")

    return results, total_time_ms