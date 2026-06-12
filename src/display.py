# ============================================================================
# FICHIER : src/display.py
# MODIFICATION : icône 🟠 pour healthy+slow, affichage du seuil en verbose,
#                compteur de latency warnings dans le résumé
# ============================================================================

from datetime import datetime



def display_dashboard(
    results: list[dict],
    verbose: bool = False,
    total_time_ms: float | None = None,
    workers: int | None = None,
) -> None:

    """
    Affiche un dashboard formaté dans le terminal.
    """

    print("\n" + "=" * 80)
    print(f"  🚚 CARRIER API HEALTH DASHBOARD — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    for r in results:

        # ---- LOGIQUE D'ICÔNE ENRICHIE ----
        #
        # AVANT : 3 cas (error, healthy, unhealthy)
        # APRÈS : 4 cas (error, healthy+slow, healthy, unhealthy)
        #
        # L'icône 🟠 est un signal intermédiaire :
        #   🟢 = tout va bien
        #   🟠 = ça marche mais c'est lent (à surveiller)
        #   🟡 = status code inattendu
        #   🔴 = erreur réseau (timeout, connexion...)
        if r["error"]:
            status_icon = "🔴"
            status_text = f"ERROR ({r['error']})"
            time_text = "N/A"
        elif r["is_healthy"] and r.get("latency_warning"):
            # NOUVEAU : healthy mais latence trop élevée
            status_icon = "🟠"
            status_text = f"HTTP {r['status_code']} (slow)"
            time_text = f"{r['response_time_ms']} ms ⚠️  > {r.get('max_latency_ms', '?')} ms"
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

        # Attempts (inchangé)
        attempts = r.get("attempts", 1)
        if attempts > 1:
            print(f"     Attempts: {attempts} (retried {attempts - 1}x)")

        # Affichage verbose
        if verbose:
            expected = r.get("expected_status", [])
            if expected:
                print(f"     Expected: {expected}")

            # ---- NOUVEAU : affichage du seuil de latence en verbose ----
            max_lat = r.get("max_latency_ms", 0)
            if max_lat > 0:
                print(f"     Max lat:  {max_lat} ms")

            # Verdict (enrichi avec le cas latency_warning)
            if r["error"]:
                print(f"     Verdict:  ❌ ERROR — no HTTP response received")
            elif r["is_healthy"] and r.get("latency_warning"):
                print(f"     Verdict:  ✅ HEALTHY but ⚠️  SLOW ({r['response_time_ms']} ms > {max_lat} ms)")
            elif r["is_healthy"]:
                print(f"     Verdict:  ✅ HEALTHY ({r['status_code']} ∈ {expected})")
            else:
                print(f"     Verdict:  ⚠️  UNHEALTHY ({r['status_code']} ∉ {expected})")

            # Perf indicator (inchangé)
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
    total_retries = sum(max(0, r.get("attempts", 1) - 1) for r in results)

    # NOUVEAU : compteur de latency warnings
    latency_warnings = sum(1 for r in results if r.get("latency_warning"))

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

    if total_retries > 0:
        print(f"  🔄 Total retries: {total_retries}")

    # NOUVEAU : affichage du nombre de latency warnings s'il y en a
    if latency_warnings > 0:
        print(f"  🟠 Latency warnings: {latency_warnings}")

    if verbose:
        print(f"  🔴 Errors: {errors}")

        latencies = [r["response_time_ms"] for r in results if r["response_time_ms"] is not None]
        if latencies:
            avg = round(sum(latencies) / len(latencies), 2)
            fastest = round(min(latencies), 2)
            slowest = round(max(latencies), 2)
            print(f"  ⏱️  Avg latency: {avg} ms (fastest: {fastest} ms / slowest: {slowest} ms)")

    print("=" * 80 + "\n")