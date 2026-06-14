# ============================================================================
# FICHIER : tests/test_version.py
# RESPONSABILITÉ : tester le module src/version.py
# ============================================================================

from src.version import APP_NAME, AUTHOR, VERSION


def test_version_format():
    """La version respecte le format SemVer (X.Y.Z)."""

    parts = VERSION.split(".")
    assert len(parts) == 3, f"VERSION doit avoir 3 parties (X.Y.Z), got {VERSION}"

    for part in parts:
        assert part.isdigit(), f"Chaque partie doit être un entier, got '{part}'"


def test_version_constants_not_empty():
    """Les constantes APP_NAME et AUTHOR ne sont pas vides."""

    assert len(APP_NAME) > 0
    assert len(AUTHOR) > 0
    assert "Carrier" in APP_NAME
    assert "Anchanto" in AUTHOR
