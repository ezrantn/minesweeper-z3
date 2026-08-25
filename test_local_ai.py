import json
from local_ai import call_local_ai

class FakeMessage:
    def __init__(self, content):
        self.content = content

class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)

class FakeResponse:
    def __init__(self, content):
        self.choices = [
            FakeChoice(content)
        ]

class FakeCompletion:

    def create(
        self,
        model,
        messages,
        response_format
    ):

        return FakeResponse(
            json.dumps(
                {
                    "reasoning": "mock reasoning",

                    "probabilities": [
                        {
                            "coord": [0, 1],
                            "risk": 0.30
                        },
                        {
                            "coord": [1, 0],
                            "risk": 0.10
                        },
                        {
                            "coord": [1, 1],
                            "risk": 0.70
                        }
                    ]
                }
            )
        )

class InvalidClient:

    def __init__(self):

        self.chat = type(
            "",
            (),
            {
                "completions": InvalidCompletion()
            }
        )()


class InvalidCompletion:

    def create(
        self,
        model,
        messages,
        response_format
    ):

        return FakeResponse(
            json.dumps(
                {
                    "reasoning": "",

                    "probabilities": [
                        {
                            "coord": [100, 100],
                            "risk": 0.01
                        }
                    ]
                }
            )
        )

class FakeClient:

    def __init__(self):

        self.chat = type(
            "",
            (),
            {
                "completions": FakeCompletion()
            }
        )()


def test_lowest_risk_selected():

    board = [
        [1, "U"],
        ["U", "U"]
    ]

    result, frontier = call_local_ai(
        board,
        2,
        2,
        1,
        client=FakeClient()
    )

    assert result["coordinate"] == [1, 0]

    assert result["ranking"][0]["risk"] == 0.10

    assert result["ranking"][1]["risk"] == 0.30

    assert result["ranking"][2]["risk"] == 0.70

def test_invalid_coordinate_returns_no_valid_prediction():

    board = [
        [1, "U"],
        ["U", "U"]
    ]

    result, _ = call_local_ai(
        board,
        2,
        2,
        1,
        client=InvalidClient()
    )

    assert result == "NO_VALID_PREDICTION"
