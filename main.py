# ============================================================================
# FICHIER : main.py
# MODIFICATION : passage de workers + adaptation au tuple de retour
# ============================================================================

from src.logger import setup_logger
from src.cli import parse_args
from src.config import load_config
from src.checker import run_health_checks
from src.display import display_dashboard
from src.export import export_to_csv

import logging


def main():
    """
    Fonction principale — orchestre le pipeline complet.
    """

    args = parse_args()
    setup_logger(log_level=args.log_level)
    logger = logging.getLogger(__name__)

    try:
        print("\n  🔧 Carrier API Health Checker v1.0")
        print("  Anchanto — Technical Partnerships")

        if args.verbose:
            print(f"\n  ⚙️  Config file:  {args.config}")
            print(f"  ⚙️  Verbose mode: ON")
            print(f"  ⚙️  Log level:    {args.log_level}")
            print(f"  ⚙️  Workers:      {args.workers}")
            print(f"  ⚙️  CSV export:   {'OFF' if args.no_export else 'ON → ' + args.output}")

        # ÉTAPE 1 : Charger la config
        carriers = load_config(args.config)
        print(f"\n  📋 {len(carriers)} carriers loaded from config\n")

        # ÉTAPE 2 : Lancer les health checks
        # AVANT : results = run_health_checks(carriers, verbose=args.verbose)
        # APRÈS : on "unpack" le tuple retourné (results, total_time_ms)
        #
        # C'est du "tuple unpacking" :
        #   La fonction retourne (results, total_time_ms)
        #   On assigne chaque élément à une variable séparée en une seule ligne.
        #   Équivalent de :
        #     result_tuple = run_health_checks(...)
        #     results = result_tuple[0]
        #     total_time_ms = result_tuple[1]
        results, total_time_ms = run_health_checks(
            carriers,
            verbose=args.verbose,
            workers=args.workers,
        )

        # ÉTAPE 3 : Afficher le dashboard
        # AVANT : display_dashboard(results, verbose=args.verbose)
        # APRÈS : on passe aussi total_time_ms et workers pour l'affichage
        display_dashboard(
            results,
            verbose=args.verbose,
            total_time_ms=total_time_ms,
            workers=args.workers,
        )

        # ÉTAPE 4 : Exporter en CSV (conditionnel)
        if not args.no_export:
            export_to_csv(results, output_dir=args.output)
        else:
            print("  ⏭️  CSV export skipped (--no-export flag)")

    except SystemExit:
        raise

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()