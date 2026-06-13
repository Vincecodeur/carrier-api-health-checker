# ============================================================================
# FICHIER : src/compare.py
# RESPONSABILITÉ : comparer les résultats actuels avec le run précédent
#
# Ce module détecte les TRANSITIONS entre deux runs :
#   - Un carrier qui tombe (healthy → unhealthy/error)
#   - Un carrier qui se rétablit (unhealthy/error → healthy)
#   - Une latence qui se dégrade ou s'améliore significativement
#   - Un carrier ajouté ou supprimé de la config
#
# Il ne modifie rien, ne fait pas d'appel HTTP, ne fait pas d'export.
# Il prend deux listes de résultats et retourne une liste de changements.
# ============================================================================

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def find_previous_run(output_dir: str = "output", exclude_file: str | None = None) -> dict | None:
    """
    Trouve et charge le fichier JSON du run précédent.

    Scanne le dossier output/ à la recherche de fichiers health_check_*.json,
    les trie par nom (qui contient un timestamp → tri chronologique),
    et retourne le contenu du plus récent.

    Args:
        output_dir:   Dossier contenant les fichiers d'export.
        exclude_file: Chemin du fichier du run actuel à exclure de la recherche.

    Returns:
        Dictionnaire contenant les données du run précédent, ou None si aucun
        fichier trouvé.

    Concept nouveau — pathlib.Path :
        Path est la manière MODERNE de manipuler les chemins en Python.
        Plus lisible que os.path :
            Path("output").glob("*.json")   vs   glob.glob(os.path.join("output", "*.json"))
            file.stem                        vs   os.path.splitext(os.path.basename(file))[0]
            file.name                        vs   os.path.basename(file)
    """

    output_path = Path(output_dir)

    # Vérifier que le dossier existe
    if not output_path.exists():
        logger.debug(f"Output directory {output_dir} does not exist")
        return None

    # Trouver tous les fichiers health_check_*.json
    # .glob() retourne un générateur de Path objects qui matchent le pattern
    json_files = sorted(output_path.glob("health_check_*.json"))

    # Exclure le fichier du run actuel s'il est spécifié
    # On compare les chemins résolus (absolus) pour éviter les problèmes
    # de chemins relatifs vs absolus
    if exclude_file:
        exclude_path = Path(exclude_file).resolve()
        json_files = [f for f in json_files if f.resolve() != exclude_path]

    # Si aucun fichier restant → pas de run précédent
    if not json_files:
        logger.debug("No previous JSON run found")
        return None

    # Prendre le dernier fichier (le plus récent chronologiquement)
    # Les fichiers sont nommés health_check_YYYYMMDD_HHMMSS.json
    # → le tri alphabétique = tri chronologique
    previous_file = json_files[-1]

    logger.info(f"Loading previous run from: {previous_file.name}")

    try:
        with open(previous_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load previous run: {e}")
        return None


def compare_results(previous_results: list[dict], current_results: list[dict], latency_threshold: float = 50.0) -> list[dict]:
    """
    Compare les résultats du run précédent avec les résultats actuels.

    Détecte 6 types de changements :
        - NEW_DOWN:  carrier healthy → unhealthy ou error
        - RECOVERED: carrier unhealthy/error → healthy
        - DEGRADED:  latence augmentée de plus de latency_threshold %
        - IMPROVED:  latence diminuée de plus de latency_threshold %
        - NEW:       carrier présent dans current mais pas dans previous
        - REMOVED:   carrier présent dans previous mais pas dans current

    Args:
        previous_results: Liste de dicts résultats du run précédent.
        current_results:  Liste de dicts résultats du run actuel.
        latency_threshold: Seuil de variation de latence en % pour déclencher
                           un changement DEGRADED/IMPROVED (défaut: 50%).

    Returns:
        Liste de dicts, chaque dict décrivant un changement détecté :
        {
            "type": "NEW_DOWN" | "RECOVERED" | "DEGRADED" | "IMPROVED" | "NEW" | "REMOVED",
            "carrier": "Colissimo SLS",
            "details": "HTTP 200 → HTTP 500",
            "previous_value": ...,
            "current_value": ...,
        }
    """

    changes = []

    # ---- INDEXER PAR NOM ----
    # On crée un dict {nom_carrier: résultat} pour chaque run.
    # Ça permet de retrouver un carrier par son nom en O(1).
    prev_by_name = {r["name"]: r for r in previous_results}
    curr_by_name = {r["name"]: r for r in current_results}

    # ---- DÉTECTER LES CARRIERS SUPPRIMÉS ----
    # Présents dans previous mais pas dans current
    for name in prev_by_name:
        if name not in curr_by_name:
            changes.append({
                "type": "REMOVED",
                "carrier": name,
                "details": "Carrier removed from config",
                "previous_value": None,
                "current_value": None,
            })

    # ---- COMPARER CHAQUE CARRIER ACTUEL ----
    for name, curr in curr_by_name.items():

        # Carrier nouveau (pas dans le run précédent)
        if name not in prev_by_name:
            changes.append({
                "type": "NEW",
                "carrier": name,
                "details": f"New carrier added — {'HEALTHY' if curr.get('is_healthy') else 'UNHEALTHY'}",
                "previous_value": None,
                "current_value": curr.get("status_code"),
            })
            continue

        prev = prev_by_name[name]

        # ---- CHANGEMENT DE STATUT ----
        prev_healthy = prev.get("is_healthy", False)
        curr_healthy = curr.get("is_healthy", False)
        prev_error = prev.get("error")
        curr_error = curr.get("error")

        # Healthy → Unhealthy ou Error (NOUVEAU DOWN)
        if prev_healthy and not curr_healthy:
            if curr_error:
                details = f"HEALTHY → ERROR ({curr_error})"
            else:
                details = f"HTTP {prev.get('status_code')} → HTTP {curr.get('status_code')} (unexpected)"
            changes.append({
                "type": "NEW_DOWN",
                "carrier": name,
                "details": details,
                "previous_value": prev.get("status_code"),
                "current_value": curr.get("status_code") or curr_error,
            })

        # Unhealthy ou Error → Healthy (RÉTABLI)
        elif not prev_healthy and curr_healthy:
            if prev_error:
                details = f"ERROR ({prev_error}) → HEALTHY (HTTP {curr.get('status_code')})"
            else:
                details = f"HTTP {prev.get('status_code')} (unhealthy) → HTTP {curr.get('status_code')} (healthy)"
            changes.append({
                "type": "RECOVERED",
                "carrier": name,
                "details": details,
                "previous_value": prev.get("status_code") or prev_error,
                "current_value": curr.get("status_code"),
            })

        # ---- CHANGEMENT DE LATENCE ----
        # Seulement si les deux runs ont une latence mesurable
        # et que le carrier est healthy dans les deux cas
        prev_latency = prev.get("response_time_ms")
        curr_latency = curr.get("response_time_ms")

        if (prev_latency and curr_latency
                and prev_healthy and curr_healthy
                and prev_latency > 0):

            # Calculer le pourcentage de variation
            # (curr - prev) / prev * 100
            # Positif = dégradation, négatif = amélioration
            change_pct = ((curr_latency - prev_latency) / prev_latency) * 100

            if change_pct > latency_threshold:
                changes.append({
                    "type": "DEGRADED",
                    "carrier": name,
                    "details": f"{prev_latency:.0f} ms → {curr_latency:.0f} ms (+{change_pct:.0f}%)",
                    "previous_value": prev_latency,
                    "current_value": curr_latency,
                })

            elif change_pct < -latency_threshold:
                changes.append({
                    "type": "IMPROVED",
                    "carrier": name,
                    "details": f"{prev_latency:.0f} ms → {curr_latency:.0f} ms ({change_pct:.0f}%)",
                    "previous_value": prev_latency,
                    "current_value": curr_latency,
                })

    return changes