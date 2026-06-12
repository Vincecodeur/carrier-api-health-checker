# ============================================================================
# FICHIER : src/cli.py
# RESPONSABILITÉ : définition et parsing des arguments de ligne de commande
# CONTIENT : parse_args()
# ============================================================================
#
# QU'EST-CE QU'UN ARGUMENT CLI (Command Line Interface) ?
#   Quand tu lances "python main.py --verbose", "--verbose" est un argument CLI.
#   C'est un moyen de paramétrer un script SANS modifier son code.
#
#   Il existe 2 types d'arguments :
#     - POSITIONNELS : obligatoires, identifiés par leur position
#       Ex : python script.py fichier.txt  → "fichier.txt" est positionnel
#     - OPTIONNELS : facultatifs, préfixés par -- (ou - en raccourci)
#       Ex : python script.py --verbose --config custom.json
#
# POURQUOI argparse (ET PAS sys.argv DIRECTEMENT) ?
#   sys.argv donne la liste brute des arguments : ["main.py", "--verbose"]
#   Tu devrais tout parser toi-même (vérifier les noms, les types, les défauts...).
#   argparse fait tout ça automatiquement + génère un --help gratuit.
# ============================================================================

# argparse est un module STANDARD (pas besoin de pip install).
# C'est LE module officiel pour parser les arguments CLI en Python.
# Alternatives tierces populaires : click, typer (plus modernes mais hors scope ici).
import argparse


def parse_args():
    """
    Définit et parse les arguments de ligne de commande.

    Ne prend aucun paramètre : argparse lit automatiquement sys.argv
    (la liste des arguments passés au script dans le terminal).

    Retourne :
        argparse.Namespace : un objet dont les attributs sont les arguments parsés.
        Exemple : args.config → "config/carriers.json"
                  args.verbose → True ou False
                  args.no_export → True ou False
                  args.output → "output"
    """

    # ---- CRÉATION DU PARSER ----
    # ArgumentParser est la classe principale d'argparse.
    # Elle crée un "parseur" qui va analyser les arguments du terminal.
    #
    # Paramètres :
    #   - prog : nom du programme affiché dans l'aide (--help)
    #   - description : texte affiché en haut du --help
    #   - epilog : texte affiché en bas du --help (exemples d'utilisation)
    #
    # formatter_class=RawDescriptionHelpFormatter :
    #   Par défaut, argparse reformate le texte (supprime les sauts de ligne).
    #   RawDescriptionHelpFormatter préserve le formatage exact de 'epilog',
    #   ce qui permet d'écrire des exemples proprement alignés.
    parser = argparse.ArgumentParser(
        prog="carrier-health-checker",
        description="🚚 Carrier API Health Checker — Anchanto Technical Partnerships",
        epilog="""
examples:
  python main.py                                   Run with default config
  python main.py --config config/prod.json         Use a custom config file
  python main.py --verbose                         Show detailed output per check
  python main.py --no-export                       Skip CSV export
  python main.py --output results/                 Export CSV to a custom folder
  python main.py --verbose --no-export             Combine multiple flags
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ---- DÉFINITION DES ARGUMENTS ----
    # Chaque appel à add_argument() définit UN argument que le script accepte.
    #
    # Structure générale :
    #   parser.add_argument(
    #       "nom_ou_flag",       → nom positionnel OU flag(s) optionnel(s)
    #       type=...,            → type Python attendu (str, int, float...)
    #       default=...,         → valeur par défaut si l'argument n'est pas fourni
    #       help=...,            → description affichée dans --help
    #       action=...,          → comportement spécial (store_true, count, append...)
    #   )

    # ARGUMENT 1 : --config / -c
    # Permet de spécifier un fichier de configuration différent.
    parser.add_argument(
        # "-c" est le raccourci (short flag) : python main.py -c custom.json
        # "--config" est le nom complet (long flag) : python main.py --config custom.json
        # Les deux sont interchangeables. Le nom de l'attribut dans args sera "config"
        # (argparse utilise le long flag sans les --, en remplaçant les - par des _).
        "-c", "--config",

        # type=str : l'argument est une chaîne de caractères.
        # argparse convertira automatiquement la valeur au type spécifié.
        # Si tu mettais type=int et que l'utilisateur passe "abc" → erreur automatique.
        type=str,

        # default : valeur utilisée si l'argument n'est PAS fourni dans le terminal.
        # Donc "python main.py" équivaut à "python main.py --config config/carriers.json"
        default="config/carriers.json",

        # metavar : nom affiché dans le --help pour représenter la valeur attendue.
        # Sans metavar, argparse afficherait "--config CONFIG" (le nom de la variable en majuscules).
        # Avec metavar="FILE", il affichera "--config FILE" → plus clair.
        metavar="FILE",

        # help : texte descriptif affiché dans le --help.
        # %(default)s est un placeholder spécial d'argparse qui sera remplacé
        # par la valeur de 'default' → affichera "(default: config/carriers.json)"
        help="Path to the carriers JSON config file (default: %(default)s)",
    )


    # ARGUMENT 2 : --verbose / -v
    # Active le mode détaillé (affiche les headers, expected_status, etc.)
    parser.add_argument(
        "-v", "--verbose",

        # action="store_true" : c'est un FLAG BOOLÉEN (pas de valeur attendue).
        # Si --verbose est présent → args.verbose = True
        # Si --verbose est absent  → args.verbose = False (le default implicite)
        #
        # Contrairement à type=str où l'utilisateur passe une valeur (--config fichier.json),
        # ici l'utilisateur écrit juste --verbose, sans rien après.
        action="store_true",

        help="Show detailed output for each carrier check",
    )

    # ARGUMENT 3 : --no-export
    # Désactive l'export CSV (utile pour un quick check sans polluer le dossier output/)
    parser.add_argument(
        "--no-export",

        # Même principe que --verbose : flag booléen sans valeur.
        action="store_true",

        # Note : le nom "--no-export" contient un tiret.
        # argparse le convertit en underscore pour l'attribut Python :
        # args.no_export (pas args.no-export, qui serait invalide en Python)
        help="Disable CSV export (dashboard display only)",
    )

    # ARGUMENT 4 : --output / -o
    # Permet de changer le dossier de sortie des fichiers CSV.
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output",
        metavar="DIR",
        help="Output directory for CSV export (default: %(default)s)",
    )

    # ---- PARSING ----
    # parse_args() lit sys.argv, analyse les arguments selon les règles définies,
    # et retourne un objet Namespace.
    #
    # Si l'utilisateur passe un argument inconnu (ex: --foo) → erreur automatique.
    # Si l'utilisateur passe --help ou -h → affiche l'aide et quitte (automatique aussi).
    #
    # L'objet retourné permet d'accéder aux valeurs avec la notation pointée :
    #   args.config     → str  ("config/carriers.json" ou la valeur custom)
    #   args.verbose    → bool (True si --verbose, sinon False)
    #   args.no_export  → bool (True si --no-export, sinon False)
    #   args.output     → str  ("output" ou la valeur custom)


    
  # ARGUMENT 5 : --log-level ----
    parser.add_argument(
        "--log-level",

        # type=str : la valeur est une chaîne
        type=str,

        # default="INFO" : niveau par défaut, bon compromis pour l'utilisation normale.
        # DEBUG serait trop bavard en usage courant.
        default="INFO",

        # choices : liste EXHAUSTIVE des valeurs autorisées.
        # Si l'utilisateur tape --log-level TOTO → argparse lève une erreur
        # automatiquement avec la liste des valeurs valides. Pas besoin de valider manuellement.
        #
        # C'est une fonctionnalité puissante d'argparse : la validation est déclarative.
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],

        # metavar remplace la liste des choices dans le --help.
        # Sans metavar, argparse afficherait : --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
        # Avec metavar="LEVEL" : --log-level LEVEL → plus propre, les choices sont dans le help text.
        metavar="LEVEL",

        help="Set logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: %(default)s)",
    )

    args = parser.parse_args()

    return args