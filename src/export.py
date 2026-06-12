# ============================================================================
# FICHIER : src/export.py
# RESPONSABILITÉ : export des résultats vers des fichiers
# MODIFICATION : logging remplace print()
# ============================================================================

import csv
import os
import logging
from datetime import datetime

# Logger spécifique à ce module → %(name)s affichera "src.export"
logger = logging.getLogger(__name__)


def export_to_csv(results: list[dict], output_dir: str = "output") -> str | None:
    """
    Exporte les résultats du health check dans un fichier CSV horodaté.
    """

    logger.info(f"Exporting results to CSV in {output_dir}/")

    # ---- NOUVEAU : gestion d'erreur sur l'écriture fichier ----
    # L'écriture peut échouer : permissions insuffisantes, disque plein, etc.
    try:
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"health_check_{timestamp}.csv")

        fieldnames = ["name", "url", "status_code", "response_time_ms", "is_healthy", "error", "expected_status", "attempts","max_latency_ms", "latency_warning"]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        # INFO : confirmation de succès (remplace le print())
        logger.info(f"Results exported to {filepath}")

        return filepath

    except PermissionError:
        # ERROR : le dossier/fichier n'est pas accessible en écriture
        logger.error(f"Permission denied: cannot write to {output_dir}/")
        return None

    except OSError as e:
        # ERROR : toute autre erreur liée au système de fichiers
        logger.error(f"Failed to export CSV: {e}")
        return None