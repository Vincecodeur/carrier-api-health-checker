# ============================================================================
# FICHIER : tests/test_config.py
# RESPONSABILITÉ : tester le module src/config.py (chargement + validation)
# ============================================================================

import json
import pytest
from src.config import load_config, validate_carriers


# ============================================================================
# Tests pour load_config() — chargement (existants, inchangés)
# ============================================================================


def test_load_config_success(tmp_path):
    """Chargement réussi d'un fichier JSON valide."""

    config = {
        "carriers": [
            {
                "name": "Test Carrier",
                "url": "https://api.example.com",
                "method": "GET",
                "expected_status": [200],
                "timeout": 10,
            }
        ]
    }

    config_file = tmp_path / "carriers.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")

    result = load_config(str(config_file))

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "Test Carrier"


def test_load_config_file_not_found():
    """Fichier introuvable → SystemExit."""

    with pytest.raises(SystemExit):
        load_config("nonexistent_file.json")


def test_load_config_invalid_json(tmp_path):
    """JSON invalide → SystemExit."""

    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ this is not valid json !!!", encoding="utf-8")

    with pytest.raises(SystemExit):
        load_config(str(bad_file))


def test_load_config_missing_carriers_key(tmp_path):
    """Clé "carriers" absente → SystemExit."""

    config = {"transporteurs": []}
    config_file = tmp_path / "carriers.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(SystemExit):
        load_config(str(config_file))


def test_load_config_empty_carriers(tmp_path):
    """Liste vide → valide, retourne une liste vide."""

    config = {"carriers": []}
    config_file = tmp_path / "carriers.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")

    result = load_config(str(config_file))
    assert result == []


# ============================================================================
# Tests pour validate_carriers() — validation directe
# ============================================================================


def test_validate_valid_carrier():
    """Carrier complet et valide → aucune erreur."""

    carriers = [
        {
            "name": "Test Carrier",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [200, 401],
            "timeout": 10,
            "retries": 2,
            "max_latency_ms": 500,
        }
    ]

    errors = validate_carriers(carriers)
    assert errors == []


def test_validate_minimal_carrier():
    """Carrier avec uniquement les champs requis → aucune erreur."""

    carriers = [
        {
            "name": "Minimal",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [200],
            "timeout": 5,
        }
    ]

    errors = validate_carriers(carriers)
    assert errors == []


def test_validate_missing_required_field():
    """Champ requis manquant (url) → erreur détectée."""

    carriers = [
        {
            "name": "No URL",
            "method": "GET",
            "expected_status": [200],
            "timeout": 10,
        }
    ]

    errors = validate_carriers(carriers)
    assert len(errors) == 1
    assert "missing required field" in errors[0]
    assert '"url"' in errors[0]


def test_validate_wrong_type():
    """Type incorrect (timeout string au lieu de int) → erreur détectée."""

    carriers = [
        {
            "name": "Bad Type",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [200],
            "timeout": "ten",
        }
    ]

    errors = validate_carriers(carriers)
    assert len(errors) == 1
    assert "timeout" in errors[0]
    assert "int or float" in errors[0]
    assert "str" in errors[0]


def test_validate_invalid_url():
    """URL sans http/https → erreur détectée."""

    carriers = [
        {
            "name": "Bad URL",
            "url": "ftp://not-http.example.com",
            "method": "GET",
            "expected_status": [200],
            "timeout": 10,
        }
    ]

    errors = validate_carriers(carriers)
    assert len(errors) == 1
    assert "http://" in errors[0]


def test_validate_invalid_method():
    """Méthode HTTP invalide → erreur détectée."""

    carriers = [
        {
            "name": "Bad Method",
            "url": "https://api.example.com",
            "method": "DOWNLOAD",
            "expected_status": [200],
            "timeout": 10,
        }
    ]

    errors = validate_carriers(carriers)
    assert len(errors) == 1
    assert "DOWNLOAD" in errors[0]


def test_validate_empty_expected_status():
    """expected_status vide → erreur détectée."""

    carriers = [
        {
            "name": "Empty Status",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [],
            "timeout": 10,
        }
    ]

    errors = validate_carriers(carriers)
    assert len(errors) == 1
    assert "must not be empty" in errors[0]


def test_validate_invalid_status_code():
    """expected_status contient un code hors limites → erreur détectée."""

    carriers = [
        {
            "name": "Bad Status",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [200, 999],
            "timeout": 10,
        }
    ]

    errors = validate_carriers(carriers)
    assert len(errors) == 1
    assert "999" in errors[0]
    assert "100 and 599" in errors[0]


def test_validate_negative_timeout():
    """timeout négatif → erreur détectée."""

    carriers = [
        {
            "name": "Negative Timeout",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [200],
            "timeout": -5,
        }
    ]

    errors = validate_carriers(carriers)
    assert len(errors) == 1
    assert "timeout" in errors[0]
    assert "> 0" in errors[0]


def test_validate_negative_retries():
    """retries négatif → erreur détectée."""

    carriers = [
        {
            "name": "Negative Retries",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [200],
            "timeout": 10,
            "retries": -1,
        }
    ]

    errors = validate_carriers(carriers)
    assert len(errors) == 1
    assert "retries" in errors[0]
    assert ">= 0" in errors[0]


def test_validate_optional_wrong_type():
    """Champ optionnel avec mauvais type → erreur détectée."""

    carriers = [
        {
            "name": "Bad Optional",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [200],
            "timeout": 10,
            "max_latency_ms": "fast",
        }
    ]

    errors = validate_carriers(carriers)
    assert len(errors) == 1
    assert "max_latency_ms" in errors[0]


def test_validate_multiple_errors():
    """Plusieurs erreurs sur un même carrier → toutes détectées."""

    carriers = [
        {
            "name": "",
            "url": "not-a-url",
            "method": "DOWNLOAD",
            "expected_status": [],
            "timeout": -1,
        }
    ]

    errors = validate_carriers(carriers)

    # Au moins 4 erreurs : name vide, url invalide, method invalide,
    # expected_status vide, timeout négatif
    assert len(errors) >= 4


def test_validate_multiple_carriers():
    """Erreurs sur plusieurs carriers → toutes détectées avec le bon identifiant."""

    carriers = [
        {
            "name": "Good Carrier",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [200],
            "timeout": 10,
        },
        {
            "name": "Bad Carrier",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [200],
            "timeout": "oops",
        },
    ]

    errors = validate_carriers(carriers)

    assert len(errors) == 1
    assert "Bad Carrier" in errors[0]
    # Pas d'erreur pour Good Carrier


def test_load_config_validation_failure(tmp_path):
    """load_config avec un carrier invalide → SystemExit."""

    config = {
        "carriers": [
            {
                "name": "Invalid",
                "url": "not-a-url",
                "method": "GET",
                "expected_status": [200],
                "timeout": 10,
            }
        ]
    }

    config_file = tmp_path / "carriers.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(SystemExit):
        load_config(str(config_file))


def test_validate_unknown_fields_ignored():
    """Champs inconnus → ignorés (pas d'erreur)."""

    carriers = [
        {
            "name": "Extra Fields",
            "url": "https://api.example.com",
            "method": "GET",
            "expected_status": [200],
            "timeout": 10,
            "color": "blue",
            "priority": 1,
        }
    ]

    errors = validate_carriers(carriers)
    assert errors == []