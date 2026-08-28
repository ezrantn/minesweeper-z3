import csv
from simulate import simulate_game

RESULTS_CSV = "experiment_results.csv"
DECISIONS_CSV = "llm_decisions.csv"

RESULTS_HEADER = [
    "board_name", "mode", "iteration", "game_id", "result", "failure_reason",
    "duration", "z3_calls", "llm_calls", "frontier_calls", "avg_frontier_size"
]

DECISIONS_HEADER = [
    "game_id", "board_name", "mode", "step", "frontier_size",
    "llm_choice", "safe", "deadlock_type", "reasoning",
    "top1_hit", "top3_hit", "top5_hit"
]

# Ablation DSG on/off: OLLAMA_ONLY = tanpa Z3 gatekeeper, NEURO_SYMBOLIC = dengan Z3 gatekeeper.
LLM_MODES = ["OLLAMA_ONLY", "NEURO_SYMBOLIC"]
NON_LLM_MODES = ["Z3_ONLY", "RANDOM_FRONTIER", "Z3_FRONTIER_RANDOM"]

# Tambahkan model lain di sini kalau Ollama sudah punya modelnya terpasang lokal.
# Contoh saat siap eksperimen skala penuh: ["llama3", "qwen2.5", "gemma3", "mistral"]
MODELS = ["llama3"]

# False = kirim cuma frontier cells ke LLM, True = kirim seluruh unexplored board.
FULL_BOARD_OPTIONS = [False, True]

def build_runs():
    """
    Bangun daftar konfigurasi run: setiap dict merepresentasikan satu kombinasi
    (mode, model, prompt_scope) yang akan dijalankan `iterations` kali per board.
    Mode non-LLM cuma dijalankan sekali karena model/full_board tidak relevan.
    """
    runs = []

    for mode in NON_LLM_MODES:
        runs.append({
            "base_mode": mode,
            "model": None,
            "full_board": False,
            "label": mode
        })

    for mode in LLM_MODES:
        for model in MODELS:
            for full_board in FULL_BOARD_OPTIONS:
                scope = "FULLBOARD" if full_board else "FRONTIER"
                runs.append({
                    "base_mode": mode,
                    "model": model,
                    "full_board": full_board,
                    "label": f"{mode}__{model}__{scope}"
                })

    return runs


def main():
    boards = {
        "Beginner": {"w": 9, "h": 9, "m": 10},
        "Intermediate": {"w": 16, "h": 16, "m": 40},
        "Expert": {"w": 30, "h": 16, "m": 99}
    }

    modes = ["OLLAMA_ONLY", "Z3_ONLY", "NEURO_SYMBOLIC", "RANDOM_FRONTIER", "Z3_FRONTIER_RANDOM"]
    iterations = 100 # Set ke 1000 atau 5000 saat pengumpulan data final paper lo
    runs = build_runs()

    print("==========================================================")
    print("      NEURO-SYMBOLIC MINESWEEPER BATCH SIMULATOR          ")
    print("==========================================================\n")
    print(f"Total konfigurasi run per board: {len(runs)}\n")

    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(RESULTS_HEADER)
    with open(DECISIONS_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(DECISIONS_HEADER)

    for board_name, spec in boards.items():
        print(f"--- MENGUJI UKURAN PAPAN: {board_name} ({spec['w']}x{spec['h']} | {spec['m']} Mines) ---")

        for run in runs:
            mode = run["base_mode"]
            model = run["model"]
            full_board = run["full_board"]
            label = run["label"]
            scope = "FULLBOARD" if full_board else "FRONTIER"

            wins = 0
            total_time = 0
            total_llm_calls = 0
            total_z3_calls = 0
            fail_reasons = {
                "Z3_Stuck": 0,
                "Z3_Frontier_Random": 0,
                "Random_Frontier": 0,
                "Invalid_JSON": 0,
                "API_Error": 0,
                "Hallucination_Coord": 0,
                "Out_of_Bounds": 0,
                "Already_Open": 0,
                "Wrong_Guess": 0,
                "Pure_50_50": 0,
                "None": 0
            }

            results_rows = []
            decision_rows = []
            decision_dicts = []

            for i in range(iterations):
                # game_id sama antar mode pada board yang sama => papan identik,
                # perbandingan antar mode jadi paired (bukan sampel acak independen).
                game_id = i
                res = simulate_game(
                    mode, spec['w'], spec['h'], spec['m'],
                    game_id=game_id, board_name=board_name,
                    model=model or "llama3", full_board=full_board
                )

                if res["result"] == "WIN":
                    wins += 1
                total_time += res["duration"]
                total_llm_calls += res["llm_calls"]
                total_z3_calls += res["z3_calls"]
                fail_reasons[res["failure_reason"]] += 1

                results_rows.append([
                    board_name, label, mode, model, scope, i + 1, game_id,
                    res["result"], res["failure_reason"], res["duration"],
                    res["z3_calls"], res["llm_calls"],
                    res["frontier_calls"], res["avg_frontier_size"]
                ])

                for d in res.get("llm_decisions", []):
                    decision_dicts.append(d)
                    decision_rows.append([
                        d["game_id"], d["board_name"], label, mode, model, scope, d["step"],
                        d["frontier_size"], d["llm_choice"], d["safe"], d["deadlock_type"], d["reasoning"],
                        d["top1_hit"], d["top3_hit"], d["top5_hit"]
                    ])

            win_rate = (wins / iterations) * 100
            avg_time = total_time / iterations
            avg_llm = total_llm_calls / iterations

            print(f"[{label}] Win Rate: {win_rate:.1f}% | Avg Time: {avg_time:.2f}s | Avg LLM Calls: {avg_llm:.1f}")
            if mode in LLM_MODES:
                print(
                    "   -> [Failure Distribution] "
                    f"Invalid_JSON: {fail_reasons['Invalid_JSON']} | "
                    f"API_Error: {fail_reasons['API_Error']} | "
                    f"Hallucination_Coord: {fail_reasons['Hallucination_Coord']} | "
                    f"Out_of_Bounds: {fail_reasons['Out_of_Bounds']} | "
                    f"Already_Open: {fail_reasons['Already_Open']} | "
                    f"Pure_50_50: {fail_reasons['Pure_50_50']} | "
                    f"Wrong_Guess: {fail_reasons['Wrong_Guess']}"
                )
                
                # Top-K accuracy: dari semua keputusan LLM yang punya ranking valid
                # (bukan fallback/hallucination), berapa persen yang top-k nya
                # mengandung minimal satu sel aman.
                scored = [d for d in decision_dicts if d["top1_hit"] is not None]
                if scored:
                    top1 = sum(d["top1_hit"] for d in scored) / len(scored) * 100
                    top3 = sum(d["top3_hit"] for d in scored) / len(scored) * 100
                    top5 = sum(d["top5_hit"] for d in scored) / len(scored) * 100
                    print(f"   -> [Top-K Accuracy] Top-1: {top1:.1f}% | Top-3: {top3:.1f}% | Top-5: {top5:.1f}% (n={len(scored)})")

            with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(results_rows)
            with open(DECISIONS_CSV, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(decision_rows)

        print("-" * 60)

if __name__ == "__main__":
    main()
