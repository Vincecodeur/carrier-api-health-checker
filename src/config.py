# ============================================================================
# FICHIER : src/config.py
# RESPONSABILITÉ : chargement de la configuration
# MODIFICATION : logging remplace print() + gestion d'erreurs robuste
# ============================================================================

import json
import logging

# ---- CRÉATION DU LOGGER DU MODULE ----
#
# logging.getLogger(__name__) crée un logger spécifique à CE module.
#
# __name__ est une variable spéciale Python qui contient le nom du module :
#   - Si ce fichier est src/config.py → __name__ = "src.config"
#   - Si ce fichier est exécuté directement → __name__ = "__main__"
#
# Ce logger est un ENFANT du logger racine configuré dans setup_logger().
# Tous les messages écrits ici remontent automatiquement au root logger
# et sont envoyés à ses handlers (console + fichier).
#
# POURQUOI un logger par module (et pas un logger global) ?
#   Le champ %(name)s dans le formatter affichera "src.config",
#   ce qui permet d'identifier immédiatement QUEL module a écrit le message.
#   En production, quand tu lis un fichier de 500 lignes de log, c'est indispensable.
logger = logging.getLogger(__name__)


def load_config(filepath: str) -> list[dict]:
    """
    Charge la configuration des transporteurs depuis un fichier JSON.

    Paramètre :
        filepath (str) : chemin vers le fichier JSON

    Retourne :
        list : liste de dicts transporteurs

    Lève :
        SystemExit : si le fichier est introuvable, invalide, ou mal structuré
    """

    # ---- TRY / EXCEPT AVEC GESTION PROPRE DES ERREURS ----
    #
    # AVANT (étape 2) : aucun try/except → crash brut avec traceback Python
    # APRÈS : on attrape chaque type d'erreur et on affiche un message clair
    #
    # Le script QUITTE proprement au lieu de cracher un traceback incompréhensible.
    # C'est la différence entre un script de dev et un outil professionnel.

    # logger.info() écrit un message de niveau INFO.
    # Ce message sera affiché en console ET écrit dans le fichier de log.
    logger.info(f"Loading config from: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)

        carriers = config["carriers"]

        # ---- VALIDATION SUPPLÉMENTAIRE ----
        # On vérifie que la liste n'est pas vide.
        # Un fichier JSON valide avec "carriers": [] ne ferait pas planter le script
        # mais produirait un dashboard vide — autant prévenir l'utilisateur.
        if not carriers:
            # logger.warning() → niveau WARNING : pas bloquant mais anormal
            logger.warning("Config file is valid but contains 0 carriers")

        # logger.info() pour confirmer le succès
        logger.info(f"Successfully loaded {len(carriers)} carriers")

        # logger.debug() → niveau DEBUG : détail technique, visible uniquement avec --log-level DEBUG
        # Utile pour le développeur, pas pour l'utilisateur final.
        for carrier in carriers:
            logger.debug(f"  Loaded carrier: {carrier['name']} → {carrier['url']}")

        return carriers

    except FileNotFoundError:
        # AVANT : crash avec "FileNotFoundError: [Errno 2] No such file or directory"
        # APRÈS : message clair + arrêt propre

        # logger.critical() → niveau CRITICAL : le programme ne peut pas continuer
        logger.critical(f"Config file not found: {filepath}")
        logger.critical("Please check the path or use --config to specify another file")

        # ---- sys.exit() vs raise ----
        # raise FileNotFoundError → relance l'exception (traceback affiché)
        # sys.exit(1) → quitte le programme proprement avec un code de sortie
        #
        # Le code de sortie est une convention :
        #   0 = succès (tout s'est bien passé)
        #   1 = erreur générique
        #   2 = erreur d'usage (mauvais arguments)
        #
        # On utilise raise SystemExit(1) plutôt que sys.exit(1) pour éviter
        # d'importer sys juste pour ça. Les deux font exactement la même chose.
        raise SystemExit(1)

    except json.JSONDecodeError as e:
        # Le fichier existe mais son contenu n'est pas du JSON valide.
        # Ex : accolades manquantes, virgule en trop, commentaires (// ...)
        logger.critical(f"Invalid JSON in config file: {filepath}")
        logger.critical(f"Parse error: {e}")
        raise SystemExit(1)

    except KeyError:
        # Le JSON est valide mais ne contient pas la clé "carriers".
        # Ex : {"transporteurs": [...]} au lieu de {"carriers": [...]}
        logger.critical(f"Missing 'carriers' key in config file: {filepath}")
        logger.critical("Expected structure: {\"carriers\": [...]}")
        raise SystemExit(1)