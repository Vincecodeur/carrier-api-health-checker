# ============================================================================
# FICHIER : tests/test_config.py
# RESPONSABILITÉ : tester le module src/config.py
#
# On teste 4 scénarios :
#   1. Chargement réussi d'un fichier JSON valide
#   2. Fichier introuvable → SystemExit
#   3. JSON invalide → SystemExit
#   4. Clé "carriers" manquante → SystemExit
# ============================================================================

import pytest
import json
import os
from src.config import load_config


def test_load_config_success(tmp_path):
    """
    Test : chargement d'un fichier JSON valide.

    tmp_path est une FIXTURE BUILT-IN de pytest.
    Elle crée un dossier temporaire unique pour chaque test.
    Les fichiers créés dedans sont automatiquement nettoyés après le test.
    C'est la méthode standard pour tester des opérations fichier.
    """

    # ARRANGE — préparer les données
    # On crée un fichier carriers.json temporaire avec 2 carriers
    config_data = {
        "carriers": [
            {"name": "Carrier A", "url": "https://a.com", "expected_status": [200], "timeout": 5},
            {"name": "Carrier B", "url": "https://b.com", "expected_status": [200, 401], "timeout": 10},
        ]
    }

    # tmp_path / "carriers.json" crée un chemin dans le dossier temporaire
    config_file = tmp_path / "carriers.json"

    # Écrire le fichier JSON
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    # ACT — exécuter la fonction testée
    result = load_config(str(config_file))

    # ASSERT — vérifier le résultat
    # assert est le mot-clé central des tests.
    # Si la condition est True → le test PASSE.
    # Si la condition est False → le test ÉCHOUE avec un message détaillé.
    assert isinstance(result, list), "Le résultat doit être une liste"
    assert len(result) == 2, "La liste doit contenir 2 carriers"
    assert result[0]["name"] == "Carrier A"
    assert result[1]["url"] == "https://b.com"


def test_load_config_file_not_found():
    """
    Test : le fichier n'existe pas → doit lever SystemExit.

    pytest.raises() est un context manager qui VÉRIFIE qu'une exception
    est levée. Si l'exception n'est PAS levée → le test ÉCHOUE.
    C'est l'inverse d'un assert classique : on VEUT que ça plante.
    """

    with pytest.raises(SystemExit):
        load_config("config/this_file_does_not_exist.json")


def test_load_config_invalid_json(tmp_path):
    """
    Test : le fichier existe mais contient du JSON invalide.
    """

    # Écrire du contenu non-JSON
    config_file = tmp_path / "bad.json"
    config_file.write_text("{ this is not valid json !!!", encoding="utf-8")

    with pytest.raises(SystemExit):
        load_config(str(config_file))


def test_load_config_missing_carriers_key(tmp_path):
    """
    Test : JSON valide mais la clé "carriers" est absente.
    """

    config_data = {"transporteurs": []}  # Mauvaise clé
    config_file = tmp_path / "wrong_key.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    with pytest.raises(SystemExit):
        load_config(str(config_file))


def test_load_config_empty_carriers(tmp_path):
    """
    Test : JSON valide avec une liste vide de carriers.
    Ne doit PAS lever d'exception — retourne une liste vide.
    """

    config_data = {"carriers": []}
    config_file = tmp_path / "empty.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    result = load_config(str(config_file))

    assert isinstance(result, list)
    assert len(result) == 0