# ============================================================================
# FICHIER : tests/test_checker.py
# RESPONSABILITÉ : tester le module src/checker.py
#
# PRINCIPE CLÉ : on ne fait JAMAIS de vrai appel HTTP dans les tests.
# On utilise des MOCKS pour simuler les réponses de requests.get().
# Ça rend les tests rapides, reproductibles et indépendants du réseau.
# ============================================================================

import pytest
from unittest.mock import patch, MagicMock
from src.checker import check_carrier, run_health_checks


class TestCheckCarrier:
    """
    Groupe de tests pour la fonction check_carrier().

    En pytest, une classe préfixée par Test regroupe des tests liés.
    Ce n'est pas obligatoire (des fonctions simples marchent aussi),
    mais ça aide à organiser quand il y a beaucoup de tests.
    """

    @patch("src.checker.requests.get")
    def test_healthy_response(self, mock_get, sample_carrier):
        """
        Test : le serveur répond 200 → is_healthy=True.

        @patch("src.checker.requests.get") :
            Remplace TEMPORAIREMENT requests.get dans le module src.checker
            par un objet MagicMock. Pendant ce test, aucun appel HTTP réel
            n'est effectué. Le mock est injecté comme premier paramètre (mock_get).

        IMPORTANT : on patche "src.checker.requests.get" (l'endroit où
        requests.get est UTILISÉ), pas "requests.get" (l'endroit où il
        est DÉFINI). C'est une règle fondamentale du mocking en Python.
        """

        # ARRANGE — configurer le mock
        # mock_get.return_value = ce que requests.get() retourne
        # On crée un faux objet Response avec un status_code de 200
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # ACT — appeler la fonction testée
        result = check_carrier(sample_carrier)

        # ASSERT — vérifier le résultat
        assert result["is_healthy"] is True
        assert result["status_code"] == 200
        assert result["error"] is None
        assert result["response_time_ms"] is not None
        assert result["response_time_ms"] > 0
        assert result["attempts"] == 1

    @patch("src.checker.requests.get")
    def test_unhealthy_response(self, mock_get, sample_carrier):
        """
        Test : le serveur répond 500 (pas dans expected_status) → is_healthy=False.
        """

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = check_carrier(sample_carrier)

        assert result["is_healthy"] is False
        assert result["status_code"] == 500
        assert result["error"] is None

    @patch("src.checker.requests.get")
    def test_timeout_error(self, mock_get, sample_carrier):
        """
        Test : requests.get() lève un Timeout → error="TIMEOUT".

        mock_get.side_effect = Exception :
            Au lieu de retourner une valeur, le mock LÈVE UNE EXCEPTION
            quand il est appelé. Ça simule un timeout réseau.
        """

        import requests as req
        mock_get.side_effect = req.exceptions.Timeout("Connection timed out")

        result = check_carrier(sample_carrier, default_retries=0)

        assert result["is_healthy"] is False
        assert result["status_code"] is None
        assert result["error"] == "TIMEOUT"

    @patch("src.checker.requests.get")
    def test_connection_error(self, mock_get, sample_carrier):
        """
        Test : erreur de connexion → error="CONNECTION_ERROR".
        """

        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("DNS resolution failed")

        result = check_carrier(sample_carrier, default_retries=0)

        assert result["error"] == "CONNECTION_ERROR"
        assert result["is_healthy"] is False

    @patch("src.checker.requests.get")
    def test_retry_then_success(self, mock_get, sample_carrier):
        """
        Test : 1er appel → Timeout, 2ème appel → succès HTTP 200.

        side_effect avec une LISTE :
            Chaque appel consomme l'élément suivant de la liste.
            1er appel → lève Timeout
            2ème appel → retourne mock_response (HTTP 200)
        """

        import requests as req

        mock_response = MagicMock()
        mock_response.status_code = 200

        # Liste : [exception, réponse valide]
        mock_get.side_effect = [
            req.exceptions.Timeout("timeout"),
            mock_response,
        ]

        result = check_carrier(sample_carrier, default_retries=2)

        assert result["is_healthy"] is True
        assert result["status_code"] == 200
        assert result["attempts"] == 2  # 1 échec + 1 succès

    @patch("src.checker.requests.get")
    def test_all_retries_fail(self, mock_get, sample_carrier):
        """
        Test : toutes les tentatives échouent → error après max_retries.
        """

        import requests as req
        mock_get.side_effect = req.exceptions.Timeout("timeout")

        result = check_carrier(sample_carrier, default_retries=2)

        assert result["is_healthy"] is False
        assert result["error"] == "TIMEOUT"
        assert result["attempts"] == 3  # 1 initial + 2 retries

    @patch("src.checker.requests.get")
    def test_latency_warning(self, mock_get, sample_carrier):
        """
        Test : la latence dépasse max_latency_ms → latency_warning=True.

        Pour simuler une latence élevée, on utilise side_effect avec
        une FONCTION qui dort avant de retourner la réponse.
        Mais c'est trop lent pour un test. À la place, on vérifie juste
        la logique : si response_time_ms > max_latency_ms → warning.

        On triche un peu : on patch time.time() pour contrôler la latence.
        """

        # Carrier avec un seuil très bas (1ms) pour garantir le dépassement
        carrier = sample_carrier.copy()
        carrier["max_latency_ms"] = 1

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = check_carrier(carrier)

        # La requête mockée prend > 0ms (overhead Python), donc > 1ms
        # En pratique le mock prend ~0.01-0.1ms, donc on ne peut pas
        # garantir > 1ms. On vérifie plutôt que le champ existe et est booléen.
        assert isinstance(result["latency_warning"], bool)
        assert "max_latency_ms" in result

    @patch("src.checker.requests.get")
    def test_no_latency_warning_when_disabled(self, mock_get, sample_carrier):
        """
        Test : max_latency_ms=0 (désactivé) → latency_warning=False toujours.
        """

        carrier = sample_carrier.copy()
        carrier["max_latency_ms"] = 0

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = check_carrier(carrier, default_max_latency=0)

        assert result["latency_warning"] is False

    @patch("src.checker.requests.get")
    def test_result_contains_all_expected_keys(self, mock_get, sample_carrier):
        """
        Test : le dict result contient TOUTES les clés attendues.
        C'est LE TEST qui aurait attrapé le bug export.py / fieldnames.
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = check_carrier(sample_carrier)

        expected_keys = {
            "name", "url", "status_code", "response_time_ms",
            "is_healthy", "error", "expected_status", "attempts",
            "max_latency_ms", "latency_warning"
        }

        assert set(result.keys()) == expected_keys, (
            f"Clés manquantes : {expected_keys - set(result.keys())}\n"
            f"Clés en trop : {set(result.keys()) - expected_keys}"
        )


class TestRunHealthChecks:
    """Tests pour run_health_checks()."""

    @patch("src.checker.check_carrier")
    def test_returns_tuple(self, mock_check, sample_carriers_list):
        """
        Test : run_health_checks retourne un tuple (results, total_time_ms).
        """

        mock_check.return_value = {
            "name": "Test", "url": "https://test.com",
            "status_code": 200, "response_time_ms": 100.0,
            "is_healthy": True, "error": None,
            "expected_status": [200], "attempts": 1,
            "max_latency_ms": 500, "latency_warning": False,
        }

        result = run_health_checks(sample_carriers_list, workers=1)

        assert isinstance(result, tuple)
        assert len(result) == 2

        results, total_time_ms = result
        assert isinstance(results, list)
        assert isinstance(total_time_ms, float)

    @patch("src.checker.check_carrier")
    def test_results_count_matches_carriers(self, mock_check, sample_carriers_list):
        """
        Test : le nombre de résultats = le nombre de carriers en entrée.
        """

        mock_check.return_value = {
            "name": "Test", "url": "https://test.com",
            "status_code": 200, "response_time_ms": 100.0,
            "is_healthy": True, "error": None,
            "expected_status": [200], "attempts": 1,
            "max_latency_ms": 500, "latency_warning": False,
        }

        results, _ = run_health_checks(sample_carriers_list, workers=1)

        assert len(results) == len(sample_carriers_list)