# ============================================================================
# FICHIER : src/cli.py
# MODIFICATION : ajout du flag --workers
# ============================================================================

import argparse


def parse_args():
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
  python main.py --workers 1                       Sequential mode (no parallelism)
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

    # ---- NOUVEAU : --workers / -w ----
    parser.add_argument(
        "-w", "--workers",

        # type=int : argparse convertit automatiquement la valeur en entier.
        # Si l'utilisateur passe "abc" → erreur automatique : "invalid int value"
        type=int,

        # default=5 : bon compromis.
        # 5 threads suffisent pour 6 carriers (quasiment tout en parallèle).
        # Pas trop élevé pour éviter de surcharger le réseau ou de se faire bloquer
        # par les serveurs (rate limiting).
        default=5,

        metavar="N",

        help="Number of parallel workers/threads for health checks (default: %(default)s). "
             "Use 1 for sequential mode.",
    )

    args = parser.parse_args()
    return args