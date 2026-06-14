# ============================================================================
# FICHIER : src/export.py
# RESPONSABILITÉ : export des résultats vers des fichiers
# MODIFICATION : logging remplace print()
# ============================================================================

import csv
import json
import logging
import os
from datetime import datetime

from src.version import APP_NAME, AUTHOR, VERSION

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

        fieldnames = [
            "name",
            "url",
            "status_code",
            "response_time_ms",
            "is_healthy",
            "error",
            "expected_status",
            "attempts",
            "max_latency_ms",
            "latency_warning",
        ]

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
            "tool": APP_NAME,
            "version": VERSION,
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


def export_to_html(results: list[dict], output_dir: str = "output") -> str | None:
    """
    Exporte les résultats du health check dans un fichier HTML autonome.

    Le fichier HTML contient :
        - Un en-tête avec le titre et le timestamp
        - Un tableau coloré avec une ligne par carrier
        - Un résumé (healthy, unhealthy, errors, latency warnings)
        - Du CSS inline (pas de fichier externe nécessaire)

    Args:
        results:    Liste de dicts résultats à exporter.
        output_dir: Dossier de destination du fichier HTML.

    Returns:
        Chemin du fichier HTML créé, ou None en cas d'erreur.
    """

    logger.info(f"Exporting results to HTML in {output_dir}/")

    try:
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"health_check_{timestamp}.html")

        # ---- COMPTAGES POUR LE RÉSUMÉ ----
        total = len(results)
        healthy = sum(1 for r in results if r.get("is_healthy"))
        unhealthy = sum(1 for r in results if not r.get("is_healthy") and not r.get("error"))
        errors = sum(1 for r in results if r.get("error"))
        latency_warnings = sum(1 for r in results if r.get("latency_warning"))

        # ---- CONSTRUIRE LES LIGNES DU TABLEAU ----
        #
        # Pour chaque résultat, on génère une ligne <tr> avec :
        #   - Une couleur de fond selon le statut
        #   - Un emoji de statut
        #   - Le nom, l'URL, le status code, la latence, le verdict
        rows_html = ""

        for r in results:
            # Déterminer la couleur et l'icône
            if r.get("error"):
                bg_color = "#fde8e8"  # Rouge clair
                icon = "🔴"
                status_text = r["error"]
                latency_text = "N/A"
            elif r.get("is_healthy") and r.get("latency_warning"):
                bg_color = "#fff3e0"  # Orange clair
                icon = "🟠"
                status_text = f"HTTP {r['status_code']} (slow)"
                latency_text = f"{r['response_time_ms']} ms ⚠️ > {r.get('max_latency_ms', '?')} ms"
            elif r.get("is_healthy"):
                bg_color = "#e8f5e9"  # Vert clair
                icon = "🟢"
                status_text = f"HTTP {r['status_code']}"
                latency_text = f"{r['response_time_ms']} ms"
            else:
                bg_color = "#fffde7"  # Jaune clair
                icon = "🟡"
                status_text = f"HTTP {r['status_code']} (unexpected)"
                latency_text = f"{r['response_time_ms']} ms"

            # Nombre de tentatives
            attempts = r.get("attempts", 1)
            attempts_text = f"{attempts} (retried {attempts - 1}x)" if attempts > 1 else "1"

            # Construire la ligne HTML
            rows_html += f"""
            <tr style="background-color: {bg_color};">
                <td>{icon}</td>
                <td><strong>{r["name"]}</strong></td>
                <td style="font-size: 0.85em; color: #666;">{r["url"]}</td>
                <td>{status_text}</td>
                <td>{latency_text}</td>
                <td>{attempts_text}</td>
            </tr>"""

        # ---- ASSEMBLER LE HTML COMPLET ----
        #
        # Tout le CSS est inline dans une balise <style>.
        # Pas de fichier CSS externe → le HTML est 100% autonome.
        # On peut l'ouvrir dans n'importe quel navigateur,
        # l'envoyer par email, le partager sur Teams.
        report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Carrier Health Check — {report_time}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #1a237e;
            margin-bottom: 5px;
        }}
        .subtitle {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 25px;
        }}
        .summary {{
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }}
        .summary-card {{
            padding: 15px 25px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 1.1em;
        }}
        .card-healthy {{ background-color: #e8f5e9; color: #2e7d32; }}
        .card-unhealthy {{ background-color: #fffde7; color: #f57f17; }}
        .card-error {{ background-color: #fde8e8; color: #c62828; }}
        .card-slow {{ background-color: #fff3e0; color: #e65100; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th {{
            background-color: #1a237e;
            color: white;
            padding: 12px 15px;
            text-align: left;
            font-size: 0.9em;
        }}
        td {{
            padding: 10px 15px;
            border-bottom: 1px solid #e0e0e0;
        }}
        tr:hover {{
            filter: brightness(0.97);
        }}
        .footer {{
            margin-top: 25px;
            text-align: center;
            color: #999;
            font-size: 0.8em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚚 Carrier API Health Dashboard</h1>
        <div class="subtitle">Anchanto — Technical Partnerships • {report_time}</div>

        <div class="summary">
            <div class="summary-card card-healthy">🟢 Healthy: {healthy}/{total}</div>
            {"<div class='summary-card card-unhealthy'>🟡 Unhealthy: " + str(unhealthy) + "</div>" if unhealthy > 0 else ""}
            {"<div class='summary-card card-error'>🔴 Errors: " + str(errors) + "</div>" if errors > 0 else ""}
            {"<div class='summary-card card-slow'>🟠 Slow: " + str(latency_warnings) + "</div>" if latency_warnings > 0 else ""}
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 40px;"></th>
                    <th>Carrier</th>
                    <th>URL</th>
                    <th>Status</th>
                    <th>Latency</th>
                    <th>Attempts</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div class="footer">
            Generated by {APP_NAME} v{VERSION} — {AUTHOR}
        </div>
    </div>
</body>
</html>"""

        # ---- ÉCRIRE LE FICHIER ----
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Results exported to {filepath}")
        return filepath

    except PermissionError:
        logger.error(f"Permission denied: cannot write to {output_dir}/")
        return None

    except OSError as e:
        logger.error(f"Failed to export HTML: {e}")
        return None
