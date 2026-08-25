from simulate import topk_hit

class FakeGame:
    """Board minimal yang cuma punya true_board, cukup buat topk_hit."""
    def __init__(self, true_board):
        self.true_board = true_board


def test_top1_hit_true_when_best_ranked_is_safe():
    # (0,0) aman (0), ranking taruh (0,0) di urutan pertama
    game = FakeGame([[0, 1], [0, 0]])
    ranking = [
        {"coord": [0, 0], "risk": 0.05},
        {"coord": [0, 1], "risk": 0.90},
    ]
    assert topk_hit(game, ranking, 1) is True


def test_top1_hit_false_when_best_ranked_is_mine():
    # (0,1) ranjau (1), tapi ranking taruh itu di urutan pertama
    game = FakeGame([[0, 1], [0, 0]])
    ranking = [
        {"coord": [0, 1], "risk": 0.10},
        {"coord": [1, 0], "risk": 0.50},
    ]
    assert topk_hit(game, ranking, 1) is False


def test_top3_hit_true_if_safe_cell_within_top3():
    # (0,0) aman, (0,1) ranjau, (1,0) ranjau, (1,1) aman
    game = FakeGame([[0, 1], [1, 0]])
    ranking = [
        {"coord": [0, 1], "risk": 0.10},  # mine, top-1 salah
        {"coord": [1, 0], "risk": 0.20},  # mine, top-2 salah
        {"coord": [1, 1], "risk": 0.30},  # aman, top-3 benar
    ]
    assert topk_hit(game, ranking, 1) is False
    assert topk_hit(game, ranking, 2) is False
    assert topk_hit(game, ranking, 3) is True


def test_top5_hit_false_when_all_top5_are_mines():
    # Papan 2x3 dengan cuma 1 sel aman, dan itu di luar top-5
    game = FakeGame([
        [0, 1, 1],
        [1, 1, 1],
    ])
    ranking = [
        {"coord": [0, 1], "risk": 0.1},
        {"coord": [0, 2], "risk": 0.2},
        {"coord": [1, 0], "risk": 0.3},
        {"coord": [1, 1], "risk": 0.4},
        {"coord": [1, 2], "risk": 0.5},
        {"coord": [0, 0], "risk": 0.99},  # sel aman satu-satunya, di luar top-5
    ]
    assert topk_hit(game, ranking, 5) is False
    assert topk_hit(game, ranking, 6) is True


def test_topk_hit_empty_ranking_returns_false():
    game = FakeGame([[0, 0], [0, 0]])
    assert topk_hit(game, [], 3) is False


if __name__ == "__main__":
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"PASS {t.__name__}")
    print(f"\n{passed}/{len(tests)} tests passed")