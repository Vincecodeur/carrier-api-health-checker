# ============================================================================
# FICHIER : src/checker.py
# RESPONSABILITÉ : logique de health check HTTP
# MODIFICATION : verbose simplifié — une seule ligne courte par check
# ============================================================================

import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def check_carrier(carrier):
    """
    Envoie une requête HTTP à l'endpoint d'un transporteur et analyse la réponse.
    (Inchangé)
    """

    result = {
        "name": carrier["name"],
        "url": carrier["url"],
        "status_code": None,
        "response_time_ms": None,
        "is_healthy": False,
        "error": None,
        "expected_status": carrier.get("expected_status", []),
    }

    logger.debug(f"Sending GET request to {carrier['url']} (timeout: {carrier.get('timeout', 10)}s)")

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

        logger.debug(f"Response: HTTP {response.status_code} in {elapsed_ms} ms")

    except requests.exceptions.Timeout:
        result["error"] = "TIMEOUT"
        logger.error(f"Timeout after {carrier.get('timeout', 10)}s — {carrier['url']}")

    except requests.exceptions.ConnectionError:
        result["error"] = "CONNECTION_ERROR"
        logger.error(f"Connection failed — {carrier['url']}")

    except requests.exceptions.RequestException as e:
        result["error"] = f"REQUEST_ERROR: {str(e)}"
        logger.error(f"Request error for {carrier['url']}: {e}")

    return result


def run_health_checks(carriers, verbose=False, workers=5):
    """
    Exécute le health check sur tous les transporteurs.

    Paramètres :
        carriers (list)  : liste de dicts transporteurs
        verbose (bool)   : mode détaillé
        workers (int)    : nombre de threads parallèles

    Retourne :
        tuple : (results, total_time_ms)
    """

    logger.info(f"Starting health checks for {len(carriers)} carriers (workers: {workers})")

    total_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:

        future_to_carrier = {}

        for carrier in carriers:
            future = executor.submit(check_carrier, carrier)
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
                }

            results.append(result)

            # ---- LOGGING (technique, vers le fichier de log) ----
            # Inchangé : les logs techniques restent détaillés
            if result["error"]:
                pass
            elif result["is_healthy"]:
                logger.info(f"  ✓ {carrier['name']} — HTTP {result['status_code']} in {result['response_time_ms']} ms")
            else:
                logger.warning(
                    f"  ✗ {carrier['name']} — HTTP {result['status_code']} "
                    f"(expected: {carrier['expected_status']})"
                )

            # ---- AFFICHAGE TEMPS RÉEL (console uniquement) ----
            #
            # AVANT : 5-6 lignes détaillées par carrier (URL, expected, verdict...)
            # APRÈS : UNE seule ligne courte par carrier
            #
            # Rôle : donner un feedback immédiat à l'utilisateur pendant les checks.
            # Le détail complet sera dans le dashboard (display.py), trié dans l'ordre config.
            #
            # On affiche toujours cette ligne, que verbose soit True ou False.
            # La différence :
            #   - Normal : juste le nom + résultat
            #   - Verbose : idem (le détail verbose est maintenant dans le dashboard)
            #
            # L'icône donne l'info essentielle en un coup d'œil :
            #   ✓ = check réussi (healthy)
            #   ✗ = check réussi mais status inattendu (unhealthy)
            #   ✗ = erreur réseau (timeout, connexion...)
            if result["error"]:
                print(f"  ✗ {carrier['name']} — {result['error']}")
            elif result["is_healthy"]:
                print(f"  ✓ {carrier['name']} ({result['response_time_ms']} ms)")
            else:
                print(f"  ✗ {carrier['name']} — HTTP {result['status_code']} UNHEALTHY ({result['response_time_ms']} ms)")

    # Réordonner les résultats dans l'ordre de la config
    carrier_order = {c["name"]: i for i, c in enumerate(carriers)}
    results = sorted(results, key=lambda r: carrier_order.get(r["name"], 999))

    total_time_ms = round((time.time() - total_start) * 1000, 2)

    healthy = sum(1 for r in results if r["is_healthy"])
    logger.info(f"Health checks complete: {healthy}/{len(results)} carriers healthy in {total_time_ms} ms")

    return results, total_time_ms