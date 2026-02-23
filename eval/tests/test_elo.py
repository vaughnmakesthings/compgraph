"""Tests for Elo rating calculator."""

from eval.elo import calculate_elo_ratings


def test_single_comparison_winner_gains():
    """Winner should gain points, loser should lose."""
    comparisons = [
        {"result_a_id": 1, "result_b_id": 2, "winner": "a"},
    ]
    run_map = {1: "haiku/v1", 2: "gpt4o-mini/v1"}
    ratings = calculate_elo_ratings(comparisons, run_map)
    assert ratings["haiku/v1"] > 1500
    assert ratings["gpt4o-mini/v1"] < 1500


def test_tie_no_change():
    """A tie should result in minimal rating change."""
    comparisons = [
        {"result_a_id": 1, "result_b_id": 2, "winner": "tie"},
    ]
    run_map = {1: "haiku/v1", 2: "gpt4o-mini/v1"}
    ratings = calculate_elo_ratings(comparisons, run_map)
    assert abs(ratings["haiku/v1"] - 1500) < 1
    assert abs(ratings["gpt4o-mini/v1"] - 1500) < 1


def test_both_bad_no_change():
    """both_bad should not affect ratings."""
    comparisons = [
        {"result_a_id": 1, "result_b_id": 2, "winner": "both_bad"},
    ]
    run_map = {1: "haiku/v1", 2: "gpt4o-mini/v1"}
    ratings = calculate_elo_ratings(comparisons, run_map)
    assert ratings["haiku/v1"] == 1500
    assert ratings["gpt4o-mini/v1"] == 1500


def test_multiple_comparisons():
    """Multiple wins should compound rating advantage."""
    comparisons = [
        {"result_a_id": 1, "result_b_id": 2, "winner": "a"},
        {"result_a_id": 1, "result_b_id": 2, "winner": "a"},
        {"result_a_id": 1, "result_b_id": 2, "winner": "a"},
    ]
    run_map = {1: "haiku/v1", 2: "gpt4o-mini/v1"}
    ratings = calculate_elo_ratings(comparisons, run_map)
    assert ratings["haiku/v1"] > ratings["gpt4o-mini/v1"]
    assert ratings["haiku/v1"] > 1530
