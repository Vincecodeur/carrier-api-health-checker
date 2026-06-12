# ============================================================================
# FICHIER : src/export.py
# RESPONSABILITÉ : export des résultats vers des fichiers
# MODIFICATION : logging remplace print()
# ============================================================================

import csv
import json
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

    
def export_to_json(results: list[dict], output_dir: str = "output") -> str | None:
    """
    Exporte les résultats du health check dans un fichier JSON horodaté.

    Args:
        results:    Liste de dicts résultats à exporter.
        output_dir: Dossier de destination du fichier JSON.

    Returns:
        Chemin du fichier JSON créé, ou None en cas d'erreur.

    Le JSON conserve les types natifs Python :
        - int (status_code: 200, pas "200")
        - float (response_time_ms: 150.0, pas "150.0")
        - bool (is_healthy: true, pas "True")
        - null (error: null, pas "")
        - list (expected_status: [200, 401], pas "[200, 401]")

    C'est un avantage sur le CSV où tout est converti en string.
    """

    logger.info(f"Exporting results to JSON in {output_dir}/")

    try:
        # ---- CRÉER LE DOSSIER ----
        # Même logique que export_to_csv : exist_ok=True évite l'erreur
        # si le dossier existe déjà.
        os.makedirs(output_dir, exist_ok=True)

        # ---- CONSTRUIRE LE NOM DU FICHIER ----
        # Même convention que le CSV : health_check_YYYYMMDD_HHMMSS.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"health_check_{timestamp}.json")

        # ---- CONSTRUIRE LA STRUCTURE JSON ----
        #
        # On n'écrit pas juste la liste brute des résultats.
        # On l'enveloppe dans un objet avec des métadonnées :
        #   - timestamp : quand le check a été exécuté
        #   - total_carriers : combien de carriers ont été testés
        #   - healthy : combien sont healthy
        #   - results : la liste des résultats
        #
        # Pourquoi ? Parce qu'un fichier JSON doit être auto-descriptif.
        # Si quelqu'un ouvre le fichier dans 6 mois, il comprend
        # immédiatement ce que c'est sans contexte extérieur.
        output = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_carriers": len(results),
            "healthy": sum(1 for r in results if r.get("is_healthy")),
            "unhealthy": sum(1 for r in results if not r.get("is_healthy") and not r.get("error")),
            "errors": sum(1 for r in results if r.get("error")),
            "results": results,
        }

        # ---- ÉCRIRE LE FICHIER ----
        #
        # json.dump(data, file) écrit directement dans le fichier.
        #
        # Paramètres :
        #   indent=2         → formatage lisible (2 espaces par niveau)
        #   ensure_ascii=False → conserve les accents (é, è, ç) au lieu
        #                        de les convertir en \u00e9
        #   default=str      → si une valeur n'est pas sérialisable
        #                       (ex: datetime, set), elle est convertie
        #                       en string au lieu de lever TypeError
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Results exported to {filepath}")
        return filepath

    except PermissionError:
        logger.error(f"Permission denied: cannot write to {output_dir}/")
        return None

    except OSError as e:
        logger.error(f"Failed to export JSON: {e}")
        return None
