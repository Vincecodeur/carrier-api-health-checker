# ============================================================================
# FICHIER : src/notify.py
# RESPONSABILITÉ : envoyer des notifications vers Microsoft Teams via webhook
#
# Utilise le format Adaptive Card (requis par Teams Workflows / Power Automate).
# L'ancien format MessageCard (connecteurs O365) est déprécié depuis 2024.
#
# Le module ne décide PAS quand envoyer — c'est main.py qui décide.
# Ce module se contente de :
#   1. Construire le payload Adaptive Card
#   2. Envoyer le POST HTTP
#   3. Retourner True/False selon le succès
# ============================================================================

import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


def build_adaptive_card(
    results: list[dict],
    changes: list[dict] | None = None,
) -> dict:
    """
    Construit le payload Adaptive Card pour Teams.

    L'Adaptive Card est le format de carte riche supporté par Teams.
    C'est un JSON qui décrit une mise en page avec des blocs de texte,
    des tableaux, des couleurs, etc. Teams le rend visuellement dans le channel.

    Args:
        results:  Liste de dicts résultats du health check.
        changes:  Liste de dicts changements (optionnel, issu de compare_results).

    Returns:
        Dict représentant le payload complet à envoyer au webhook.
    """

    # ---- COMPTAGES ----
    total = len(results)
    healthy = sum(1 for r in results if r.get("is_healthy"))
    unhealthy = sum(1 for r in results if not r.get("is_healthy") and not r.get("error"))
    errors = sum(1 for r in results if r.get("error"))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---- COULEUR GLOBALE ----
    # Vert si tout est OK, rouge si des carriers sont down
    if errors > 0 or unhealthy > 0:
        status_emoji = "🔴"
        status_text = f"{errors + unhealthy} carrier(s) en échec"
    else:
        status_emoji = "🟢"
        status_text = "Tous les carriers sont healthy"

    # ---- CONSTRUIRE LE BODY DE LA CARTE ----
    body = [
        # Titre
        {
            "type": "TextBlock",
            "text": f"{status_emoji} Carrier API Health Check",
            "size": "Large",
            "weight": "Bolder",
        },
        # Sous-titre avec timestamp
        {
            "type": "TextBlock",
            "text": f"Anchanto — {timestamp}",
            "size": "Small",
            "isSubtle": True,
            "spacing": "None",
        },
        # Résumé
        {
            "type": "TextBlock",
            "text": f"**{healthy}/{total}** healthy — {status_text}",
            "spacing": "Medium",
        },
    ]

    # ---- CARRIERS EN ÉCHEC ----
    failed = [r for r in results if not r.get("is_healthy")]

    if failed:
        # Séparateur
        body.append(
            {
                "type": "TextBlock",
                "text": "**Carriers en échec :**",
                "spacing": "Medium",
                "weight": "Bolder",
            }
        )

        for r in failed:
            if r.get("error"):
                detail = f"🔴 **{r['name']}** — {r['error']}"
            else:
                detail = f"🟡 **{r['name']}** — HTTP {r.get('status_code')} (unexpected)"

            body.append(
                {
                    "type": "TextBlock",
                    "text": detail,
                    "spacing": "Small",
                }
            )

    # ---- CHANGEMENTS CRITIQUES ----
    if changes:
        # Filtrer uniquement les changements importants
        critical_types = {"NEW_DOWN", "RECOVERED"}
        critical_changes = [c for c in changes if c["type"] in critical_types]

        if critical_changes:
            body.append(
                {
                    "type": "TextBlock",
                    "text": "**Changements détectés :**",
                    "spacing": "Medium",
                    "weight": "Bolder",
                }
            )

            icons = {
                "NEW_DOWN": "🔻",
                "RECOVERED": "🔺",
            }

            for c in critical_changes:
                icon = icons.get(c["type"], "❓")
                body.append(
                    {
                        "type": "TextBlock",
                        "text": f"{icon} **{c['type']}** — {c['carrier']}: {c['details']}",
                        "spacing": "Small",
                    }
                )

    # ---- ASSEMBLER LE PAYLOAD COMPLET ----
    #
    # Format requis par Teams Workflows (Power Automate) :
    # {
    #   "type": "message",
    #   "attachments": [{
    #     "contentType": "application/vnd.microsoft.card.adaptive",
    #     "content": { ... Adaptive Card ... }
    #   }]
    # }
    #
    # C'est différent de l'ancien format MessageCard.
    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body,
                },
            }
        ],
    }

    return payload


def send_teams_notification(
    webhook_url: str,
    results: list[dict],
    changes: list[dict] | None = None,
    timeout: int = 10,
) -> bool:
    """
    Envoie une notification dans un channel Teams via webhook.

    Args:
        webhook_url: URL du webhook Teams (Workflows / Power Automate).
        results:     Liste de dicts résultats du health check.
        changes:     Liste de dicts changements (optionnel).
        timeout:     Timeout de la requête POST en secondes.

    Returns:
        True si la notification a été envoyée avec succès, False sinon.

    La fonction ne lève JAMAIS d'exception — elle retourne False en cas
    d'erreur. Le health check ne doit pas échouer parce que Teams est down.
    """

    logger.info("Sending Teams notification...")

    # ---- CONSTRUIRE LE PAYLOAD ----
    payload = build_adaptive_card(results, changes)

    # ---- ENVOYER LE POST ----
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

        # Teams retourne 200 ou 202 si le message est accepté
        if response.status_code in (200, 202):
            logger.info(f"Teams notification sent successfully (HTTP {response.status_code})")
            return True
        else:
            logger.warning(
                f"Teams notification failed: HTTP {response.status_code} — {response.text[:200]}"
            )
            return False

    except requests.exceptions.Timeout:
        logger.error("Teams notification failed: timeout")
        return False

    except requests.exceptions.ConnectionError:
        logger.error("Teams notification failed: connection error")
        return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Teams notification failed: {e}")
        return False


def should_notify(results: list[dict], changes: list[dict] | None = None) -> bool:
    """
    Détermine si une notification doit être envoyée.

    Règles :
        - OUI si au moins un carrier est unhealthy ou en erreur
        - OUI si un changement critique est détecté (NEW_DOWN ou RECOVERED)
        - NON si tout est healthy et stable (pas de bruit)

    Args:
        results: Liste de dicts résultats.
        changes: Liste de dicts changements (optionnel).

    Returns:
        True si une notification doit être envoyée.
    """

    # Vérifier s'il y a des carriers en échec
    has_failures = any(not r.get("is_healthy") for r in results)

    if has_failures:
        return True

    # Vérifier s'il y a des changements critiques
    if changes:
        critical_types = {"NEW_DOWN", "RECOVERED"}
        has_critical = any(c["type"] in critical_types for c in changes)
        if has_critical:
            return True

    return False
