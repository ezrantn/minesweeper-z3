import os
import json
from anthropic import Anthropic

def call_claude_heuristic_strategist(visible_board, width, height, mines_left):
    """
    Memanggil Claude API ketika Z3 mengalami deadlock.
    Menganalisis papan secara heuristik dan mengembalikan koordinat tebakan terbaik [row, col].
    """
    # Pastikan lo udah set ANTHROPIC_API_KEY di environment variable lo
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    # 1. Ubah matriks papan menjadi string teks yang scannable buat LLM
    matrix_rows = []
    for row in visible_board:
        matrix_rows.append(" ".join(str(cell) for cell in row))
    matrix_string = "\n".join(matrix_rows)
    
    # 2. Rancang Prompt Neuro-Symbolic
    system_prompt = (
        "You are an advanced Neuro-Symbolic AI Agent specializing in exact SMT grid puzzles "
        "and probabilistic heuristic optimization. Your role is to resolve logical deadlocks "
        "in Minesweeper where strict deduction is impossible."
    )
    
    user_prompt = f"""
[CRITICAL STATE REPORT: LOGICAL DEADLOCK]
Matrix Size: {width}x{height}
Remaining Global Mines: {mines_left}

BOARD MATRIX REPRESENTATION:
Legend: 'U' = Unexplored/Hidden, 'F' = Flagged, '0-8' = Revealed safe cell numbers.
{matrix_string}

INSTRUCTIONS:
1. Analyze the global remaining mine density against open borders.
2. Formulate heuristic probabilities for cells directly adjacent to the revealed frontier (like the cells surrounding the '1' at the top-left).
3. Return exactly one optimal coordinate to click that minimizes mine probability.
4. Output your decision strictly in valid JSON format without markdown blocks: {{"reasoning": "your evaluation", "coordinate": [row, col]}}
"""

    # 3. Hit Anthropic API (Paket Claude 3.5 Sonnet biar otaknya encer)
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=400,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    
    # 4. Parsing Output JSON
    try:
        raw_text = response.content[0].text.strip()
        # Bersihkan jika Claude secara tidak sengaja membungkusnya di dalam ```json
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1].replace("json", "").strip()
            
        data = json.loads(raw_text)
        print(f"[CLAUDE HEURISTIC] Reasoning: {data['reasoning']}")
        return data['coordinate'] # Mengembalikan [row, col]
    except Exception as e:
        print(f"[ERROR] Gagal parsing keputusan Claude: {e}")
        # Fallback tebakan acak aman jika API/parsing error
        return [0, 1]