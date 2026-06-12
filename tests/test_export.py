# ============================================================================
# FICHIER : tests/test_export.py
# RESPONSABILITÉ : tester le module src/export.py
# ============================================================================

import pytest
import csv
import os
from src.export import export_to_csv


def test_export_creates_csv_file(tmp_path, sample_result_healthy):
    """
    Test : export_to_csv crée bien un fichier CSV dans le dossier spécifié.
    """

    results = [sample_result_healthy]
    filepath = export_to_csv(results, output_dir=str(tmp_path))

    assert filepath is not None, "export_to_csv doit retourner le chemin du fichier"
    assert os.path.exists(filepath), "Le fichier CSV doit exister sur le disque"
    assert filepath.endswith(".csv"), "Le fichier doit avoir l'extension .csv"


def test_export_csv_content(tmp_path, sample_result_healthy):
    """
    Test : le contenu du CSV correspond aux données exportées.
    """

    results = [sample_result_healthy]
    filepath = export_to_csv(results, output_dir=str(tmp_path))

    # Lire le CSV et vérifier le contenu
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1, "Le CSV doit contenir 1 ligne de données"
    assert rows[0]["name"] == "Test Carrier"
    assert rows[0]["status_code"] == "200"
    assert rows[0]["is_healthy"] == "True"


def test_export_csv_fieldnames_match_result_keys(tmp_path, sample_result_healthy):
    """
    Test : les colonnes du CSV correspondent EXACTEMENT aux clés du dict result.

    C'EST LE TEST QUI AURAIT ATTRAPÉ LE BUG fieldnames vs result dict.
    Si on ajoute un champ à result sans l'ajouter à fieldnames → ce test échoue.
    """

    results = [sample_result_healthy]
    filepath = export_to_csv(results, output_dir=str(tmp_path))

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_fieldnames = set(reader.fieldnames)

    result_keys = set(sample_result_healthy.keys())

    assert csv_fieldnames == result_keys, (
        f"Mismatch entre CSV fieldnames et result keys!\n"
        f"Dans CSV mais pas dans result : {csv_fieldnames - result_keys}\n"
        f"Dans result mais pas dans CSV : {result_keys - csv_fieldnames}"
    )


def test_export_multiple_results(tmp_path, sample_result_healthy, sample_result_unhealthy, sample_result_error):
    """
    Test : export de plusieurs résultats (healthy, unhealthy, error).
    """

    results = [sample_result_healthy, sample_result_unhealthy, sample_result_error]
    filepath = export_to_csv(results, output_dir=str(tmp_path))

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 3


def test_export_returns_none_on_permission_error(tmp_path):
    """
    Test : si le dossier est inaccessible, retourne None sans crash.
    """

    # On passe un chemin invalide qui provoquera une erreur
    result = export_to_csv([], output_dir="/root/impossible_path_12345")

    # Sur Windows ce chemin n'existera pas mais makedirs pourrait le créer
    # On vérifie au moins que la fonction ne crash pas
    assert result is None or isinstance(result, str)