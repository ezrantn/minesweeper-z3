import time
import random
from board import MinesweeperBoard
from local_ai import call_local_ai
from verifier import execute_z3_inference

LLM_RESPONSE_FAILURE = {
    "INVALID_JSON": "Invalid_JSON",
    "API_ERROR": "API_Error",
    "NO_VALID_PREDICTION": "Hallucination_Coord",
}


def get_frontier_cells(game):
    """
    Mengembalikan semua unexplored cell yang bertetangga
    dengan minimal satu angka.
    """
    frontier = []

    for r in range(game.height):
        for c in range(game.width):
            if game.visible_board[r][c] != 'U':
                continue

            if any(
                isinstance(game.visible_board[nr][nc], int)
                for nr, nc in game.get_neighbors(r, c)
            ):
                frontier.append((r, c))

    return frontier

def topk_hit(game, ranking, k):
    """
    True jika ada minimal satu sel AMAN (bukan ranjau) di antara
    k koordinat teratas ranking LLM (diurutkan risk terendah -> tertinggi).
    """
    for item in ranking[:k]:
        r, c = item["coord"]
        if game.true_board[r][c] == 0:
            return True
    return False

def simulate_game(mode, width, height, total_mines, game_id=0, board_name=""):
    random.seed(game_id)
    game = MinesweeperBoard(width, height, total_mines)
    game.reveal_cell(0, 0) # Pembukaan aman awal

    stats = {
        "duration": 0,
        "z3_calls": 0,
        "llm_calls": 0,
        "failure_reason": "None",
        "result": "LOSS",
        "frontier_calls": 0,
        "frontier_size_sum": 0,
        "llm_decisions": []
    }

    step = 0
    start_time = time.time()

    while not game.game_over and not game.won:
        step += 1
        # --- MODE A: OLLAMA MURNI ---
        if mode == "OLLAMA_ONLY":
            flat = [c for r in game.visible_board for c in r]
            mines_left = game.total_mines - flat.count('F')
            analysis, num_options = call_local_ai(game.visible_board, width, height, mines_left)
            stats["llm_calls"] += 1
            stats["frontier_calls"] += 1
            stats["frontier_size_sum"] += num_options

            if not isinstance(analysis, dict) or not analysis:
                stats["failure_reason"] = LLM_RESPONSE_FAILURE.get(analysis, "Invalid_JSON")
                stats["llm_decisions"].append({
                    "game_id": game_id, "board_name": board_name, "mode": mode, "step": step,
                    "frontier_size": num_options, "llm_choice": None, "safe": False,
                    "deadlock_type": "N/A", "reasoning": f"invalid_response:{analysis}",
                    "top1_hit": None, "top3_hit": None, "top5_hit": None
                })

                break

            coord = analysis["coordinate"]
            if not (0 <= coord[0] < height and 0 <= coord[1] < width):
                stats["failure_reason"] = "Out_of_Bounds"
                stats["llm_decisions"].append({
                    "game_id": game_id, "board_name": board_name, "mode": mode, "step": step,
                    "frontier_size": num_options, "llm_choice": coord, "safe": False,
                    "deadlock_type": "Out_of_Bounds", "reasoning": analysis.get("reasoning", ""),
                    "top1_hit": None, "top3_hit": None, "top5_hit": None
                })

                break

            if game.visible_board[coord[0]][coord[1]] != 'U':
                stats["failure_reason"] = "Already_Open"
                stats["llm_decisions"].append({
                    "game_id": game_id, "board_name": board_name, "mode": mode, "step": step,
                    "frontier_size": num_options, "llm_choice": coord, "safe": False,
                    "deadlock_type": "Already_Open", "reasoning": analysis.get("reasoning", ""),
                    "top1_hit": None, "top3_hit": None, "top5_hit": None
                })

                break

            ranking = analysis.get("ranking", [])
            success = game.reveal_cell(coord[0], coord[1])
            stats["llm_decisions"].append({
                "game_id": game_id, "board_name": board_name, "mode": mode, "step": step,
                "frontier_size": num_options, "llm_choice": coord, "safe": success,
                "deadlock_type": "Pure_50_50" if num_options <= 2 else "Complex_Guess",
                "reasoning": analysis.get("reasoning", ""),
                "top1_hit": topk_hit(game, ranking, 1),
                "top3_hit": topk_hit(game, ranking, 3),
                "top5_hit": topk_hit(game, ranking, 5)
            })

            if not success:
                stats["failure_reason"] = "Wrong_Guess"
                break

        # Kalau cuma memilih acak dari frontier, performanya berapa?
        elif mode == "RANDOM_FRONTIER":
            frontier = get_frontier_cells(game)

            if frontier:
                coord = random.choice(frontier)
            else:
                unexplored = [
                    (r, c)
                    for r in range(height)
                    for c in range(width)
                    if game.visible_board[r][c] == 'U'
                ]

                if not unexplored:
                    break

                coord = random.choice(unexplored)

            if not game.reveal_cell(coord[0], coord[1]):
                stats["failure_reason"] = "Random_Frontier"
                break

        # --- MODE B: Z3 MURNI (Tebak acak pas mentok) ---
        elif mode == "Z3_ONLY":
            stats["z3_calls"] += 1
            safe, flags = execute_z3_inference(game.visible_board, width, height, game.total_mines)

            if safe:
                for r, c in safe: game.reveal_cell(r, c)
            elif flags:
                for r, c in flags: game.flag_cell(r, c)
            else:
                # Z3 Mentok -> Tebak Acak Instan (Baseline)
                unexplored = [
                    (r, c)
                    for r in range(height)
                    for c in range(width)
                    if game.visible_board[r][c] == 'U'
                ]

                if not unexplored:
                    break

                frontier = get_frontier_cells(game)

                coord = random.choice(frontier if frontier else unexplored)
                r, c = coord
                if not game.reveal_cell(r, c):
                    stats["failure_reason"] = "Z3_Stuck"
                    break

        elif mode == "Z3_FRONTIER_RANDOM":
            stats["z3_calls"] += 1

            safe, flags = execute_z3_inference(
                game.visible_board,
                width,
                height,
                game.total_mines
            )

            if safe:
                for r, c in safe:
                    game.reveal_cell(r, c)
            elif flags:
                for r, c in flags:
                    game.flag_cell(r, c)
            else:
                frontier = get_frontier_cells(game)

                if frontier:
                    coord = random.choice(frontier)
                else:
                    unexplored = [
                        (r, c)
                        for r in range(height)
                        for c in range(width)
                        if game.visible_board[r][c] == 'U'
                    ]

                    if not unexplored:
                        break

                    coord = random.choice(unexplored)

                if not game.reveal_cell(coord[0], coord[1]):
                    stats["failure_reason"] = "Z3_Frontier_Random"
                    break

        # --- MODE C: GABUNGAN NEURO-SYMBOLIC (Z3 + OLLAMA) ---
        elif mode == "NEURO_SYMBOLIC":
            stats["z3_calls"] += 1
            safe, flags = execute_z3_inference(game.visible_board, width, height, game.total_mines)

            if safe:
                for r, c in safe: game.reveal_cell(r, c)
            elif flags:
                for r, c in flags: game.flag_cell(r, c)
            else:
                flat = [cell for row in game.visible_board for cell in row]
                mines_left = game.total_mines - flat.count('F')
                analysis, num_options = call_local_ai(game.visible_board, width, height, mines_left)

                stats["llm_calls"] += 1
                stats["frontier_calls"] += 1
                stats["frontier_size_sum"] += num_options

                reasoning = ""
                used_fallback = False
                fallback_cause = None

                # Tangkap pertahanan Gatekeeper dari ai.py
                if not isinstance(analysis, dict) or not analysis:
                    used_fallback = True
                    fallback_cause = LLM_RESPONSE_FAILURE.get(analysis, "Invalid_JSON")
                    reasoning = f"invalid_response:{analysis}"

                    # Picu Stochastic Fallback Defense langsung di sini
                    unexplored = [(r, c) for r in range(height) for c in range(width) if game.visible_board[r][c] == 'U']
                    if not unexplored: break

                    # Utamakan frontier dulu jika ada kotak U yang menempel angka
                    frontier = get_frontier_cells(game)
                    target_r, target_c = random.choice(frontier) if frontier else random.choice(unexplored)

                else:
                    target_r, target_c = analysis["coordinate"][0], analysis["coordinate"][1]
                    reasoning = analysis.get("reasoning", "")

                    out_of_bounds = not (0 <= target_r < height and 0 <= target_c < width)
                    already_open = not out_of_bounds and game.visible_board[target_r][target_c] != 'U'

                    if out_of_bounds or already_open:
                        used_fallback = True
                        fallback_cause = "Out_of_Bounds" if out_of_bounds else "Already_Open"
                        reasoning = f"{fallback_cause.lower()}:{[target_r, target_c]}"
                        unexplored = [(r, c) for r in range(height) for c in range(width) if game.visible_board[r][c] == 'U']
                        if not unexplored: break
                        frontier = get_frontier_cells(game)
                        target_r, target_c = random.choice(frontier) if frontier else random.choice(unexplored)

                ranking = [] if used_fallback else analysis.get("ranking", [])

                # Jalankan tindakan eksekusi
                success = game.reveal_cell(target_r, target_c)

                stats["llm_decisions"].append({
                    "game_id": game_id, "board_name": board_name, "mode": mode, "step": step,
                    "frontier_size": num_options, "llm_choice": [target_r, target_c], "safe": success,
                    "deadlock_type": "Fallback" if used_fallback else ("Pure_50_50" if num_options <= 2 else "Complex_Guess"),
                    "reasoning": reasoning,
                    "top1_hit": None if used_fallback else topk_hit(game, ranking, 1),
                    "top3_hit": None if used_fallback else topk_hit(game, ranking, 3),
                    "top5_hit": None if used_fallback else topk_hit(game, ranking, 5)
                })

                if not success:
                    if used_fallback:
                        stats["failure_reason"] = fallback_cause
                    elif num_options <= 2:
                        stats["failure_reason"] = "Pure_50_50"
                    else:
                        stats["failure_reason"] = "Wrong_Guess"
                    

    if game.won:
        stats["result"] = "WIN"
        stats["failure_reason"] = "None"

    stats["duration"] = time.time() - start_time

    if stats["frontier_calls"] > 0:
      stats["avg_frontier_size"] = (
          stats["frontier_size_sum"] /
          stats["frontier_calls"]
      )
    else:
        stats["avg_frontier_size"] = 0

    return stats
