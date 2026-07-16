import json
from openai import OpenAI

def call_local_ai_strategist(visible_board, width, height, mines_left):
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    
    matrix_rows = [" ".join(str(cell) for cell in row) for row in visible_board]
    matrix_string = "\n".join(matrix_rows)
    
    user_prompt = f"""
You are an AI Agent resolving logical deadlocks in Minesweeper where strict deduction is impossible.
Matrix Size: {width}x{height}
Remaining Mines: {mines_left}

BOARD MATRIX:
'U' = Unexplored, 'F' = Flagged, '0-8' = Numbers.
{matrix_string}

INSTRUCTIONS:
1. Analyze the frontier cells next to numbers.
2. Select exactly ONE coordinate [row, col] that is safest to click.
3. Output strictly in this JSON format: {{"reasoning": "text", "coordinate": [row, col]}}
"""
    try:
        response = client.chat.completions.create(
            model="llama3",
            messages=[{"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content.strip())
        print(f"[LOCAL AI HEURISTIC] Reasoning: {data['reasoning']}")
        return data['coordinate']
    except Exception as e:
        print(f"[LOCAL AI ERROR] Fallback invoked due to: {e}")
        for r in range(height):
            for c in range(width):
                if visible_board[r][c] == 'U':
                    return [r, c]
        return [0, 0]