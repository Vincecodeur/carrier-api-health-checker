# ============================================================================
# FICHIER : tests/conftest.py
# RESPONSABILITÉ : fixtures partagées entre tous les fichiers de test
#
# conftest.py est un fichier SPÉCIAL reconnu automatiquement par pytest.
# Les fixtures définies ici sont disponibles dans TOUS les fichiers test_*.py
# du même dossier — sans avoir besoin de les importer.
#
# FIXTURE = une fonction qui prépare des données de test réutilisables.
# C'est l'équivalent d'un "setup" avant chaque test.
# ============================================================================

import pytest


@pytest.fixture
def sample_carrier():
    """
    Retourne un carrier de test standard.

    @pytest.fixture est un DÉCORATEUR — une fonction qui modifie
    le comportement d'une autre fonction.

    Quand une fonction de test déclare 'sample_carrier' comme paramètre,
    pytest appelle automatiquement cette fixture et injecte sa valeur
    de retour dans le paramètre. C'est de l'INJECTION DE DÉPENDANCES.

    Exemple d'utilisation dans un test :
        def test_something(sample_carrier):
            # sample_carrier contient le dict retourné ci-dessous
            assert sample_carrier["name"] == "Test Carrier"
    """
    return {
        "name": "Test Carrier",
        "url": "https://api.example.com/health",
        "method": "GET",
        "expected_status": [200, 401],
        "timeout": 5,
        "retries": 2,
        "max_latency_ms": 500,
    }


@pytest.fixture
def sample_carrier_minimal():
    """
    Carrier avec le minimum de champs requis (pas de retries, pas de max_latency_ms).
    Teste que le code gère correctement les champs optionnels absents.
    """
    return {
        "name": "Minimal Carrier",
        "url": "https://api.example.com/ping",
        "method": "GET",
        "expected_status": [200],
        "timeout": 10,
    }


@pytest.fixture
def sample_result_healthy():
    """
    Résultat de health check simulé — carrier healthy.
    Utilisé pour tester display.py et export.py sans avoir
    besoin de faire un vrai appel HTTP.
    """
    return {
        "name": "Test Carrier",
        "url": "https://api.example.com/health",
        "status_code": 200,
        "response_time_ms": 150.0,
        "is_healthy": True,
        "error": None,
        "expected_status": [200, 401],
        "attempts": 1,
        "max_latency_ms": 500,
        "latency_warning": False,
    }


@pytest.fixture
def sample_result_unhealthy():
    """
    Résultat simulé — carrier unhealthy (status code inattendu).
    """
    return {
        "name": "Unhealthy Carrier",
        "url": "https://api.example.com/health",
        "status_code": 404,
        "response_time_ms": 80.0,
        "is_healthy": False,
        "error": None,
        "expected_status": [200],
        "attempts": 1,
        "max_latency_ms": 300,
        "latency_warning": False,
    }


@pytest.fixture
def sample_result_error():
    """
    Résultat simulé — erreur réseau (timeout après retries).
    """
    return {
        "name": "Error Carrier",
        "url": "https://api.example.com/health",
        "status_code": None,
        "response_time_ms": None,
        "is_healthy": False,
        "error": "TIMEOUT",
        "expected_status": [200],
        "attempts": 3,
        "max_latency_ms": 300,
        "latency_warning": False,
    }


@pytest.fixture
def sample_result_slow():
    """
    Résultat simulé — carrier healthy mais latence trop élevée.
    """
    return {
        "name": "Slow Carrier",
        "url": "https://api.example.com/health",
        "status_code": 200,
        "response_time_ms": 650.0,
        "is_healthy": True,
        "error": None,
        "expected_status": [200],
        "attempts": 1,
        "max_latency_ms": 500,
        "latency_warning": True,
    }


@pytest.fixture
def sample_carriers_list(sample_carrier):
    """
    Liste de 3 carriers pour tester run_health_checks().
    Utilise la fixture sample_carrier comme base et crée des variations.

    Note : une fixture PEUT utiliser d'autres fixtures en les déclarant
    comme paramètre — pytest gère la chaîne d'injection automatiquement.
    """
    return [
        sample_carrier,
        {
            "name": "Second Carrier",
            "url": "https://api.second.com/health",
            "method": "GET",
            "expected_status": [200],
            "timeout": 5,
        },
        {
            "name": "Third Carrier",
            "url": "https://api.third.com/health",
            "method": "GET",
            "expected_status": [200, 401, 403],
            "timeout": 5,
        },
    ]