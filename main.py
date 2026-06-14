# ============================================================================
# FICHIER : main.py
# RESPONSABILITÉ : orchestration du pipeline complet
#
# VERSION : E4 — ajout du mode watch (--watch N)
#
# Le pipeline est encapsulé dans run_pipeline() pour pouvoir être appelé
# une seule fois (mode normal) ou en boucle (mode watch).
# ============================================================================


import sys
import time
import logging

from src.logger import setup_logger
from src.cli import parse_args
from src.config import load_config
from src.checker import run_health_checks
from src.display import display_dashboard, display_changes
from src.export import export_to_csv, export_to_json, export_to_html
from src.compare import find_previous_run, compare_results
from src.notify import send_teams_notification, should_notify
from src.version import VERSION, APP_NAME, AUTHOR
from dotenv import load_dotenv

load_dotenv()



def run_pipeline(args, carriers: list[dict], run_number: int = 1) -> list[dict]:
    """
    Exécute le pipeline complet une fois :
        1. Health checks
        2. Affichage dashboard
        3. Export (CSV/JSON/HTML)
        4. Comparaison historique
        5. Notification Teams

    Args:
        args:       Arguments CLI parsés (argparse.Namespace).
        carriers:   Liste de dicts transporteurs (chargée depuis carriers.json).
        run_number: Numéro du run (pour le mode watch).

    Returns:
        Liste de dicts résultats du health check.

    Cette fonction ne gère PAS l'exit code — c'est la responsabilité
    de main(). En mode watch, un carrier down ne doit pas arrêter la boucle.
    """

    logger = logging.getLogger(__name__)

    # ---- EN-TÊTE DU RUN (mode watch uniquement) ----
    if run_number > 1 or args.watch:
        print(f"\n{'=' * 80}")
        print(f"  🔄 Run #{run_number}")
        print(f"{'=' * 80}")

    # ---- ÉTAPE 1 : Health checks ----
    results, total_time_ms = run_health_checks(
        carriers,
        verbose=args.verbose,
        workers=args.workers,
        default_retries=args.retries,
        default_max_latency=args.max_latency,
    )

    # ---- ÉTAPE 2 : Affichage dashboard ----
    display_dashboard(
        results,
        verbose=args.verbose,
        total_time_ms=total_time_ms,
        workers=args.workers,
    )

    # ---- ÉTAPE 3 : Export (conditionnel) ----
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

    # ---- ÉTAPE 4 : Comparaison historique ----
    changes: list[dict] | None = None

    previous_run = find_previous_run(
        output_dir=args.output,
        exclude_file=exported_file if args.format == "json" else None,
    )

    if previous_run and "results" in previous_run:
        changes = compare_results(previous_run["results"], results)
        display_changes(changes)
    else:
        print("\n  ℹ️  No previous JSON run found — skipping comparison")

    # ---- ÉTAPE 5 : Notification Teams (conditionnelle) ----
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

    return results


def main() -> None:
    """
    Fonction principale — orchestre le pipeline complet.

    Deux modes de fonctionnement :
        - Mode normal (défaut) : run unique + exit code
        - Mode watch (--watch N) : boucle infinie, re-run toutes les N minutes

    Returns:
        None (point d'entrée du programme).
    """

    # ---- SETUP ----
    args = parse_args()
    
    # ---- VARIABLES D'ENVIRONNEMENT ----
    # Les flags CLI ont priorité sur les variables d'environnement.
    # Si --webhook-url est passé en CLI, on l'utilise.
    # Sinon, on regarde WEBHOOK_URL dans .env.
    # Sinon, pas de notification.
    import os

    if not args.webhook_url:
        args.webhook_url = os.environ.get("WEBHOOK_URL") or None

    if not args.format or args.format == "json":
        env_format = os.environ.get("EXPORT_FORMAT")
        if env_format and env_format in ("csv", "json", "html"):
            args.format = env_format

    if not args.watch:
        env_watch = os.environ.get("WATCH_INTERVAL")
        if env_watch and env_watch.isdigit():
            args.watch = int(env_watch)

    setup_logger(log_level=args.log_level)
    logger = logging.getLogger(__name__)

    # ---- BANNER ----
    print(f"\n  🔧 {APP_NAME} v{VERSION}")
    print(f"  {AUTHOR}")


    if args.verbose:
        print(f"\n  ⚙️  Config file:  {args.config}")
        print(f"  ⚙️  Verbose mode: ON")
        print(f"  ⚙️  Log level:    {args.log_level}")
        print(f"  ⚙️  Workers:      {args.workers}")
        print(f"  ⚙️  Retries:      {args.retries}")
        max_lat_display = f"{args.max_latency} ms" if args.max_latency > 0 else "disabled"
        print(f"  ⚙️  Max latency:  {max_lat_display}")
        print(f"  ⚙️  Export:       {'OFF' if args.no_export else f'ON → {args.output} ({args.format})'}")
        if args.watch:
            print(f"  ⚙️  Watch mode:  ON — every {args.watch} minute(s)")
        if args.webhook_url:
            
            masked = args.webhook_url[:20] + "..." if len(args.webhook_url) > 20 else args.webhook_url
            print(f"  ⚙️  Webhook:     {masked} (from {'CLI' if '--webhook-url' in sys.argv else '.env'})")


    # ---- CHARGER LA CONFIG ----
    # La config est chargée UNE SEULE FOIS, avant la boucle.
    # Si carriers.json change pendant le watch, il faut relancer le script.
    carriers = load_config(args.config)

    print(f"\n  📋 {len(carriers)} carriers loaded from config\n")

    # ---- WARNING : watch + no-export ----
    if args.watch and args.no_export:
        print("  ⚠️  Warning: watch mode without export — historical comparison won't work\n")

    # ---- MODE WATCH ----
    if args.watch:
        interval_seconds = args.watch * 60
        run_count = 0

        try:
            while True:
                run_count += 1

                try:
                    run_pipeline(args, carriers, run_number=run_count)
                except SystemExit:
                    # run_pipeline ne lève pas SystemExit, mais au cas où
                    # un module le ferait, on ne veut pas tuer le watch
                    logger.warning("SystemExit caught during watch run — continuing")
                except Exception as e:
                    # Filet de sécurité : si le pipeline crashe,
                    # on log l'erreur et on continue au prochain run.
                    # Le watch ne doit JAMAIS s'arrêter à cause d'un bug.
                    logger.error(f"Error during run #{run_count}: {e}")
                    print(f"\n  ⚠️  Run #{run_count} failed: {e}")

                # ---- ATTENTE ENTRE LES RUNS ----
                print(f"\n  ⏳ Next run in {args.watch} minute(s) (Ctrl+C to stop)...")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            # Ctrl+C propre — message de fin
            print(f"\n\n  🛑 Watch mode stopped by user ({run_count} run(s) completed)")

    # ---- MODE NORMAL (run unique) ----
    else:
        try:
            results = run_pipeline(args, carriers)

            # Exit code conditionnel (mode normal uniquement)
            unhealthy_count = sum(1 for r in results if not r["is_healthy"])
            error_count = sum(1 for r in results if r["error"])

            if unhealthy_count > 0 or error_count > 0:
                print(f"\n  ❌ {unhealthy_count + error_count} carrier(s) en échec — exit code 1")
                raise SystemExit(1)

        except SystemExit:
            raise
        except Exception as e:
            logger.critical(f"Fatal error: {e}")
            raise SystemExit(1)


if __name__ == "__main__":
    main()