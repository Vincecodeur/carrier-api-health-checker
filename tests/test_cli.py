# ============================================================================
# FICHIER : tests/test_cli.py
# RESPONSABILITÉ : tester le module src/cli.py
# ============================================================================

import pytest
from unittest.mock import patch
from src.cli import parse_args


class TestParseArgs:

    @patch("sys.argv", ["main.py"])
    def test_default_values(self):
        """Sans arguments, les valeurs par défaut sont correctes."""

        args = parse_args()

        assert args.config == "config/carriers.json"
        assert args.verbose is False
        assert args.no_export is False
        assert args.output == "output"
        assert args.log_level == "INFO"
        assert args.workers == 5
        assert args.retries == 2
        assert args.max_latency == 0
        assert args.format == "json"

    @patch("sys.argv", ["main.py", "--verbose", "--no-export"])
    def test_boolean_flags(self):
        """Les flags booléens (store_true) fonctionnent."""

        args = parse_args()

        assert args.verbose is True
        assert args.no_export is True

    @patch("sys.argv", ["main.py", "--workers", "10", "--retries", "3"])
    def test_integer_arguments(self):
        """Les arguments entiers sont correctement parsés."""

        args = parse_args()

        assert args.workers == 10
        assert args.retries == 3

    @patch("sys.argv", ["main.py", "--log-level", "DEBUG"])
    def test_log_level_choices(self):
        """--log-level accepte les valeurs autorisées."""

        args = parse_args()
        assert args.log_level == "DEBUG"

    @patch("sys.argv", ["main.py", "--log-level", "INVALID"])
    def test_invalid_log_level_exits(self):
        """Une valeur invalide pour --log-level → SystemExit."""

        with pytest.raises(SystemExit):
            parse_args()

    @patch("sys.argv", ["main.py", "-v", "-c", "custom.json", "-w", "3", "-r", "1"])
    def test_short_flags(self):
        """Les raccourcis (-v, -c, -w, -r) fonctionnent."""

        args = parse_args()

        assert args.verbose is True
        assert args.config == "custom.json"
        assert args.workers == 3
        assert args.retries == 1

    @patch("sys.argv", ["main.py", "--max-latency", "500"])
    def test_max_latency(self):
        """--max-latency est correctement parsé."""

        args = parse_args()
        assert args.max_latency == 500

    # ------------------------------------------------------------------
    # NOUVEAU — Tests pour --format
    # ------------------------------------------------------------------

    @patch("sys.argv", ["main.py", "--format", "json"])
    def test_format_json(self):
        """--format json est correctement parsé."""

        args = parse_args()
        assert args.format == "json"

    @patch("sys.argv", ["main.py", "-f", "json"])
    def test_format_short_flag(self):
        """Le raccourci -f fonctionne."""

        args = parse_args()
        assert args.format == "json"

    @patch("sys.argv", ["main.py", "--format", "xml"])
    def test_invalid_format_exits(self):
        """--format xml (invalide) → SystemExit."""

        with pytest.raises(SystemExit):
            parse_args()

# NOUVEAU — test pour --format html
    @patch("sys.argv", ["main.py", "--format", "html"])
    def test_format_html(self):
        """--format html est correctement parsé."""

        args = parse_args()
        assert args.format == "html"


    