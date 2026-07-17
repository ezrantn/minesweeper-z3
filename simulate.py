import time
import random
from board import MinesweeperBoard
from local_ai import call_local_ai
from verifier import execute_z3_inference


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

def simulate_game(mode, width, height, total_mines):
    game = MinesweeperBoard(width, height, total_mines)
    game.reveal_cell(0, 0) # Pembukaan aman awal

    stats = {
        "duration": 0,
        "z3_calls": 0,
        "llm_calls": 0,
        "failure_reason": "None",
        "result": "LOSS",

        "frontier_calls": 0,
        "frontier_size_sum": 0
    }

    start_time = time.time()

    while not game.game_over and not game.won:
        # --- MODE A: OLLAMA MURNI ---
        if mode == "OLLAMA_ONLY":
            flat = [c for r in game.visible_board for c in r]
            mines_left = game.total_mines - flat.count('F')
            stats["llm_calls"] += 1
            analysis, num_options = call_local_ai(game.visible_board, width, height, mines_left)
            stats["llm_calls"] += 1
            stats["frontier_calls"] += 1
            stats["frontier_size_sum"] += num_options

            if analysis in ["HALLUCINATION", "ERROR"] or not analysis or not isinstance(analysis, dict):
                stats["failure_reason"] = "LLM_Hallucination"
                break

            coord = analysis["coordinate"]
            if not (0 <= coord[0] < height and 0 <= coord[1] < width):
                stats["failure_reason"] = "LLM_Hallucination"
                break

            if not game.reveal_cell(coord[0], coord[1]):
                stats["failure_reason"] = "LLM_Wrong_Probability"
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
                frontier = [
                    (r, c)
                    for r, c in unexplored
                    if any(
                        isinstance(game.visible_board[nr][nc], int)
                        for nr, nc in game.get_neighbors(r, c)
                    )
                ]

                coord = random.choice(frontier if frontier else unexplored)
                if not unexplored: break
                r, c = coord
                if not game.reveal_cell(r, c):
                    stats["failure_reason"] = "Z3_Macet"
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

                stats["llm_calls"] += 1
                analysis, num_options = call_local_ai(game.visible_board, width, height, mines_left)

                stats["llm_calls"] += 1
                stats["frontier_calls"] += 1
                stats["frontier_size_sum"] += num_options

                # Tangkap pertahanan Gatekeeper dari ai.py
                if analysis == "HALLUCINATION" or analysis == "ERROR":
                    stats["failure_reason"] = "LLM_Hallucination" if analysis == "HALLUCINATION" else "LLM_Wrong_Probability"

                    # Picu Stochastic Fallback Defense langsung di sini
                    unexplored = [(r, c) for r in range(height) for c in range(width) if game.visible_board[r][c] == 'U']
                    if not unexplored: break
                    # Utamakan frontier dulu jika ada kotak U yang menempel angka
                    frontier = [(r, c) for r, c in unexplored if any(isinstance(game.visible_board[nr][nc], int) for nr, nc in game.get_neighbors(r, c))]
                    coord = random.choice(frontier) if frontier else random.choice(unexplored)

                # Jalankan tindakan eksekusi
                target_r, target_c = analysis["coordinate"][0], analysis["coordinate"][1]
                success = game.reveal_cell(target_r, target_c)

                if not success:
                    # Di sini kita bisa langsung pakai nilai num_options dari ai.py secara presisi!
                    if num_options <= 2:
                        stats["failure_reason"] = "Pure_50_50"
                    else:
                        stats["failure_reason"] = "LLM_Wrong_Probability"

                    break

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
