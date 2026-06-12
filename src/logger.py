# ============================================================================
# FICHIER : src/logger.py
# RESPONSABILITÉ : configuration centralisée du système de logging
# CONTIENT : setup_logger()
# ============================================================================
#
# CE MODULE EST LE PREMIER APPELÉ AU DÉMARRAGE DU SCRIPT.
# Il configure UNE SEULE FOIS le logging pour tout le projet.
# Tous les autres modules utiliseront ensuite logging.getLogger(__name__)
# pour écrire des logs — sans avoir besoin de reconfigurer quoi que ce soit.
#
# VOCABULAIRE LOGGING :
#   - Logger    : l'objet qui écrit les messages (logging.getLogger())
#   - Handler   : la destination des messages (console, fichier, réseau...)
#   - Formatter : le format du message (timestamp, niveau, texte...)
#   - Level     : le seuil minimum de sévérité affiché (DEBUG, INFO, WARNING...)
#
# ANALOGIE :
#   Logger    = un journaliste qui rédige des articles
#   Handler   = les journaux qui publient (Le Monde, Le Figaro...)
#   Formatter = la mise en page de chaque journal (colonnes, titres...)
#   Level     = la politique éditoriale (on ne publie que les scoops, ou tout ?)
# ============================================================================

# 'logging' est un module STANDARD (pas de pip install).
# C'est le système de logging officiel de Python, utilisé par
# quasiment toutes les librairies et tous les projets professionnels.
import logging

# 'os' pour créer le dossier logs/ s'il n'existe pas
import os

# 'datetime' pour horodater le nom du fichier de log
from datetime import datetime


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """
    Configure le système de logging pour tout le projet.

    Paramètre :
        log_level (str) : niveau minimum de log à afficher.
                          Valeurs possibles : "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
                          Défaut : "INFO"

    Retourne :
        logging.Logger : le logger racine configuré

    Fonctionnement :
        Après l'appel à setup_logger(), N'IMPORTE QUEL MODULE du projet
        peut écrire des logs en faisant :
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Mon message")
        Les messages seront automatiquement envoyés aux handlers configurés ici.
    """

    # ---- ÉTAPE 1 : Créer le dossier logs/ ----
    # Même logique que pour output/ dans export.py
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Nom du fichier de log horodaté (un nouveau fichier par exécution)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"health_check_{timestamp}.log")

    # ---- ÉTAPE 2 : Récupérer le logger RACINE ----
    #
    # logging.getLogger() SANS argument retourne le logger RACINE (root logger).
    # C'est le logger parent de tous les autres loggers du projet.
    #
    # Hiérarchie des loggers :
    #   root (racine)
    #   ├── src.config      (créé par getLogger(__name__) dans config.py)
    #   ├── src.checker     (créé par getLogger(__name__) dans checker.py)
    #   ├── src.export      (créé par getLogger(__name__) dans export.py)
    #   └── ...
    #
    # Les messages des loggers enfants REMONTENT automatiquement au root logger.
    # En configurant le root logger ici, on configure TOUT le projet d'un coup.
    logger = logging.getLogger()

    # ---- ÉTAPE 3 : Définir le niveau minimum du logger ----
    #
    # getattr(logging, log_level.upper()) convertit une chaîne en constante logging :
    #   "DEBUG"    → logging.DEBUG    (valeur numérique : 10)
    #   "INFO"     → logging.INFO     (valeur numérique : 20)
    #   "WARNING"  → logging.WARNING  (valeur numérique : 30)
    #   "ERROR"    → logging.ERROR    (valeur numérique : 40)
    #   "CRITICAL" → logging.CRITICAL (valeur numérique : 50)
    #
    # getattr(objet, nom_attribut) est une fonction built-in Python qui retourne
    # la valeur d'un attribut d'un objet à partir de son NOM en string.
    # C'est utile quand le nom de l'attribut est dynamique (vient d'un argument CLI).
    #
    # Exemple : getattr(logging, "INFO") équivaut à logging.INFO
    #
    # Le niveau du logger détermine le seuil MINIMUM :
    #   - Si level = INFO → les messages DEBUG sont IGNORÉS
    #   - Si level = WARNING → DEBUG et INFO sont IGNORÉS
    #   - Si level = DEBUG → TOUT est affiché
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # ---- ÉTAPE 4 : Supprimer les handlers existants ----
    #
    # POURQUOI ? Si setup_logger() est appelé plusieurs fois (ex: dans des tests),
    # les handlers s'accumulent et chaque message s'affiche en double, triple...
    # logger.handlers est une LISTE de tous les handlers attachés au logger.
    # .clear() vide cette liste. C'est une mesure de sécurité.
    logger.handlers.clear()

    # ---- ÉTAPE 5 : Créer les FORMATTERS ----
    #
    # Un Formatter définit le FORMAT du message de log.
    # C'est un template avec des placeholders spéciaux :
    #
    #   %(asctime)s    → timestamp "2026-06-12 17:45:00"
    #   %(name)s       → nom du logger ("src.checker", "src.config"...)
    #   %(levelname)s  → niveau en texte ("INFO", "WARNING", "ERROR"...)
    #   %(message)s    → le message que tu as écrit
    #
    # On crée DEUX formatters différents :
    #   - Un pour la console (court, lisible)
    #   - Un pour le fichier (complet, avec le nom du module)

    # Formatter console : compact, pas de nom de module (le terminal est déjà chargé)
    # Exemple de sortie : "2026-06-12 17:45:00 | INFO | 6 carriers loaded"
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        #                   %(levelname)-8s
        #                               ^^
        #                               |└── largeur minimale de 8 caractères
        #                               └── aligné à gauche (le - signifie left-align)
        #   Résultat : "INFO    " ou "WARNING " ou "ERROR   " → colonnes alignées

        datefmt="%Y-%m-%d %H:%M:%S",
        #   datefmt remplace le format par défaut de %(asctime)s
        #   Sans datefmt, le timestamp inclut les millisecondes : "2026-06-12 17:45:00,123"
        #   Avec datefmt, on garde un format propre sans les millisecondes
    )

    # Formatter fichier : complet, avec le nom du module source
    # Exemple de sortie : "2026-06-12 17:45:00 | INFO     | src.checker | 6 carriers loaded"
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        #                                   %(name)s → identifie QUEL module a écrit ce log
        #   En production, c'est indispensable pour retrouver l'origine d'un problème.
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ---- ÉTAPE 6 : Créer le HANDLER CONSOLE ----
    #
    # StreamHandler() envoie les logs vers un "stream" (flux de sortie).
    # Sans argument, il utilise sys.stderr (la sortie d'erreur standard).
    #
    # POURQUOI stderr et pas stdout ?
    #   - stdout (print) → pour les données/résultats du programme
    #   - stderr (logging) → pour les messages techniques/diagnostics
    #   Ça permet de séparer les deux : python main.py > results.txt
    #   → les logs techniques restent visibles dans le terminal
    #   → seul le dashboard va dans le fichier results.txt
    console_handler = logging.StreamHandler()

    # On attache le formatter console à ce handler
    console_handler.setFormatter(console_formatter)

    # On peut aussi définir un niveau SPÉCIFIQUE par handler.
    # Ici on met le même niveau que le logger racine.
    # Mais on pourrait mettre WARNING pour la console et DEBUG pour le fichier
    # → la console n'affiche que les problèmes, le fichier capture tout.
    console_handler.setLevel(numeric_level)

    # ---- ÉTAPE 7 : Créer le HANDLER FICHIER ----
    #
    # FileHandler() envoie les logs dans un fichier.
    # Paramètres :
    #   - log_file      → chemin du fichier de log
    #   - encoding="utf-8" → supporte les caractères spéciaux
    #
    # Le fichier est créé automatiquement s'il n'existe pas.
    # Les messages sont ajoutés à la fin (mode append par défaut).
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(file_formatter)

    # Le handler fichier capture TOUT (DEBUG+), quel que soit le niveau console.
    # C'est une bonne pratique : le fichier sert d'archive complète pour le debug,
    # même si la console n'affiche que les WARNING+.
    file_handler.setLevel(logging.DEBUG)

    # ---- ÉTAPE 8 : Attacher les handlers au logger racine ----
    #
    # addHandler() connecte un handler au logger.
    # Un logger peut avoir PLUSIEURS handlers (ici : console + fichier).
    # Chaque message de log sera envoyé à TOUS les handlers attachés.
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # On log un premier message pour confirmer que le système fonctionne
    # et pour tracer la configuration active dans le fichier de log.
    logger.debug(f"Logging initialized — level: {log_level}, file: {log_file}")

    return logger