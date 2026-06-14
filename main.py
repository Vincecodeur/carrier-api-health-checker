# ============================================================================
# FICHIER : main.py
# MODIFICATION : passage de args.retries à run_health_checks()
# ============================================================================

from src.logger import setup_logger
from src.cli import parse_args
from src.config import load_config
from src.checker import run_health_checks
from src.display import display_dashboard, display_changes
from src.export import export_to_csv, export_to_json, export_to_html
from src.compare import find_previous_run, compare_results
from src.notify import send_teams_notification, should_notify



import logging


def main()-> None:
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
            print(f"  ⚙️  Retries:      {args.retries}")
            max_lat_display = f"{args.max_latency} ms" if args.max_latency > 0 else "disabled"
            print(f"  ⚙️  Max latency:  {max_lat_display}")
            print(f"  ⚙️  Export:       {'OFF' if args.no_export else f'ON → {args.output} ({args.format})'}")



        # ÉTAPE 1 : Charger la config
        carriers = load_config(args.config)
        print(f"\n  📋 {len(carriers)} carriers loaded from config\n")

        # ÉTAPE 2 : Lancer les health checks
        # MODIFIÉ : on passe default_retries=args.retries
        results, total_time_ms = run_health_checks(
            carriers,
            verbose=args.verbose,
            workers=args.workers,
            default_retries=args.retries,
            default_max_latency=args.max_latency,
        )

        # ÉTAPE 3 : Afficher le dashboard
        display_dashboard(
            results,
            verbose=args.verbose,
            total_time_ms=total_time_ms,
            workers=args.workers,
        )


# ÉTAPE 4 : Exporter (conditionnel)
        if not args.no_export:
            if args.format == "json":
                exported_file = export_to_json(results, output_dir=args.output)
            elif args.format == "html":
                exported_file = export_to_html(results, output_dir=args.output)
            else:
                exported_file = export_to_csv(results, output_dir=args.output)
        else:
            exported_file = None
            print("  ⏭️  Export skipped (--no-export flag)")

        # ÉTAPE 4b : Comparaison avec le run précédent
        #
        # On cherche le dernier fichier JSON dans output/.
        # Si on vient d'exporter en JSON, on exclut ce fichier
        # pour ne pas comparer le run avec lui-même.
        #
        # La comparaison fonctionne QUEL QUE SOIT le format d'export actuel :
        # même avec --format csv ou --format html, on peut comparer
        # avec un ancien fichier JSON s'il existe.
        previous_run = find_previous_run(
            output_dir=args.output,
            exclude_file=exported_file if args.format == "json" else None,
        )

        if previous_run and "results" in previous_run:
            changes = compare_results(previous_run["results"], results)
            display_changes(changes)
        else:
            changes = None
            print("\n  ℹ️  No previous JSON run found — skipping comparison")


        # ÉTAPE 4c : Notification Teams (conditionnelle)
        #
        # On envoie une notification seulement si :
        #   1. --webhook-url est fourni
        #   2. should_notify() retourne True (échec ou changement critique)
        #
        # Si le webhook n'est pas configuré → on skip silencieusement.
        # Si l'envoi échoue → on log un warning mais le script continue.
        if args.webhook_url:
            if should_notify(results, changes):
                success = send_teams_notification(
                    webhook_url=args.webhook_url,
                    results=results,
                    changes=changes,
                )
                if success:
                    print("  📨 Teams notification sent")
                else:
                    print("  ⚠️  Teams notification failed (see logs)")
            else:
                logger.info("All carriers healthy, no critical changes — notification skipped")


        # ÉTAPE 5 : Exit code conditionnel
        unhealthy_count = sum(1 for r in results if not r["is_healthy"])
        error_count = sum(1 for r in results if r["error"])

        if unhealthy_count > 0 or error_count > 0:
            print(f"\n  ❌ {unhealthy_count + error_count} carrier(s) en échec — exit code 1")
            raise SystemExit(1)

   

    except SystemExit:
        raise

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()