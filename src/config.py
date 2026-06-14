# ============================================================================
# FICHIER : src/config.py
# RESPONSABILITÉ : chargement et validation de la configuration carriers
#
# VERSION : E5 — ajout de validate_carriers()
#
# Le fichier carriers.json est :
#   1. Chargé (load_config)
#   2. Validé (validate_carriers)
#   3. Retourné à main.py
#
# Si la validation échoue, le script s'arrête AVANT les health checks
# avec des messages d'erreur clairs et actionnables.
# ============================================================================

import json
import logging
import sys

logger = logging.getLogger(__name__)

# ---- CONSTANTES DE VALIDATION ----

REQUIRED_FIELDS = {
    "name": str,
    "url": str,
    "method": str,
    "expected_status": list,
    "timeout": (int, float),
}

OPTIONAL_FIELDS = {
    "retries": int,
    "max_latency_ms": (int, float),
}

VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"}


def validate_carriers(carriers: list[dict]) -> list[str]:
    """
    Valide la structure et les types de chaque carrier.

    Vérifie :
        - Présence des champs requis (name, url, method, expected_status, timeout)
        - Types corrects pour chaque champ
        - Contraintes métier (url commence par http, timeout > 0, etc.)
        - Types corrects pour les champs optionnels s'ils sont présents

    Args:
        carriers: Liste de dicts carriers chargés depuis carriers.json.

    Returns:
        Liste de messages d'erreur. Liste vide = aucune erreur.

    La fonction ne lève PAS d'exception — elle retourne les erreurs.
    C'est load_config() qui décide quoi faire avec (afficher + sys.exit).
    """

    errors = []

    for i, carrier in enumerate(carriers):

        # Identifiant pour les messages d'erreur
        # On utilise le name s'il existe, sinon l'index
        carrier_id = carrier.get("name", f"carrier index {i}")

        # ---- CHAMPS REQUIS ----
        for field, expected_type in REQUIRED_FIELDS.items():

            # Vérifier la présence
            if field not in carrier:
                errors.append(f'Carrier "{carrier_id}": missing required field "{field}"')
                continue

            # Vérifier le type
            value = carrier[field]
            if not isinstance(value, expected_type):
                # expected_type peut être un tuple (int, float) ou un type simple (str)
                if isinstance(expected_type, tuple):
                    type_names = " or ".join(t.__name__ for t in expected_type)
                else:
                    type_names = expected_type.__name__
                errors.append(
                    f'Carrier "{carrier_id}": field "{field}" must be {type_names}, '
                    f"got {type(value).__name__}"
                )
                continue

            # ---- CONTRAINTES MÉTIER ----

            # name : non vide
            if field == "name" and not value.strip():
                errors.append(f'Carrier index {i}: field "name" must not be empty')

            # url : commence par http:// ou https://
            if field == "url" and not value.startswith(("http://", "https://")):
                errors.append(
                    f'Carrier "{carrier_id}": field "url" must start with http:// or https://, '
                    f'got "{value[:50]}"'
                )

            # method : valeur autorisée
            if field == "method" and value.upper() not in VALID_METHODS:
                errors.append(
                    f'Carrier "{carrier_id}": field "method" must be one of {VALID_METHODS}, '
                    f'got "{value}"'
                )

            # expected_status : liste non vide d'entiers entre 100 et 599
            if field == "expected_status":
                if len(value) == 0:
                    errors.append(
                        f'Carrier "{carrier_id}": field "expected_status" must not be empty'
                    )
                else:
                    for j, status in enumerate(value):
                        if not isinstance(status, int):
                            errors.append(
                                f'Carrier "{carrier_id}": expected_status[{j}] must be int, '
                                f"got {type(status).__name__}"
                            )
                        elif not (100 <= status <= 599):
                            errors.append(
                                f'Carrier "{carrier_id}": expected_status[{j}] must be between '
                                f"100 and 599, got {status}"
                            )

            # timeout : supérieur à 0
            if field == "timeout" and value <= 0:
                errors.append(
                    f'Carrier "{carrier_id}": field "timeout" must be > 0, got {value}'
                )

        # ---- CHAMPS OPTIONNELS ----
        for field, expected_type in OPTIONAL_FIELDS.items():

            # Absent = pas d'erreur (c'est optionnel)
            if field not in carrier:
                continue

            value = carrier[field]

            # Vérifier le type
            if not isinstance(value, expected_type):
                if isinstance(expected_type, tuple):
                    type_names = " or ".join(t.__name__ for t in expected_type)
                else:
                    type_names = expected_type.__name__
                errors.append(
                    f'Carrier "{carrier_id}": field "{field}" must be {type_names}, '
                    f"got {type(value).__name__}"
                )
                continue

            # retries : >= 0
            if field == "retries" and value < 0:
                errors.append(
                    f'Carrier "{carrier_id}": field "retries" must be >= 0, got {value}'
                )

            # max_latency_ms : >= 0
            if field == "max_latency_ms" and value < 0:
                errors.append(
                    f'Carrier "{carrier_id}": field "max_latency_ms" must be >= 0, got {value}'
                )

    return errors


def load_config(filepath: str) -> list[dict]:
    """
    Charge et valide la configuration des transporteurs depuis un fichier JSON.

    Args:
        filepath: Chemin vers le fichier JSON de configuration.

    Returns:
        Liste de dictionnaires, un par transporteur.

    Raises:
        SystemExit: Si le fichier est introuvable, le JSON invalide,
                    la clé "carriers" absente, ou la validation échoue.
    """

    logger.info(f"Loading config from: {filepath}")

    # ---- CHARGEMENT ----
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

    except FileNotFoundError:
        logger.critical(f"Config file not found: {filepath}")
        print(f"\n  ❌ Config file not found: {filepath}")
        sys.exit(1)

    except json.JSONDecodeError as e:
        logger.critical(f"Invalid JSON in {filepath}: {e}")
        print(f"\n  ❌ Invalid JSON in {filepath}: {e}")
        sys.exit(1)

    # ---- VÉRIFIER LA CLÉ "carriers" ----
    if "carriers" not in data:
        logger.critical(f'Missing "carriers" key in {filepath}')
        print(f'\n  ❌ Missing "carriers" key in {filepath}')
        sys.exit(1)

    carriers = data["carriers"]

    # ---- VALIDATION ----
    # On valide seulement si la liste n'est pas vide.
    # Une liste vide est valide (aucun carrier configuré).
    if carriers:
        validation_errors = validate_carriers(carriers)

        if validation_errors:
            logger.critical(f"Config validation failed: {len(validation_errors)} error(s)")
            print(f"\n  ❌ Config validation failed ({len(validation_errors)} error(s)):\n")

            for error in validation_errors:
                print(f"     • {error}")
                logger.error(f"  {error}")

            print()
            sys.exit(1)

    logger.info(f"Successfully loaded {len(carriers)} carriers")
    return carriers