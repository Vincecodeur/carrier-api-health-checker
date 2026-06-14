# ============================================================================
# FICHIER : tests/test_notify.py
# RESPONSABILITÉ : tester le module src/notify.py
# ============================================================================

from unittest.mock import patch, MagicMock
from src.notify import build_adaptive_card, send_teams_notification, should_notify


# ============================================================================
# Tests pour build_adaptive_card()
# ============================================================================


def test_build_card_all_healthy(sample_result_healthy):
    """
    Test : tous les carriers healthy → carte verte avec le bon résumé.
    """

    results = [sample_result_healthy]
    payload = build_adaptive_card(results)

    # Structure Adaptive Card
    assert payload["type"] == "message"
    assert len(payload["attachments"]) == 1
    assert payload["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"

    # Contenu
    content = payload["attachments"][0]["content"]
    assert content["type"] == "AdaptiveCard"
    assert content["version"] == "1.4"

    # Le titre contient l'emoji vert
    body = content["body"]
    assert any("🟢" in block.get("text", "") for block in body)
    assert any("1/1" in block.get("text", "") for block in body)


def test_build_card_with_failures(sample_result_healthy, sample_result_unhealthy, sample_result_error):
    """
    Test : carriers en échec → carte rouge avec détails des échecs.
    """

    results = [sample_result_healthy, sample_result_unhealthy, sample_result_error]
    payload = build_adaptive_card(results)

    body = payload["attachments"][0]["content"]["body"]

    # Emoji rouge dans le titre
    assert any("🔴" in block.get("text", "") for block in body)

    # Noms des carriers en échec mentionnés
    all_text = " ".join(block.get("text", "") for block in body)
    assert "Unhealthy Carrier" in all_text
    assert "Error Carrier" in all_text


def test_build_card_with_changes(sample_result_healthy):
    """
    Test : changements critiques inclus dans la carte.
    """

    results = [sample_result_healthy]
    changes = [
        {"type": "NEW_DOWN", "carrier": "DHL Express", "details": "HEALTHY → TIMEOUT"},
        {"type": "RECOVERED", "carrier": "GLS", "details": "TIMEOUT → HTTP 200"},
    ]

    payload = build_adaptive_card(results, changes=changes)

    body = payload["attachments"][0]["content"]["body"]
    all_text = " ".join(block.get("text", "") for block in body)

    assert "DHL Express" in all_text
    assert "GLS" in all_text
    assert "🔻" in all_text
    assert "🔺" in all_text


def test_build_card_ignores_non_critical_changes(sample_result_healthy):
    """
    Test : les changements DEGRADED/IMPROVED ne sont PAS inclus dans la carte.
    Seuls NEW_DOWN et RECOVERED sont affichés.
    """

    results = [sample_result_healthy]
    changes = [
        {"type": "DEGRADED", "carrier": "FedEx", "details": "200ms → 400ms (+100%)"},
        {"type": "IMPROVED", "carrier": "DPD", "details": "300ms → 100ms (-67%)"},
    ]

    payload = build_adaptive_card(results, changes=changes)

    body = payload["attachments"][0]["content"]["body"]
    all_text = " ".join(block.get("text", "") for block in body)

    # Les changements non-critiques ne doivent PAS apparaître
    assert "FedEx" not in all_text
    assert "DPD" not in all_text


def test_build_card_no_changes(sample_result_healthy):
    """
    Test : pas de changements → pas de section changements dans la carte.
    """

    results = [sample_result_healthy]
    payload = build_adaptive_card(results, changes=None)

    body = payload["attachments"][0]["content"]["body"]
    all_text = " ".join(block.get("text", "") for block in body)

    assert "Changements" not in all_text


# ============================================================================
# Tests pour send_teams_notification()
# ============================================================================


class TestSendNotification:

    @patch("src.notify.requests.post")
    def test_success(self, mock_post, sample_result_healthy):
        """
        Test : Teams répond 200 → retourne True.
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = send_teams_notification(
            webhook_url="https://fake-webhook.example.com",
            results=[sample_result_healthy],
        )

        assert result is True
        mock_post.assert_called_once()

    @patch("src.notify.requests.post")
    def test_accepted_202(self, mock_post, sample_result_healthy):
        """
        Test : Teams répond 202 (Accepted) → retourne True.
        """

        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        result = send_teams_notification(
            webhook_url="https://fake-webhook.example.com",
            results=[sample_result_healthy],
        )

        assert result is True

    @patch("src.notify.requests.post")
    def test_failure_400(self, mock_post, sample_result_healthy):
        """
        Test : Teams répond 400 → retourne False.
        """

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        result = send_teams_notification(
            webhook_url="https://fake-webhook.example.com",
            results=[sample_result_healthy],
        )

        assert result is False

    @patch("src.notify.requests.post")
    def test_timeout(self, mock_post, sample_result_healthy):
        """
        Test : timeout lors de l'envoi → retourne False (pas de crash).
        """

        import requests as req
        mock_post.side_effect = req.exceptions.Timeout("timeout")

        result = send_teams_notification(
            webhook_url="https://fake-webhook.example.com",
            results=[sample_result_healthy],
        )

        assert result is False

    @patch("src.notify.requests.post")
    def test_connection_error(self, mock_post, sample_result_healthy):
        """
        Test : erreur de connexion → retourne False (pas de crash).
        """

        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("DNS failed")

        result = send_teams_notification(
            webhook_url="https://fake-webhook.example.com",
            results=[sample_result_healthy],
        )

        assert result is False

    @patch("src.notify.requests.post")
    def test_payload_is_adaptive_card(self, mock_post, sample_result_healthy):
        """
        Test : le payload envoyé à Teams est bien au format Adaptive Card.
        Vérifie la structure exacte attendue par Teams Workflows.
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        send_teams_notification(
            webhook_url="https://fake-webhook.example.com",
            results=[sample_result_healthy],
        )

        # Récupérer le payload envoyé
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")

        assert payload["type"] == "message"
        assert payload["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"
        assert payload["attachments"][0]["content"]["type"] == "AdaptiveCard"

    @patch("src.notify.requests.post")
    def test_with_changes(self, mock_post, sample_result_unhealthy):
        """
        Test : envoi avec des changements critiques → succès.
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        changes = [
            {"type": "NEW_DOWN", "carrier": "Test", "details": "HEALTHY → ERROR"},
        ]

        result = send_teams_notification(
            webhook_url="https://fake-webhook.example.com",
            results=[sample_result_unhealthy],
            changes=changes,
        )

        assert result is True


# ============================================================================
# Tests pour should_notify()
# ============================================================================


class TestShouldNotify:

    def test_all_healthy_no_changes(self, sample_result_healthy):
        """
        Test : tout healthy, pas de changements → PAS de notification.
        """

        assert should_notify([sample_result_healthy]) is False
        assert should_notify([sample_result_healthy], changes=[]) is False

    def test_unhealthy_carrier(self, sample_result_unhealthy):
        """
        Test : carrier unhealthy → notification.
        """

        assert should_notify([sample_result_unhealthy]) is True

    def test_error_carrier(self, sample_result_error):
        """
        Test : carrier en erreur → notification.
        """

        assert should_notify([sample_result_error]) is True

    def test_new_down_change(self, sample_result_healthy):
        """
        Test : changement NEW_DOWN → notification même si tout est healthy
        (le carrier est rétabli mais on veut signaler qu'il a été down).
        """

        changes = [{"type": "NEW_DOWN", "carrier": "Test", "details": "..."}]
        assert should_notify([sample_result_healthy], changes=changes) is True

    def test_recovered_change(self, sample_result_healthy):
        """
        Test : changement RECOVERED → notification.
        """

        changes = [{"type": "RECOVERED", "carrier": "Test", "details": "..."}]
        assert should_notify([sample_result_healthy], changes=changes) is True

    def test_degraded_only_no_notify(self, sample_result_healthy):
        """
        Test : seulement DEGRADED (pas critique) → PAS de notification.
        """

        changes = [{"type": "DEGRADED", "carrier": "Test", "details": "..."}]
        assert should_notify([sample_result_healthy], changes=changes) is False

    def test_improved_only_no_notify(self, sample_result_healthy):
        """
        Test : seulement IMPROVED (pas critique) → PAS de notification.
        """

        changes = [{"type": "IMPROVED", "carrier": "Test", "details": "..."}]
        assert should_notify([sample_result_healthy], changes=changes) is False