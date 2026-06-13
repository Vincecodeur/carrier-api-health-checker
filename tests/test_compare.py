# ============================================================================
# FICHIER : tests/test_compare.py
# RESPONSABILITÉ : tester le module src/compare.py
# ============================================================================

import json
import os
from pathlib import Path
from src.compare import find_previous_run, compare_results


# ============================================================================
# Tests pour find_previous_run()
# ============================================================================


def test_find_previous_run_no_directory(tmp_path):
    """
    Test : le dossier n'existe pas → retourne None.
    """

    result = find_previous_run(output_dir=str(tmp_path / "nonexistent"))
    assert result is None


def test_find_previous_run_no_json_files(tmp_path):
    """
    Test : le dossier existe mais ne contient aucun fichier JSON → None.
    """

    result = find_previous_run(output_dir=str(tmp_path))
    assert result is None


def test_find_previous_run_finds_latest(tmp_path):
    """
    Test : avec 2 fichiers JSON, retourne le plus récent.
    """

    # Créer 2 fichiers JSON avec des timestamps différents
    old_data = {"timestamp": "2026-06-13 10:00:00", "results": []}
    new_data = {"timestamp": "2026-06-13 11:00:00", "results": [{"name": "Latest"}]}

    old_file = tmp_path / "health_check_20260613_100000.json"
    new_file = tmp_path / "health_check_20260613_110000.json"

    old_file.write_text(json.dumps(old_data), encoding="utf-8")
    new_file.write_text(json.dumps(new_data), encoding="utf-8")

    result = find_previous_run(output_dir=str(tmp_path))

    assert result is not None
    assert result["timestamp"] == "2026-06-13 11:00:00"
    assert len(result["results"]) == 1


def test_find_previous_run_excludes_current(tmp_path):
    """
    Test : exclut le fichier du run actuel et retourne le précédent.
    """

    old_data = {"timestamp": "old", "results": []}
    new_data = {"timestamp": "new", "results": []}

    old_file = tmp_path / "health_check_20260613_100000.json"
    new_file = tmp_path / "health_check_20260613_110000.json"

    old_file.write_text(json.dumps(old_data), encoding="utf-8")
    new_file.write_text(json.dumps(new_data), encoding="utf-8")

    # Exclure le fichier le plus récent
    result = find_previous_run(output_dir=str(tmp_path), exclude_file=str(new_file))

    assert result is not None
    assert result["timestamp"] == "old"


def test_find_previous_run_invalid_json(tmp_path):
    """
    Test : fichier JSON corrompu → retourne None.
    """

    bad_file = tmp_path / "health_check_20260613_100000.json"
    bad_file.write_text("{ not valid json !!!", encoding="utf-8")

    result = find_previous_run(output_dir=str(tmp_path))
    assert result is None


# ============================================================================
# Tests pour compare_results()
# ============================================================================


def test_compare_no_changes():
    """
    Test : résultats identiques → aucun changement.
    """

    previous = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]
    current = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 105.0},
    ]

    changes = compare_results(previous, current)

    # Pas de changement de statut, et 5% de variation de latence < 50% seuil
    assert len(changes) == 0


def test_compare_new_down():
    """
    Test : carrier healthy → unhealthy → détecte NEW_DOWN.
    """

    previous = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]
    current = [
        {"name": "Carrier A", "is_healthy": False, "error": None, "status_code": 404, "response_time_ms": 80.0},
    ]

    changes = compare_results(previous, current)

    assert len(changes) == 1
    assert changes[0]["type"] == "NEW_DOWN"
    assert changes[0]["carrier"] == "Carrier A"


def test_compare_new_down_error():
    """
    Test : carrier healthy → error (timeout) → détecte NEW_DOWN.
    """

    previous = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]
    current = [
        {"name": "Carrier A", "is_healthy": False, "error": "TIMEOUT", "status_code": None, "response_time_ms": None},
    ]

    changes = compare_results(previous, current)

    assert len(changes) == 1
    assert changes[0]["type"] == "NEW_DOWN"
    assert "TIMEOUT" in changes[0]["details"]


def test_compare_recovered():
    """
    Test : carrier unhealthy → healthy → détecte RECOVERED.
    """

    previous = [
        {"name": "Carrier A", "is_healthy": False, "error": None, "status_code": 404, "response_time_ms": 80.0},
    ]
    current = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]

    changes = compare_results(previous, current)

    assert len(changes) == 1
    assert changes[0]["type"] == "RECOVERED"


def test_compare_recovered_from_error():
    """
    Test : carrier error → healthy → détecte RECOVERED.
    """

    previous = [
        {"name": "Carrier A", "is_healthy": False, "error": "TIMEOUT", "status_code": None, "response_time_ms": None},
    ]
    current = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]

    changes = compare_results(previous, current)

    assert len(changes) == 1
    assert changes[0]["type"] == "RECOVERED"
    assert "TIMEOUT" in changes[0]["details"]


def test_compare_degraded_latency():
    """
    Test : latence augmentée de > 50% → détecte DEGRADED.
    """

    previous = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]
    current = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 200.0},
    ]

    # 100 → 200 = +100% > 50% seuil
    changes = compare_results(previous, current)

    assert len(changes) == 1
    assert changes[0]["type"] == "DEGRADED"
    assert "+100%" in changes[0]["details"]


def test_compare_improved_latency():
    """
    Test : latence diminuée de > 50% → détecte IMPROVED.
    """

    previous = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 300.0},
    ]
    current = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]

    # 300 → 100 = -67% < -50% seuil
    changes = compare_results(previous, current)

    assert len(changes) == 1
    assert changes[0]["type"] == "IMPROVED"


def test_compare_new_carrier():
    """
    Test : carrier dans current mais pas dans previous → NEW.
    """

    previous = []
    current = [
        {"name": "New Carrier", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]

    changes = compare_results(previous, current)

    assert len(changes) == 1
    assert changes[0]["type"] == "NEW"
    assert changes[0]["carrier"] == "New Carrier"


def test_compare_removed_carrier():
    """
    Test : carrier dans previous mais pas dans current → REMOVED.
    """

    previous = [
        {"name": "Old Carrier", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]
    current = []

    changes = compare_results(previous, current)

    assert len(changes) == 1
    assert changes[0]["type"] == "REMOVED"
    assert changes[0]["carrier"] == "Old Carrier"


def test_compare_multiple_changes():
    """
    Test : plusieurs changements simultanés.
    """

    previous = [
        {"name": "Down Carrier", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
        {"name": "Recovered", "is_healthy": False, "error": "TIMEOUT", "status_code": None, "response_time_ms": None},
        {"name": "Stable", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
        {"name": "Removed", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]
    current = [
        {"name": "Down Carrier", "is_healthy": False, "error": "CONNECTION_ERROR", "status_code": None, "response_time_ms": None},
        {"name": "Recovered", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 150.0},
        {"name": "Stable", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 105.0},
        {"name": "Brand New", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 80.0},
    ]

    changes = compare_results(previous, current)

    types = [c["type"] for c in changes]

    assert "NEW_DOWN" in types       # Down Carrier: healthy → error
    assert "RECOVERED" in types      # Recovered: error → healthy
    assert "REMOVED" in types        # Removed: absent du current
    assert "NEW" in types            # Brand New: absent du previous
    # Stable: pas de changement (5% variation < 50%)


def test_compare_custom_latency_threshold():
    """
    Test : seuil de latence personnalisé (20% au lieu de 50%).
    """

    previous = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 100.0},
    ]
    current = [
        {"name": "Carrier A", "is_healthy": True, "error": None, "status_code": 200, "response_time_ms": 130.0},
    ]

    # 30% de variation → pas de changement avec le seuil par défaut (50%)
    changes_default = compare_results(previous, current)
    assert len(changes_default) == 0

    # 30% de variation → DEGRADED avec un seuil de 20%
    changes_custom = compare_results(previous, current, latency_threshold=20.0)
    assert len(changes_custom) == 1
    assert changes_custom[0]["type"] == "DEGRADED"