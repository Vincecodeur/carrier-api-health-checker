# ============================================================================
# FICHIER : tests/test_checker.py
# RESPONSABILITÉ : tester le module src/checker.py
# VERSION : mise à jour avec 6 tests supplémentaires pour couverture complète
# ============================================================================

from unittest.mock import MagicMock, patch

from src.checker import check_carrier, run_health_checks


class TestCheckCarrier:
    """Tests pour la fonction check_carrier()."""

    # ------------------------------------------------------------------
    # Tests existants (inchangés)
    # ------------------------------------------------------------------

    @patch("src.checker.requests.get")
    def test_healthy_response(self, mock_get, sample_carrier):
        """Le serveur répond 200 → is_healthy=True."""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = check_carrier(sample_carrier)

        assert result["is_healthy"] is True
        assert result["status_code"] == 200
        assert result["error"] is None
        assert result["response_time_ms"] is not None
        assert result["response_time_ms"] > 0
        assert result["attempts"] == 1

    @patch("src.checker.requests.get")
    def test_unhealthy_response(self, mock_get, sample_carrier):
        """Le serveur répond 500 (pas dans expected_status) → is_healthy=False."""

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = check_carrier(sample_carrier)

        assert result["is_healthy"] is False
        assert result["status_code"] == 500
        assert result["error"] is None

    @patch("src.checker.requests.get")
    def test_timeout_error(self, mock_get, sample_carrier):
        """Timeout réseau → error='TIMEOUT'."""

        import requests as req

        mock_get.side_effect = req.exceptions.Timeout("Connection timed out")

        result = check_carrier(sample_carrier, default_retries=0)

        assert result["is_healthy"] is False
        assert result["status_code"] is None
        assert result["error"] == "TIMEOUT"

    @patch("src.checker.requests.get")
    def test_connection_error(self, mock_get, sample_carrier):
        """Erreur de connexion → error='CONNECTION_ERROR'."""

        import requests as req

        mock_get.side_effect = req.exceptions.ConnectionError("DNS resolution failed")

        result = check_carrier(sample_carrier, default_retries=0)

        assert result["error"] == "CONNECTION_ERROR"
        assert result["is_healthy"] is False

    @patch("src.checker.requests.get")
    def test_retry_then_success(self, mock_get, sample_carrier):
        """1er appel → Timeout, 2ème appel → succès HTTP 200."""

        import requests as req

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_get.side_effect = [
            req.exceptions.Timeout("timeout"),
            mock_response,
        ]

        result = check_carrier(sample_carrier, default_retries=2)

        assert result["is_healthy"] is True
        assert result["status_code"] == 200
        assert result["attempts"] == 2

    @patch("src.checker.requests.get")
    def test_all_retries_fail(self, mock_get, sample_carrier):
        """Toutes les tentatives échouent → error après max_retries."""

        import requests as req

        mock_get.side_effect = req.exceptions.Timeout("timeout")

        result = check_carrier(sample_carrier, default_retries=2)

        assert result["is_healthy"] is False
        assert result["error"] == "TIMEOUT"
        assert result["attempts"] == 3

    @patch("src.checker.requests.get")
    def test_latency_warning(self, mock_get, sample_carrier):
        """Le champ latency_warning existe et est booléen."""

        carrier = sample_carrier.copy()
        carrier["max_latency_ms"] = 1

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = check_carrier(carrier)

        assert isinstance(result["latency_warning"], bool)
        assert "max_latency_ms" in result

    @patch("src.checker.requests.get")
    def test_no_latency_warning_when_disabled(self, mock_get, sample_carrier):
        """max_latency_ms=0 → latency_warning=False toujours."""

        carrier = sample_carrier.copy()
        carrier["max_latency_ms"] = 0

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = check_carrier(carrier, default_max_latency=0)

        assert result["latency_warning"] is False

    @patch("src.checker.requests.get")
    def test_result_contains_all_expected_keys(self, mock_get, sample_carrier):
        """Le dict result contient TOUTES les clés attendues."""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = check_carrier(sample_carrier)

        expected_keys = {
            "name",
            "url",
            "status_code",
            "response_time_ms",
            "is_healthy",
            "error",
            "expected_status",
            "attempts",
            "max_latency_ms",
            "latency_warning",
        }

        assert set(result.keys()) == expected_keys, (
            f"Clés manquantes : {expected_keys - set(result.keys())}\n"
            f"Clés en trop : {set(result.keys()) - expected_keys}"
        )

    # ------------------------------------------------------------------
    # NOUVEAU — Zone 1 : RequestException générique
    # ------------------------------------------------------------------

    @patch("src.checker.requests.get")
    def test_generic_request_exception(self, mock_get, sample_carrier):
        """
        Zone 1 — RequestException générique → error='REQUEST_ERROR: ...'.

        On a testé Timeout et ConnectionError. Mais requests peut aussi
        lever d'autres exceptions (TooManyRedirects, ChunkedEncodingError...).
        Elles héritent toutes de RequestException.

        Ce test vérifie que le troisième bloc except (le filet de sécurité)
        fonctionne correctement.
        """

        import requests as req

        # side_effect avec une RequestException générique
        # (pas Timeout, pas ConnectionError — la classe parente directe)
        mock_get.side_effect = req.exceptions.RequestException("Something weird happened")

        result = check_carrier(sample_carrier, default_retries=0)

        # Le error doit commencer par "REQUEST_ERROR:" suivi du message
        assert result["error"] is not None
        assert result["error"].startswith("REQUEST_ERROR:")
        assert "Something weird happened" in result["error"]
        assert result["is_healthy"] is False
        assert result["status_code"] is None

    # ------------------------------------------------------------------
    # NOUVEAU — Zone 2 : Latency warning déterministe (patch time.time)
    # ------------------------------------------------------------------

    @patch("src.checker.requests.get")
    @patch("src.checker.time.time")
    def test_latency_warning_deterministic(self, mock_time, mock_get, sample_carrier):
        """
        Zone 2 — Latency warning avec temps contrôlé.

        Le problème du test précédent (test_latency_warning) : le mock
        requests.get() retourne quasi instantanément (~0.001ms), donc
        la latence mesurée est souvent inférieure au seuil de 1ms.
        Le test n'est pas déterministe.

        Solution : patcher time.time() pour contrôler le temps.

        time.time() est appelé 2 fois dans check_carrier() :
          1. start = time.time()      → on retourne 1000.0
          2. end = time.time()        → on retourne 1001.0
          → elapsed = 1001.0 - 1000.0 = 1.0 seconde = 1000ms

        Avec un seuil de 500ms, 1000ms > 500ms → latency_warning = True.

        IMPORTANT : quand on empile deux @patch, l'ordre des paramètres
        est INVERSÉ par rapport à l'ordre des décorateurs :
          @patch("src.checker.requests.get")     ← 2ème paramètre (mock_get)
          @patch("src.checker.time.time")        ← 1er paramètre (mock_time)
        C'est une convention Python : le décorateur le plus proche de def
        est injecté en premier.
        """

        # Configurer time.time() pour retourner des valeurs séquentielles
        # 1er appel (start) → 1000.0
        # 2ème appel (end) → 1001.0
        # Différence = 1.0 seconde = 1000ms
        mock_time.side_effect = [1000.0, 1001.0] + [1001.0] * 10

        # Configurer le mock HTTP
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Carrier avec un seuil de 500ms
        carrier = sample_carrier.copy()
        carrier["max_latency_ms"] = 500

        result = check_carrier(carrier, default_retries=0)

        # Vérifications
        assert result["is_healthy"] is True  # Status code OK
        assert result["latency_warning"] is True  # 1000ms > 500ms
        assert result["response_time_ms"] == 1000.0  # Exactement 1 seconde
        assert result["max_latency_ms"] == 500

    @patch("src.checker.requests.get")
    @patch("src.checker.time.time")
    def test_no_latency_warning_under_threshold(self, mock_time, mock_get, sample_carrier):
        """
        Contre-test de la zone 2 : latence SOUS le seuil → pas de warning.

        time.time() retourne 1000.0 puis 1000.1 → 100ms.
        Seuil = 500ms → 100ms < 500ms → latency_warning = False.
        """

        mock_time.side_effect = [1000.0, 1000.1] + [1000.1] * 10  # 100ms

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        carrier = sample_carrier.copy()
        carrier["max_latency_ms"] = 500

        result = check_carrier(carrier, default_retries=0)

        assert result["latency_warning"] is False
        assert result["response_time_ms"] == 100.0


class TestRunHealthChecks:
    """Tests pour run_health_checks()."""

    # ------------------------------------------------------------------
    # Tests existants (inchangés)
    # ------------------------------------------------------------------

    @patch("src.checker.check_carrier")
    def test_returns_tuple(self, mock_check, sample_carriers_list):
        """run_health_checks retourne un tuple (results, total_time_ms)."""

        mock_check.return_value = {
            "name": "Test",
            "url": "https://test.com",
            "status_code": 200,
            "response_time_ms": 100.0,
            "is_healthy": True,
            "error": None,
            "expected_status": [200],
            "attempts": 1,
            "max_latency_ms": 500,
            "latency_warning": False,
        }

        result = run_health_checks(sample_carriers_list, workers=1)

        assert isinstance(result, tuple)
        assert len(result) == 2

        results, total_time_ms = result
        assert isinstance(results, list)
        assert isinstance(total_time_ms, float)

    @patch("src.checker.check_carrier")
    def test_results_count_matches_carriers(self, mock_check, sample_carriers_list):
        """Le nombre de résultats = le nombre de carriers en entrée."""

        mock_check.return_value = {
            "name": "Test",
            "url": "https://test.com",
            "status_code": 200,
            "response_time_ms": 100.0,
            "is_healthy": True,
            "error": None,
            "expected_status": [200],
            "attempts": 1,
            "max_latency_ms": 500,
            "latency_warning": False,
        }

        results, _ = run_health_checks(sample_carriers_list, workers=1)

        assert len(results) == len(sample_carriers_list)

    # ------------------------------------------------------------------
    # NOUVEAU — Zone 3 : branche unhealthy dans run_health_checks()
    # ------------------------------------------------------------------

    @patch("src.checker.check_carrier")
    def test_unhealthy_result_logged(self, mock_check, sample_carriers_list):
        """
        Zone 3 — run_health_checks() gère les résultats unhealthy.

        Le mock retourne un résultat avec is_healthy=False et error=None.
        Ça déclenche la branche logger.warning() dans la boucle as_completed().

        On vérifie que :
          - La fonction ne crashe pas
          - Le résultat unhealthy est bien dans la liste retournée
          - Le comptage est correct
        """

        mock_check.return_value = {
            "name": "Unhealthy",
            "url": "https://test.com",
            "status_code": 404,
            "response_time_ms": 80.0,
            "is_healthy": False,
            "error": None,
            "expected_status": [200],
            "attempts": 1,
            "max_latency_ms": 300,
            "latency_warning": False,
        }

        results, total_time_ms = run_health_checks(sample_carriers_list, workers=1)

        # Tous les résultats sont unhealthy
        assert all(r["is_healthy"] is False for r in results)
        assert len(results) == len(sample_carriers_list)
        assert total_time_ms > 0

    # ------------------------------------------------------------------
    # NOUVEAU — Zone 3 bis : branche error dans run_health_checks()
    # ------------------------------------------------------------------

    @patch("src.checker.check_carrier")
    def test_error_result_in_run(self, mock_check, sample_carriers_list):
        """
        Zone 3 — run_health_checks() gère les résultats en erreur.

        Le mock retourne un résultat avec error="TIMEOUT".
        Ça déclenche la branche if result["error"]: (pass) dans la boucle.
        """

        mock_check.return_value = {
            "name": "Error",
            "url": "https://test.com",
            "status_code": None,
            "response_time_ms": None,
            "is_healthy": False,
            "error": "TIMEOUT",
            "expected_status": [200],
            "attempts": 3,
            "max_latency_ms": 300,
            "latency_warning": False,
        }

        results, total_time_ms = run_health_checks(sample_carriers_list, workers=1)

        assert all(r["error"] == "TIMEOUT" for r in results)
        assert len(results) == len(sample_carriers_list)

    # ------------------------------------------------------------------
    # NOUVEAU — Zone 4 : except Exception (filet de sécurité)
    # ------------------------------------------------------------------

    @patch("src.checker.check_carrier")
    def test_unexpected_exception_in_check(self, mock_check, sample_carriers_list):
        """
        Zone 4 — check_carrier() lève une exception totalement inattendue.

        En production, ça ne devrait jamais arriver. Mais si un bug Python
        se glisse dans check_carrier() (ex: TypeError, AttributeError),
        le filet de sécurité dans run_health_checks() doit attraper
        l'exception et créer un résultat d'erreur propre au lieu de crasher.

        side_effect = RuntimeError simule un crash total de check_carrier().
        future.result() relèvera cette exception, et le except Exception
        la capturera.
        """

        mock_check.side_effect = RuntimeError("bug inattendu dans le code")

        results, total_time_ms = run_health_checks(sample_carriers_list, workers=1)

        # La fonction ne doit PAS crasher
        assert len(results) == len(sample_carriers_list)

        # Chaque résultat doit avoir une erreur UNEXPECTED
        for r in results:
            assert r["error"] is not None
            assert "UNEXPECTED" in r["error"]
            assert "bug inattendu" in r["error"]
            assert r["is_healthy"] is False

    # ------------------------------------------------------------------
    # NOUVEAU — Zone 5 : print() feedback temps réel (capsys)
    # ------------------------------------------------------------------

    @patch("src.checker.check_carrier")
    def test_print_healthy_feedback(self, mock_check, sample_carriers_list, capsys):
        """
        Zone 5 — Le feedback temps réel affiche ✓ pour les carriers healthy.

        capsys est une fixture BUILT-IN de pytest.
        Elle capture tout ce que print() envoie vers stdout et stderr.
        Après l'exécution, capsys.readouterr() retourne un objet avec :
          - .out → tout ce qui a été print() (stdout)
          - .err → tout ce qui a été envoyé vers stderr

        On exécute run_health_checks(), puis on lit la sortie capturée
        et on vérifie que le symbole ✓ apparaît.
        """

        mock_check.return_value = {
            "name": "Healthy Carrier",
            "url": "https://test.com",
            "status_code": 200,
            "response_time_ms": 150.0,
            "is_healthy": True,
            "error": None,
            "expected_status": [200],
            "attempts": 1,
            "max_latency_ms": 500,
            "latency_warning": False,
        }

        run_health_checks(sample_carriers_list, workers=1)

        # Lire la sortie capturée
        captured = capsys.readouterr()

        # Vérifier que le feedback healthy est affiché
        assert "✓" in captured.out
        assert "Test Carrier" in captured.out
        assert "150.0 ms" in captured.out

    @patch("src.checker.check_carrier")
    def test_print_unhealthy_feedback(self, mock_check, sample_carriers_list, capsys):
        """
        Zone 5 — Le feedback temps réel affiche ✗ UNHEALTHY pour les carriers unhealthy.
        """

        mock_check.return_value = {
            "name": "Bad Carrier",
            "url": "https://test.com",
            "status_code": 404,
            "response_time_ms": 80.0,
            "is_healthy": False,
            "error": None,
            "expected_status": [200],
            "attempts": 1,
            "max_latency_ms": 300,
            "latency_warning": False,
        }

        run_health_checks(sample_carriers_list, workers=1)

        captured = capsys.readouterr()

        assert "✗" in captured.out
        assert "UNHEALTHY" in captured.out

    @patch("src.checker.check_carrier")
    def test_print_error_feedback(self, mock_check, sample_carriers_list, capsys):
        """
        Zone 5 — Le feedback temps réel affiche ✗ + erreur pour les carriers en erreur.
        """

        mock_check.return_value = {
            "name": "Timeout Carrier",
            "url": "https://test.com",
            "status_code": None,
            "response_time_ms": None,
            "is_healthy": False,
            "error": "TIMEOUT",
            "expected_status": [200],
            "attempts": 3,
            "max_latency_ms": 300,
            "latency_warning": False,
        }

        run_health_checks(sample_carriers_list, workers=1)

        captured = capsys.readouterr()

        assert "✗" in captured.out
        assert "TIMEOUT" in captured.out

    @patch("src.checker.check_carrier")
    def test_print_slow_feedback(self, mock_check, sample_carriers_list, capsys):
        """
        Zone 5 — Le feedback temps réel affiche ⚠️ SLOW pour les carriers lents.
        """

        mock_check.return_value = {
            "name": "Slow Carrier",
            "url": "https://test.com",
            "status_code": 200,
            "response_time_ms": 650.0,
            "is_healthy": True,
            "error": None,
            "expected_status": [200],
            "attempts": 1,
            "max_latency_ms": 500,
            "latency_warning": True,
        }

        run_health_checks(sample_carriers_list, workers=1)

        captured = capsys.readouterr()

        assert "✓" in captured.out
        assert "SLOW" in captured.out
