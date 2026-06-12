# ============================================================================
# FICHIER : src/checker.py
# RESPONSABILITÉ : logique de health check HTTP
# MODIFICATION : ajout du seuil de latence (max_latency_ms) et latency_warning
# ============================================================================

import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def check_carrier(carrier, default_retries=2, default_max_latency=0):
    """
    Envoie une requête HTTP à l'endpoint d'un transporteur et analyse la réponse.
    En cas d'échec, retente automatiquement avec un délai croissant (backoff).

    Paramètres :
        carrier (dict)            : dictionnaire du transporteur
        default_retries (int)     : nombre de retries par défaut
        default_max_latency (int) : seuil de latence par défaut en ms (0 = désactivé)

    Retourne :
        dict : résultat du health check
    """

    # Retries (inchangé)
    max_retries = carrier.get("retries")
    if max_retries is None:
        max_retries = default_retries
    max_attempts = max_retries + 1

    # ---- SEUIL DE LATENCE ----
    # Même pattern que retries : JSON spécifique > CLI global > défaut (0)
    # 0 signifie "pas de seuil" → latency_warning sera toujours False
    max_latency_ms = carrier.get("max_latency_ms")
    if max_latency_ms is None:
        max_latency_ms = default_max_latency

    result = {
        "name": carrier["name"],
        "url": carrier["url"],
        "status_code": None,
        "response_time_ms": None,
        "is_healthy": False,
        "error": None,
        "expected_status": carrier.get("expected_status", []),
        "attempts": 0,
        # NOUVEAU : seuil de latence configuré pour ce carrier
        # Stocké dans le result pour que display.py puisse l'afficher
        "max_latency_ms": max_latency_ms,
        # NOUVEAU : True si la latence dépasse le seuil
        # Initialisé à False, mis à jour après la requête
        "latency_warning": False,
    }

    backoff_factor = 1.0

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
            result["error"] = None

            # ---- ÉVALUATION DU SEUIL DE LATENCE ----
            # On vérifie UNIQUEMENT si :
            #   1. Un seuil est défini (max_latency_ms > 0)
            #   2. La latence mesurée dépasse ce seuil
            #
            # Le latency_warning est INDÉPENDANT de is_healthy :
            #   - is_healthy = le serveur répond-il correctement ? (status code)
            #   - latency_warning = le serveur répond-il assez vite ? (performance)
            #
            # Un carrier peut être healthy ET en latency_warning.
            if max_latency_ms > 0 and elapsed_ms > max_latency_ms:
                result["latency_warning"] = True
                logger.warning(
                    f"Latency warning for {carrier['name']}: "
                    f"{elapsed_ms} ms > {max_latency_ms} ms threshold"
                )
            else:
                result["latency_warning"] = False

            logger.debug(f"Response: HTTP {response.status_code} in {elapsed_ms} ms")
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

        if attempt < max_attempts:
            delay = backoff_factor * attempt
            logger.info(
                f"Retrying {carrier['name']} in {delay}s "
                f"(attempt {attempt + 1}/{max_attempts})..."
            )
            time.sleep(delay)
        else:
            logger.error(
                f"All {max_attempts} attempts failed for {carrier['name']} "
                f"— last error: {result['error']}"
            )

    return result


def run_health_checks(carriers, verbose=False, workers=5, default_retries=2, default_max_latency=0):
    """
    Exécute le health check sur tous les transporteurs.

    Paramètres :
        carriers (list)            : liste de dicts transporteurs
        verbose (bool)             : mode détaillé
        workers (int)              : nombre de threads parallèles
        default_retries (int)      : nombre de retries par défaut
        default_max_latency (int)  : seuil de latence par défaut en ms
    """

    logger.info(
        f"Starting health checks for {len(carriers)} carriers "
        f"(workers: {workers}, default retries: {default_retries}, "
        f"default max latency: {default_max_latency} ms)"
    )

    total_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:

        future_to_carrier = {}

        for carrier in carriers:
            # On passe default_max_latency à check_carrier()
            future = executor.submit(check_carrier, carrier, default_retries, default_max_latency)
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
                    "max_latency_ms": 0,
                    "latency_warning": False,
                }

            results.append(result)

            # Logging technique
            if result["error"]:
                pass
            elif result["is_healthy"]:
                logger.info(f"  ✓ {carrier['name']} — HTTP {result['status_code']} in {result['response_time_ms']} ms")
            else:
                logger.warning(
                    f"  ✗ {carrier['name']} — HTTP {result['status_code']} "
                    f"(expected: {carrier['expected_status']})"
                )

            # Feedback temps réel
            attempts_info = f" [attempt {result['attempts']}]" if result["attempts"] > 1 else ""
            # NOUVEAU : indicateur de latence dans le feedback temps réel
            latency_flag = " ⚠️ SLOW" if result["latency_warning"] else ""

            if result["error"]:
                print(f"  ✗ {carrier['name']} — {result['error']}{attempts_info}")
            elif result["is_healthy"]:
                print(f"  ✓ {carrier['name']} ({result['response_time_ms']} ms){latency_flag}{attempts_info}")
            else:
                print(f"  ✗ {carrier['name']} — HTTP {result['status_code']} UNHEALTHY ({result['response_time_ms']} ms){attempts_info}")

    # Réordonner les résultats
    carrier_order = {c["name"]: i for i, c in enumerate(carriers)}
    results = sorted(results, key=lambda r: carrier_order.get(r["name"], 999))

    total_time_ms = round((time.time() - total_start) * 1000, 2)

    healthy = sum(1 for r in results if r["is_healthy"])
    logger.info(f"Health checks complete: {healthy}/{len(results)} carriers healthy in {total_time_ms} ms")

    return results, total_time_ms