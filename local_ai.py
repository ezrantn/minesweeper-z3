import json
from openai import OpenAI

def call_local_ai(visible_board, width, height, mines_left, client=None):
    if client is None:  
        client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )

    matrix_rows = [
        " ".join(str(cell) for cell in row)
        for row in visible_board
    ]
    matrix_string = "\n".join(matrix_rows)

    frontier_options = []
    all_unexplored = []

    for r in range(height):
        for c in range(width):

            if visible_board[r][c] != "U":
                continue

            all_unexplored.append([r, c])

            has_numbered_neighbor = False

            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:

                    nr = r + dr
                    nc = c + dc

                    if 0 <= nr < height and 0 <= nc < width:

                        if isinstance(visible_board[nr][nc], int):
                            has_numbered_neighbor = True
                            break

                if has_numbered_neighbor:
                    break

            if has_numbered_neighbor:
                frontier_options.append([r, c])

    choices_to_send = (
        frontier_options
        if frontier_options
        else all_unexplored
    )

    options_string = ", ".join(
        f"[{r},{c}]"
        for r, c in choices_to_send
    )

    user_prompt = f"""
You are an AI agent resolving a logical deadlock in Minesweeper.

Remaining mines:
{mines_left}

BOARD:

{matrix_string}

LEGAL FRONTIER:

{options_string}

Instructions:

1. Analyze EVERY frontier coordinate.
2. Estimate the relative probability that each coordinate contains a mine.
3. Lower risk = safer move.
4. Do NOT omit any coordinate.
5. Risk must be between 0.0 and 1.0.
6. Return ONLY valid JSON.

Example:

{{
    "reasoning":"brief explanation",

    "probabilities":[
        {{
            "coord":[2,3],
            "risk":0.12
        }},
        {{
            "coord":[4,5],
            "risk":0.31
        }}
    ]
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama3",
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            response_format={
                "type": "json_object"
            }
        )

    except Exception as e:
        print(f"[LOCAL AI ERROR] API call failed: {e}")
        return "API_ERROR", len(choices_to_send)
    try:
        data = json.loads(
            response.choices[0].message.content.strip()
        )
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        print(f"[LOCAL AI ERROR] Invalid JSON: {e}")
        return "INVALID_JSON", len(choices_to_send)
    try:
        reasoning = data.get("reasoning", "")

        raw_predictions = data.get(
            "probabilities",
            []
        )

        valid_predictions = []

        for item in raw_predictions:

            if not isinstance(item, dict):
                continue

            coord = item.get("coord")
            risk = item.get("risk")

            if (
                isinstance(coord, list)
                and len(coord) == 2
                and isinstance(risk, (int, float))
            ):

                r, c = coord

                if (
                    0 <= r < height
                    and 0 <= c < width
                    and visible_board[r][c] == "U"
                ):

                    valid_predictions.append(
                        {
                            "coord": coord,
                            "risk": float(risk)
                        }
                    )

        if len(valid_predictions) == 0:

            print("[LOCAL AI WARNING] No valid prediction.")

            return "NO_VALID_PREDICTION", len(choices_to_send)

        valid_predictions.sort(
            key=lambda x: x["risk"]
        )

        print("\n===== LOCAL AI RISK ESTIMATION =====")

        for item in valid_predictions:

            print(
                f"{item['coord']} -> "
                f"{item['risk']:.3f}"
            )

        print(f"\nReasoning: {reasoning}\n")

        return {
            "coordinate": valid_predictions[0]["coord"],
            "ranking": valid_predictions,
            "reasoning": reasoning
        }, len(choices_to_send)

    except Exception as e:
        print(f"[LOCAL AI ERROR] Unexpected error while processing response: {e}")
        return "INVALID_JSON", len(choices_to_send)