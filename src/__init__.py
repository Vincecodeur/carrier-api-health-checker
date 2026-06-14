# ============================================================================
# FICHIER : src/__init__.py
# ============================================================================
#
# CE FICHIER EST VIDE (ou presque) — et c'est NORMAL.
#
# RÔLE :
#   Sa simple EXISTENCE transforme le dossier "src/" en un "package Python".
#   Sans ce fichier, Python ne reconnaît pas "src" comme un package
#   et les imports du type "from src.config import load_config" échoueront
#   avec une erreur ModuleNotFoundError.
#
# QU'EST-CE QU'UN PACKAGE PYTHON ?
#   - Un MODULE = un fichier .py unique (ex: config.py)
#   - Un PACKAGE = un dossier contenant un __init__.py + des modules
#   - Un package permet de regrouper des modules liés et de les importer
#     avec une notation à points : from package.module import fonction
#
# ANALOGIE :
#   Pense à __init__.py comme la porte d'entrée d'un immeuble.
#   Sans porte, tu ne peux pas entrer dans les appartements (modules).
#   La porte peut être vide (juste une ouverture) ou contenir du code
#   qui s'exécute à l'import du package.
#
# CONTENU POSSIBLE (optionnel, pour plus tard) :
#   - Des imports de raccourci : from src.config import load_config
#     → permettrait d'écrire "from src import load_config" directement
#   - Une variable __version__ = "1.0.0"
#   - Du code d'initialisation du package
#
# Pour l'instant, on le laisse vide. C'est la pratique la plus courante.
# ============================================================================
