# ============================================================================
# FICHIER : src/cli.py
# MODIFICATION : ajout du flag --max-latency
# ============================================================================

import argparse


def parse_args()-> argparse.Namespace:
    """
    Définit et parse les arguments de ligne de commande.
    """

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
  python main.py --log-level DEBUG                 Show all log messages
  python main.py --workers 10                      Use 10 parallel threads
  python main.py --retries 3                       Retry failed checks up to 3 times
  python main.py --max-latency 500                 Warn if any carrier exceeds 500ms
  python main.py --max-latency 0                   Disable latency warnings
  python main.py --format json                     Export results as JSON
  python main.py --format csv                      Export results as CSV (default)
  python main.py --webhook-url "https://..."       Send Teams alert if carriers fail
  python main.py --format html                     Export results as HTML dashboard
  python main.py --watch 5                         Re-run every 5 minutes (Ctrl+C to stop)
  python main.py --watch 1 --verbose               Watch mode with verbose output
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-c", "--config",
        type=str,
        default="config/carriers.json",
        metavar="FILE",
        help="Path to the carriers JSON config file (default: %(default)s)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output for each carrier check",
    )

    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Disable CSV export (dashboard display only)",
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output",
        metavar="DIR",
        help="Output directory for CSV export (default: %(default)s)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        metavar="LEVEL",
        help="Set logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: %(default)s)",
    )

    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=5,
        metavar="N",
        help="Number of parallel workers/threads for health checks (default: %(default)s). "
             "Use 1 for sequential mode.",
    )

    parser.add_argument(
        "-r", "--retries",
        type=int,
        default=2,
        metavar="N",
        help="Default number of retries for failed checks (default: %(default)s). "
             "Can be overridden per carrier in config. Use 0 for no retries.",
    )

    # ---- NOUVEAU : --max-latency ----
    parser.add_argument(
        "--max-latency",
        type=int,
        # default=0 : désactivé par défaut.
        # Les seuils sont définis dans carriers.json par carrier.
        # Ce flag ne sert que de fallback global pour les carriers
        # qui n'ont pas de max_latency_ms dans le JSON.
        # 0 = pas de seuil → latency_warning sera toujours False.
        default=0,
        metavar="MS",
        help="Default max latency threshold in ms (default: %(default)s = disabled). "
             "Carriers exceeding this will be flagged. "
             "Can be overridden per carrier in config.",
    )

    
# ---- NOUVEAU : --format ----
    parser.add_argument(
        "-f", "--format",
        type=str,
        default="json",
        choices=["csv", "json", "html"],
        metavar="FORMAT",
        help="Export format: csv or json or html (default: %(default)s).",
    )

   # ---- NOUVEAU : --webhook-url ----
    parser.add_argument(
        "--webhook-url",
        type=str,
        default=None,
        metavar="URL",
        help="Teams webhook URL for notifications. If not set, no notification is sent.",
    )


# ---- NOUVEAU : --watch ----
    parser.add_argument(
        "-W", "--watch",
        type=int,
        default=None,
        metavar="MINUTES",
        help="Watch mode: re-run health checks every N minutes. Ctrl+C to stop.",
    )


    args = parser.parse_args()
    return args