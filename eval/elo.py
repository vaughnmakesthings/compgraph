"""Elo rating calculator for LLM comparison results."""

from __future__ import annotations

DEFAULT_K = 32
DEFAULT_RATING = 1500


def calculate_elo_ratings(
    comparisons: list[dict],
    run_map: dict[int, str],
    k: int = DEFAULT_K,
) -> dict[str, float]:
    """Calculate Elo ratings from comparison results.

    Args:
        comparisons: List of comparison dicts with result_a_id, result_b_id, winner
        run_map: Maps result_id -> "model/prompt_version" label
        k: Elo K-factor (higher = more volatile)

    Returns:
        Dict mapping "model/prompt_version" -> Elo rating
    """
    ratings: dict[str, float] = {}

    for label in run_map.values():
        ratings.setdefault(label, DEFAULT_RATING)

    for comp in comparisons:
        a_id = comp["result_a_id"]
        b_id = comp["result_b_id"]
        winner = comp["winner"]

        if winner == "both_bad":
            continue

        label_a = run_map.get(a_id)
        label_b = run_map.get(b_id)
        if not label_a or not label_b or label_a == label_b:
            continue

        ra = ratings[label_a]
        rb = ratings[label_b]

        ea = 1.0 / (1.0 + 10 ** ((rb - ra) / 400))
        eb = 1.0 - ea

        if winner == "a":
            sa, sb = 1.0, 0.0
        elif winner == "b":
            sa, sb = 0.0, 1.0
        else:  # tie
            sa, sb = 0.5, 0.5

        ratings[label_a] = ra + k * (sa - ea)
        ratings[label_b] = rb + k * (sb - eb)

    return ratings
