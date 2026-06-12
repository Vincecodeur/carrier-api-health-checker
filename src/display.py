# ============================================================================
# FICHIER : src/display.py
# MODIFICATION : affichage du nombre de tentatives en mode verbose
# ============================================================================

from datetime import datetime


def display_dashboard(results, verbose=False, total_time_ms=None, workers=None):
    """
    Affiche un dashboard formaté dans le terminal.
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

        # Affichage de base
        print(f"\n  {status_icon} {r['name']}")
        print(f"     URL:      {r['url']}")
        print(f"     Status:   {status_text}")
        print(f"     Latency:  {time_text}")

        # ---- NOUVEAU : affichage du nombre de tentatives ----
        #
        # On n'affiche le nombre de tentatives QUE si un retry a eu lieu (attempts > 1).
        # Si tout passe du premier coup, on ne pollue pas l'affichage.
        # Ce champ est visible même hors verbose car c'est une info opérationnelle importante :
        # si un carrier nécessite 3 tentatives, c'est un signal d'instabilité.
        attempts = r.get("attempts", 1)
        if attempts > 1:
            print(f"     Attempts: {attempts} (retried {attempts - 1}x)")

        # Affichage verbose
        if verbose:
            expected = r.get("expected_status", [])
            if expected:
                print(f"     Expected: {expected}")

            if r["error"]:
                print(f"     Verdict:  ❌ ERROR — no HTTP response received")
            elif r["is_healthy"]:
                print(f"     Verdict:  ✅ HEALTHY ({r['status_code']} ∈ {expected})")
            else:
                print(f"     Verdict:  ⚠️  UNHEALTHY ({r['status_code']} ∉ {expected})")

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

    # Résumé
    healthy = sum(1 for r in results if r["is_healthy"])
    total = len(results)
    errors = sum(1 for r in results if r["error"])

    # ---- NOUVEAU : compteur de retries dans le résumé ----
    total_retries = sum(max(0, r.get("attempts", 1) - 1) for r in results)

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

    # Affiche le nombre total de retries s'il y en a eu
    if total_retries > 0:
        print(f"  🔄 Total retries: {total_retries}")

    if verbose:
        print(f"  🔴 Errors: {errors}")

        latencies = [r["response_time_ms"] for r in results if r["response_time_ms"] is not None]
        if latencies:
            avg = round(sum(latencies) / len(latencies), 2)
            fastest = round(min(latencies), 2)
            slowest = round(max(latencies), 2)
            print(f"  ⏱️  Avg latency: {avg} ms (fastest: {fastest} ms / slowest: {slowest} ms)")

    print("=" * 80 + "\n")