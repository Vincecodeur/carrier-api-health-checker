# ============================================================================
# FICHIER : src/display.py
# RESPONSABILITÉ : affichage des résultats dans le terminal
# CONTIENT : display_dashboard()
# MODIFICATION : ajout du mode verbose (latence moyenne, seuils de performance)
# ============================================================================

from datetime import datetime


def display_dashboard(results, verbose=False):
    """
    Affiche un dashboard formaté dans le terminal.

    Paramètres :
        results (list)  : liste de dicts de résultats
        verbose (bool)  : si True, affiche des métriques supplémentaires
    """

    print("\n" + "=" * 80)
    print(f"  🚚 CARRIER API HEALTH DASHBOARD — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    for r in results:

        if r["error"]:
            status_icon = "🔴"
            status_text = f"ERROR ({r['error']})"
            time_text = "N/A"
        elif r["is_healthy"]:
            status_icon = "🟢"
            status_text = f"HTTP {r['status_code']}"
            time_text = f"{r['response_time_ms']} ms"
        else:
            status_icon = "🟡"
            status_text = f"HTTP {r['status_code']} (unexpected)"
            time_text = f"{r['response_time_ms']} ms"

        print(f"\n  {status_icon} {r['name']}")
        print(f"     URL:      {r['url']}")
        print(f"     Status:   {status_text}")
        print(f"     Latency:  {time_text}")

        # ---- NOUVEAU : indicateur de performance en mode verbose ----
        # On catégorise le temps de réponse pour donner un repère visuel.
        # Ces seuils sont des conventions courantes en monitoring d'API :
        #   < 200ms  = rapide (très bon)
        #   < 500ms  = normal (acceptable)
        #   < 1000ms = lent (à surveiller)
        #   ≥ 1000ms = très lent (problème probable)
        if verbose and r["response_time_ms"] is not None:
            latency = r["response_time_ms"]
            if latency < 200:
                perf = "⚡ Fast"
            elif latency < 500:
                perf = "✅ Normal"
            elif latency < 1000:
                perf = "⚠️  Slow"
            else:
                perf = "🐌 Very slow"
            print(f"     Perf:     {perf} ({latency} ms)")

    # Résumé
    healthy = sum(1 for r in results if r["is_healthy"])
    total = len(results)
    errors = sum(1 for r in results if r["error"])

    print("\n" + "-" * 80)
    print(f"  📊 Summary: {healthy}/{total} carriers healthy")

    # ---- NOUVEAU : métriques supplémentaires en mode verbose ----
    if verbose:
        # Comptage des erreurs réseau (timeout, connexion...)
        print(f"  🔴 Errors: {errors}")

        # Calcul de la latence moyenne sur les checks réussis (sans erreur).
        #
        # Décomposition de la ligne :
        #   [r["response_time_ms"] for r in results if r["response_time_ms"] is not None]
        #
        #   C'est une LIST COMPREHENSION — un idiome Python très puissant :
        #     - for r in results              → itère sur chaque résultat
        #     - if r["response_time_ms"]...   → filtre : ne garde que ceux avec un temps
        #     - r["response_time_ms"]         → extrait la valeur pour chaque élément filtré
        #
        #   Résultat : une liste de floats, ex: [133.48, 271.64, 388.67, 112.03, 95.66, 274.44]
        latencies = [r["response_time_ms"] for r in results if r["response_time_ms"] is not None]

        if latencies:
            # sum(latencies) / len(latencies) = moyenne arithmétique
            avg = round(sum(latencies) / len(latencies), 2)

            # min() et max() retournent les valeurs extrêmes d'une liste
            fastest = round(min(latencies), 2)
            slowest = round(max(latencies), 2)

            print(f"  ⏱️  Avg latency: {avg} ms (fastest: {fastest} ms / slowest: {slowest} ms)")

    print("=" * 80 + "\n")