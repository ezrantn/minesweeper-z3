import csv
import os
from simulate import simulate_game

csv_file = "experiment_results.csv"

def main():
    boards = {
        "Beginner": {"w": 9, "h": 9, "m": 10},
        "Intermediate": {"w": 16, "h": 16, "m": 40},
        "Expert": {"w": 30, "h": 16, "m": 99}
    }

    modes = ["OLLAMA_ONLY", "Z3_ONLY", "NEURO_SYMBOLIC", "RANDOM_FRONTIER", "Z3_FRONTIER_RANDOM"]
    iterations = 100 # Set ke 50 atau 100 saat pengumpulan data final paper lo

    print("==========================================================")
    print("      NEURO-SYMBOLIC MINESWEEPER BATCH SIMULATOR          ")
    print("==========================================================\n")

    for board_name, spec in boards.items():
        print(f"--- MENGUJI UKURAN PAPAN: {board_name} ({spec['w']}x{spec['h']} | {spec['m']} Mines) ---")

        for mode in modes:
            wins = 0
            total_time = 0
            total_llm_calls = 0
            total_z3_calls = 0
            fail_reasons = {
                "Z3_Macet": 0,
                "Z3_Frontier_Random": 0,
                "Random_Frontier": 0,
                "LLM_Hallucination": 0,
                "LLM_Wrong_Probability": 0,
                "Pure_50_50": 0,
                "None": 0
            }

            for _ in range(iterations):
                res = simulate_game(mode, spec['w'], spec['h'], spec['m'])
                if res["result"] == "WIN": wins += 1
                total_time += res["duration"]
                total_llm_calls += res["llm_calls"]
                total_z3_calls += res["z3_calls"]
                fail_reasons[res["failure_reason"]] += 1

            win_rate = (wins / iterations) * 100
            avg_time = total_time / iterations
            avg_llm = total_llm_calls / iterations

            print(f"[{mode}] Win Rate: {win_rate:.1f}% | Avg Time: {avg_time:.2f}s | Avg LLM Calls: {avg_llm:.1f}")
            if mode == "NEURO_SYMBOLIC" or mode == "OLLAMA_ONLY":
                print(f"   -> [Failure Distribution] Hallucinations: {fail_reasons['LLM_Hallucination']} | Wrong Guess: {fail_reasons['LLM_Wrong_Probability']}")
        print("-" * 60)


        with open(csv_file, "a", newline="", encoding="utf-8") as f:
          writer = csv.writer(f)

          for i in range(iterations):

              res = simulate_game(...)

              writer.writerow([
                  board_name,
                  mode,
                  i + 1,
                  res["result"],
                  res["failure_reason"],
                  res["duration"],
                  res["z3_calls"],
                  res["llm_calls"],
                  res["frontier_calls"],
                  res["avg_frontier_size"]
              ])


if __name__ == "__main__":
    main()
