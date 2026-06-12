# ============================================================================
# FICHIER : main.py
# RESPONSABILITÉ : point d'entrée — orchestre le pipeline
# MODIFICATION : initialisation du logger + try/except global
# ============================================================================

# ---- IMPORTS LOCAUX ----
# NOUVEAU : on importe setup_logger
from src.logger import setup_logger             # NOUVEAU → src/logger.py
from src.cli import parse_args
from src.config import load_config
from src.checker import run_health_checks
from src.display import display_dashboard
from src.export import export_to_csv

# On importe aussi logging pour le try/except global
import logging


def main():
    """
    Fonction principale — orchestre le pipeline complet.
    """

    # ---- ÉTAPE 0 (NOUVEAU) : Parser les args AVANT d'initialiser le logger ----
    # On a besoin de args.log_level pour configurer le logger.
    # Note : parse_args() n'a pas besoin du logger (argparse gère ses propres erreurs).
    args = parse_args()

    # ---- ÉTAPE 0bis (NOUVEAU) : Initialiser le système de logging ----
    #
    # setup_logger() DOIT être appelé UNE SEULE FOIS, AU TOUT DÉBUT.
    # Après cet appel, tous les modules peuvent utiliser logging.getLogger(__name__)
    # et leurs messages seront automatiquement envoyés aux handlers configurés.
    #
    # args.log_level vient du CLI : --log-level DEBUG / INFO / WARNING / ERROR / CRITICAL
    # Note : argparse stocke "--log-level" en tant que attribut "log_level" (tiret → underscore)
    setup_logger(log_level=args.log_level)

    # Maintenant on peut utiliser le logger dans main.py aussi
    logger = logging.getLogger(__name__)

    # ---- TRY / EXCEPT GLOBAL ----
    #
    # C'est le "filet de sécurité" ultime.
    # Si une exception non gérée remonte jusqu'ici, on la capture
    # et on affiche un message d'erreur propre au lieu d'un traceback brut.
    #
    # Les exceptions SPÉCIFIQUES (FileNotFoundError, JSONDecodeError...)
    # sont gérées dans leurs modules respectifs (config.py, export.py).
    # Ce try/except ne devrait attraper que les erreurs VRAIMENT inattendues.
    try:
        print("\n  🔧 Carrier API Health Checker v1.0")
        print("  Anchanto — Technical Partnerships")

        if args.verbose:
            print(f"\n  ⚙️  Config file:  {args.config}")
            print(f"  ⚙️  Verbose mode: ON")
            print(f"  ⚙️  Log level:    {args.log_level}")
            print(f"  ⚙️  CSV export:   {'OFF' if args.no_export else 'ON → ' + args.output}")

        # ÉTAPE 1 : Charger la config
        carriers = load_config(args.config)
        print(f"\n  📋 {len(carriers)} carriers loaded from config\n")

        # ÉTAPE 2 : Lancer les health checks
        results = run_health_checks(carriers, verbose=args.verbose)

        # ÉTAPE 3 : Afficher le dashboard
        display_dashboard(results, verbose=args.verbose)

        # ÉTAPE 4 : Exporter en CSV (conditionnel)
        if not args.no_export:
            export_to_csv(results, output_dir=args.output)
        else:
            print("  ⏭️  CSV export skipped (--no-export flag)")

    except SystemExit as e:
        # SystemExit est levé par nos propres modules (config.py) pour un arrêt propre.
        # On le laisse passer sans le traiter comme une "erreur inattendue".
        #
        # raise fait REMONTER l'exception au système.
        # Sans ce raise, le programme continuerait après le except
        # comme si de rien n'était — ce qu'on ne veut surtout pas.
        raise

    except Exception as e:
        # ---- FILET DE SÉCURITÉ ----
        # 'Exception' est la classe parente de presque toutes les exceptions Python.
        # Ce bloc attrape TOUT ce qui n'a pas été géré ailleurs.
        #
        # logger.exception() est spécial : il log le message en ERROR
        # ET ajoute automatiquement le TRACEBACK complet.
        # C'est l'équivalent de logger.error() + traceback intégré.
        # Le traceback sera visible dans le fichier de log (utile pour le debug)
        # et dans la console.
        logger.exception(f"Unexpected error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()