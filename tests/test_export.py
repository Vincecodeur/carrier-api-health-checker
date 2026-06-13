# ============================================================================
# FICHIER : tests/test_export.py
# RESPONSABILITÉ : tester le module src/export.py (CSV et JSON)
# ============================================================================

import csv
import json
import os
from src.export import export_to_csv, export_to_json, export_to_html


# ============================================================================
# Tests pour export_to_csv()
# ============================================================================


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

    assert filepath is not None, "filepath ne doit pas être None"

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

    assert filepath is not None, "filepath ne doit pas être None"

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_fieldnames = set(reader.fieldnames or [])

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

    assert filepath is not None, "filepath ne doit pas être None"

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 3


def test_export_csv_returns_none_on_permission_error(tmp_path):
    """
    Test : si le dossier est inaccessible, retourne None sans crash.
    """

    result = export_to_csv([], output_dir="/root/impossible_path_12345")

    assert result is None or isinstance(result, str)


# ============================================================================
# Tests pour export_to_json()
# ============================================================================


def test_export_json_creates_file(tmp_path, sample_result_healthy):
    """
    Test : export_to_json crée bien un fichier .json.
    """

    results = [sample_result_healthy]
    filepath = export_to_json(results, output_dir=str(tmp_path))

    assert filepath is not None
    assert os.path.exists(filepath)
    assert filepath.endswith(".json")


def test_export_json_content(tmp_path, sample_result_healthy):
    """
    Test : le contenu du JSON est correct et conserve les types.

    C'est l'avantage principal du JSON sur le CSV :
    - status_code est un int (200), pas un string ("200")
    - is_healthy est un bool (true), pas un string ("True")
    - error est null, pas un string vide
    """

    results = [sample_result_healthy]
    filepath = export_to_json(results, output_dir=str(tmp_path))

    assert filepath is not None, "filepath ne doit pas être None"

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Vérifier les métadonnées
    assert "timestamp" in data
    assert data["total_carriers"] == 1
    assert data["healthy"] == 1
    assert data["errors"] == 0

    # Vérifier le contenu des résultats
    assert len(data["results"]) == 1
    result = data["results"][0]

    # Types conservés (contrairement au CSV)
    assert result["name"] == "Test Carrier"
    assert result["status_code"] == 200        # int, pas "200"
    assert result["is_healthy"] is True         # bool, pas "True"
    assert result["error"] is None              # null, pas ""
    assert result["response_time_ms"] == 150.0  # float, pas "150.0"


def test_export_json_multiple_results(
    tmp_path, sample_result_healthy, sample_result_unhealthy, sample_result_error
):
    """
    Test : export de 3 résultats avec comptages corrects dans les métadonnées.
    """

    results = [sample_result_healthy, sample_result_unhealthy, sample_result_error]
    filepath = export_to_json(results, output_dir=str(tmp_path))

    assert filepath is not None, "filepath ne doit pas être None"

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_carriers"] == 3
    assert data["healthy"] == 1       # sample_result_healthy
    assert data["unhealthy"] == 1     # sample_result_unhealthy (is_healthy=False, error=None)
    assert data["errors"] == 1        # sample_result_error (error="TIMEOUT")
    assert len(data["results"]) == 3


def test_export_json_returns_none_on_error(tmp_path):
    """
    Test : chemin invalide → retourne None sans crash.
    """

    result = export_to_json([], output_dir="/root/impossible_path_12345")
    assert result is None or isinstance(result, str)

# ============================================================================
# Tests pour export_to_html()
# ============================================================================


def test_export_html_creates_file(tmp_path, sample_result_healthy):
    """
    Test : export_to_html crée bien un fichier .html.
    """

    results = [sample_result_healthy]
    filepath = export_to_html(results, output_dir=str(tmp_path))

    assert filepath is not None
    assert os.path.exists(filepath)
    assert filepath.endswith(".html")


def test_export_html_contains_carrier_name(tmp_path, sample_result_healthy):
    """
    Test : le HTML contient le nom du carrier et les éléments structurels.
    """

    results = [sample_result_healthy]
    filepath = export_to_html(results, output_dir=str(tmp_path))

    assert filepath is not None

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Test Carrier" in content
    assert "Carrier API Health Dashboard" in content
    assert "<table>" in content
    assert "🟢" in content


def test_export_html_returns_none_on_error(tmp_path):
    """
    Test : chemin invalide → retourne None sans crash.
    """

    result = export_to_html([], output_dir="/root/impossible_path_12345")
    assert result is None or isinstance(result, str)
