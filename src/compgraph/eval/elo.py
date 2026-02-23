from __future__ import annotations

import uuid

DEFAULT_K = 32
DEFAULT_RATING = 1500.0


def calculate_elo_ratings(
    comparisons: list[dict],
    run_map: dict[uuid.UUID, str],
    k: int = DEFAULT_K,
) -> dict[str, float]:
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
        else:
            sa, sb = 0.5, 0.5

        ratings[label_a] = ra + k * (sa - ea)
        ratings[label_b] = rb + k * (sb - eb)

    return ratings
