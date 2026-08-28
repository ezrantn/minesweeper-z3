"""
Analisis statistik dari hasil eksperimen: Wilson score interval dan
bootstrap confidence interval untuk win rate per run, dan Top-K accuracy
per run. Baca experiment_results.csv & llm_decisions.csv, tidak menjalankan
simulasi apapun.

Pakai stdlib doang (csv, math, random, collections) biar gak nambah
dependency baru ke proyek.
"""
import csv
import math
import random
import sys
from collections import defaultdict

RESULTS_CSV = "experiment_results.csv"
DECISIONS_CSV = "llm_decisions.csv"
SUMMARY_CSV = "analysis_summary.csv"

Z_95 = 1.959963985


def wilson_ci(successes, n, z=Z_95):
    """Wilson score interval. Lebih akurat dari normal approx untuk n kecil / p ekstrem."""
    if n == 0:
        return 0.0, 0.0, 0.0

    phat = successes / n
    denom = 1 + z ** 2 / n
    center = phat + z ** 2 / (2 * n)
    margin = z * math.sqrt(phat * (1 - phat) / n + z ** 2 / (4 * n ** 2))

    low = max(0.0, (center - margin) / denom)
    high = min(1.0, (center + margin) / denom)
    return phat, low, high


def bootstrap_ci(outcomes, n_boot=2000, confidence=0.95, seed=42):
    """Bootstrap resampling CI dari list outcome biner (0/1)."""
    n = len(outcomes)
    if n == 0:
        return 0.0, 0.0, 0.0

    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = rng.choices(outcomes, k=n)
        means.append(sum(sample) / n)

    means.sort()
    alpha = 1 - confidence
    lo_idx = int(alpha / 2 * n_boot)
    hi_idx = min(n_boot - 1, int((1 - alpha / 2) * n_boot))

    phat = sum(outcomes) / n
    return phat, means[lo_idx], means[hi_idx]


def parse_bool(value):
    """Parse field CSV yang bisa 'True'/'False'/'' (None)."""
    if value == "True":
        return True
    if value == "False":
        return False
    return None


def load_win_rates(path):
    """Group win/loss per (board_name, run_label) -> list outcome 0/1."""
    groups = defaultdict(list)
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row["board_name"], row["run_label"])
                groups[key].append(1 if row["result"] == "WIN" else 0)
    except FileNotFoundError:
        print(f"[WARNING] {path} tidak ditemukan, skip win-rate analysis.")
    return groups


def load_topk_hits(path):
    """Group top1/top3/top5 hit per (board_name, run_label) -> list outcome 0/1 per k."""
    groups = defaultdict(lambda: {"top1": [], "top3": [], "top5": []})
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row["board_name"], row["run_label"])
                for k in ("top1", "top3", "top5"):
                    val = parse_bool(row.get(f"{k}_hit", ""))
                    if val is not None:
                        groups[key][k].append(1 if val else 0)
    except FileNotFoundError:
        print(f"[WARNING] {path} tidak ditemukan, skip top-k analysis.")
    return groups


def main():
    win_groups = load_win_rates(RESULTS_CSV)
    topk_groups = load_topk_hits(DECISIONS_CSV)

    if not win_groups:
        print("Tidak ada data untuk dianalisis. Jalankan main.py dulu buat generate CSV.")
        sys.exit(1)

    summary_rows = []

    print("=" * 100)
    print("WIN RATE — Wilson 95% CI vs Bootstrap 95% CI")
    print("=" * 100)

    for (board_name, run_label), outcomes in sorted(win_groups.items()):
        n = len(outcomes)
        wins = sum(outcomes)

        w_phat, w_lo, w_hi = wilson_ci(wins, n)
        b_phat, b_lo, b_hi = bootstrap_ci(outcomes)

        print(
            f"[{board_name:12s}] {run_label:35s} "
            f"n={n:4d} win={wins:4d} "
            f"Wilson: {w_phat*100:5.1f}% [{w_lo*100:5.1f}, {w_hi*100:5.1f}] "
            f"Bootstrap: [{b_lo*100:5.1f}, {b_hi*100:5.1f}]"
        )

        row = {
            "board_name": board_name, "run_label": run_label, "metric": "win_rate",
            "n": n, "successes": wins,
            "point_estimate": w_phat, "wilson_lo": w_lo, "wilson_hi": w_hi,
            "bootstrap_lo": b_lo, "bootstrap_hi": b_hi
        }
        summary_rows.append(row)

    if topk_groups:
        print()
        print("=" * 100)
        print("TOP-K ACCURACY — Wilson 95% CI vs Bootstrap 95% CI")
        print("=" * 100)

        for (board_name, run_label), ks in sorted(topk_groups.items()):
            for k_name, outcomes in ks.items():
                n = len(outcomes)
                if n == 0:
                    continue
                hits = sum(outcomes)

                w_phat, w_lo, w_hi = wilson_ci(hits, n)
                b_phat, b_lo, b_hi = bootstrap_ci(outcomes)

                print(
                    f"[{board_name:12s}] {run_label:35s} {k_name:5s} "
                    f"n={n:4d} hit={hits:4d} "
                    f"Wilson: {w_phat*100:5.1f}% [{w_lo*100:5.1f}, {w_hi*100:5.1f}] "
                    f"Bootstrap: [{b_lo*100:5.1f}, {b_hi*100:5.1f}]"
                )

                row = {
                    "board_name": board_name, "run_label": run_label, "metric": k_name,
                    "n": n, "successes": hits,
                    "point_estimate": w_phat, "wilson_lo": w_lo, "wilson_hi": w_hi,
                    "bootstrap_lo": b_lo, "bootstrap_hi": b_hi
                }
                summary_rows.append(row)

    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "board_name", "run_label", "metric", "n", "successes",
            "point_estimate", "wilson_lo", "wilson_hi", "bootstrap_lo", "bootstrap_hi"
        ])
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nSummary tersimpan di {SUMMARY_CSV}")


if __name__ == "__main__":
    main()