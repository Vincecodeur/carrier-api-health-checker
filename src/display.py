# ============================================================================
# FICHIER : src/display.py
# RESPONSABILITÉ : affichage du dashboard
# MODIFICATION : le mode verbose affiche maintenant les détails complets
#                (expected status, verdict, perf) — triés dans l'ordre config
# ============================================================================

from datetime import datetime


def display_dashboard(results, verbose=False, total_time_ms=None, workers=None):
    """
    Affiche un dashboard formaté dans le terminal.

    Paramètres :
        results (list)          : liste de dicts de résultats (triés dans l'ordre config)
        verbose (bool)          : mode détaillé — affiche expected status, verdict, perf
        total_time_ms (float)   : temps total d'exécution en ms
        workers (int)           : nombre de threads utilisés
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

        # ---- AFFICHAGE DE BASE (toujours) ----
        print(f"\n  {status_icon} {r['name']}")
        print(f"     URL:      {r['url']}")
        print(f"     Status:   {status_text}")
        print(f"     Latency:  {time_text}")

        # ---- AFFICHAGE VERBOSE (détails complets) ----
        #
        # AVANT : le verbose n'ajoutait que l'indicateur de perf (Fast/Normal/Slow).
        #         Les infos de verdict et expected status étaient dans checker.py
        #         → affichées dans le désordre en mode parallèle.
        #
        # APRÈS : tout le détail est ICI, dans le dashboard, qui est DÉJÀ TRIÉ
        #         dans l'ordre de la config. Plus de désordre.
        #
        # Infos ajoutées en verbose :
        #   - Expected : les status codes considérés sains pour ce carrier
        #   - Verdict  : HEALTHY/UNHEALTHY avec l'explication (code ∈ ou ∉ expected)
        #   - Perf     : indicateur de performance basé sur la latence
        if verbose:

            # ---- Expected status codes ----
            # On récupère cette info depuis le dict result.
            # PROBLÈME : le dict result actuel ne contient pas expected_status.
            # Il contient name, url, status_code, response_time_ms, is_healthy, error.
            #
            # SOLUTION : on a deux options :
            #   a) Ajouter expected_status au dict result dans checker.py
            #   b) Recalculer ici
            #
            # On choisit (a) car c'est plus propre : le result contient TOUTE l'info
            # nécessaire pour l'affichage, sans dépendance externe.
            # → Voir la modification dans checker.py : result["expected_status"] ajouté.
            expected = r.get("expected_status", [])
            if expected:
                print(f"     Expected: {expected}")

            # ---- Verdict explicite ----
            # Explique POURQUOI le carrier est healthy ou non.
            # C'est pédagogique pour l'utilisateur qui découvre le health checking.
            if r["error"]:
                print(f"     Verdict:  ❌ ERROR — no HTTP response received")
            elif r["is_healthy"]:
                print(f"     Verdict:  ✅ HEALTHY ({r['status_code']} ∈ {expected})")
            else:
                print(f"     Verdict:  ⚠️  UNHEALTHY ({r['status_code']} ∉ {expected})")

            # ---- Indicateur de performance ----
            if r["response_time_ms"] is not None:
                latency = r["response_time_ms"]
                if latency < 200:
                    perf = "⚡ Fast"
                elif latency < 500:
                    perf = "✅ Normal"
                elif latency < 1000:
                    perf = "⚠️  Slow"
                else:
                    perf = "🐌 Very slow"
                print(f"     Perf:     {perf}")

    # ---- RÉSUMÉ ----
    healthy = sum(1 for r in results if r["is_healthy"])
    total = len(results)
    errors = sum(1 for r in results if r["error"])

    print("\n" + "-" * 80)
    print(f"  📊 Summary: {healthy}/{total} carriers healthy")

    if total_time_ms is not None:
        individual_sum = sum(
            r["response_time_ms"] for r in results
            if r["response_time_ms"] is not None
        )
        individual_sum = round(individual_sum, 2)

        if total_time_ms > 0:
            speedup = round(individual_sum / total_time_ms, 1)
        else:
            speedup = 0

        mode = f"parallel ({workers} workers)" if workers and workers > 1 else "sequential"
        print(f"  ⏱️  Total time: {total_time_ms} ms ({mode})")
        print(f"  📈 Sum of individual latencies: {individual_sum} ms — speedup: {speedup}x")

    if verbose:
        print(f"  🔴 Errors: {errors}")

        latencies = [r["response_time_ms"] for r in results if r["response_time_ms"] is not None]
        if latencies:
            avg = round(sum(latencies) / len(latencies), 2)
            fastest = round(min(latencies), 2)
            slowest = round(max(latencies), 2)
            print(f"  ⏱️  Avg latency: {avg} ms (fastest: {fastest} ms / slowest: {slowest} ms)")

    print("=" * 80 + "\n")