# ============================================================================
# FICHIER : src/checker.py
# RESPONSABILITÉ : logique de health check HTTP
# MODIFICATION : logging remplace print() — les niveaux reflètent la sévérité
# ============================================================================

import requests
import time
import logging

# Logger spécifique à ce module → %(name)s affichera "src.checker"
logger = logging.getLogger(__name__)


def check_carrier(carrier):
    """
    Envoie une requête HTTP à l'endpoint d'un transporteur et analyse la réponse.
    """

    result = {
        "name": carrier["name"],
        "url": carrier["url"],
        "status_code": None,
        "response_time_ms": None,
        "is_healthy": False,
        "error": None,
    }

    # DEBUG : détail technique visible uniquement en mode --log-level DEBUG
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

        # DEBUG : détail de la réponse (visible uniquement en DEBUG)
        logger.debug(f"Response: HTTP {response.status_code} in {elapsed_ms} ms")

    except requests.exceptions.Timeout:
        result["error"] = "TIMEOUT"
        # ERROR : un timeout est une erreur opérationnelle significative
        logger.error(f"Timeout after {carrier.get('timeout', 10)}s — {carrier['url']}")

    except requests.exceptions.ConnectionError:
        result["error"] = "CONNECTION_ERROR"
        # ERROR : impossible de se connecter au serveur
        logger.error(f"Connection failed — {carrier['url']}")

    except requests.exceptions.RequestException as e:
        result["error"] = f"REQUEST_ERROR: {str(e)}"
        # ERROR : erreur HTTP inattendue
        logger.error(f"Request error for {carrier['url']}: {e}")

    return result


def run_health_checks(carriers, verbose=False):
    """
    Exécute le health check sur tous les transporteurs de la liste.
    """

    # INFO : événement normal attendu (début d'opération)
    logger.info(f"Starting health checks for {len(carriers)} carriers")

    results = []

    for carrier in carriers:
        # INFO remplace print() — le message est envoyé au terminal ET au fichier de log
        logger.info(f"Checking {carrier['name']}...")

        if verbose:
            # Les détails verbose restent en print() car c'est de l'affichage utilisateur,
            # pas du logging technique. On pourrait aussi les mettre en logger.debug(),
            # mais le mode --verbose est pensé pour l'affichage console, pas pour les logs.
            print(f"     → URL: {carrier['url']}")
            print(f"     → Method: {carrier.get('method', 'GET')}")
            print(f"     → Timeout: {carrier.get('timeout', 10)}s")
            print(f"     → Expected status codes: {carrier['expected_status']}")

        result = check_carrier(carrier)

        # ---- LOG CONDITIONNEL SELON LE RÉSULTAT ----
        # On utilise le BON NIVEAU de log selon la situation :
        #   - Healthy → INFO (tout va bien)
        #   - Unhealthy (status code inattendu) → WARNING (pas une erreur réseau, mais anormal)
        #   - Error (timeout, connexion...) → déjà loggé en ERROR dans check_carrier()
        if result["error"]:
            pass  # Déjà loggé dans check_carrier()
        elif result["is_healthy"]:
            logger.info(f"  ✓ {carrier['name']} — HTTP {result['status_code']} in {result['response_time_ms']} ms")
        else:
            # WARNING : le serveur répond mais avec un code inattendu
            logger.warning(
                f"  ✗ {carrier['name']} — HTTP {result['status_code']} "
                f"(expected: {carrier['expected_status']})"
            )

        if verbose:
            if result["error"]:
                print(f"     ← Error: {result['error']}")
            else:
                print(f"     ← Response: HTTP {result['status_code']} in {result['response_time_ms']} ms")
                if result["is_healthy"]:
                    print(f"     ← Verdict: HEALTHY ({result['status_code']} ∈ {carrier['expected_status']})")
                else:
                    print(f"     ← Verdict: UNHEALTHY ({result['status_code']} ∉ {carrier['expected_status']})")

        results.append(result)

    # INFO : résumé de fin d'opération
    healthy = sum(1 for r in results if r["is_healthy"])
    logger.info(f"Health checks complete: {healthy}/{len(results)} carriers healthy")

    return results