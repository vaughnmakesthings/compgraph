"""Page 3: Elo leaderboard and field-level accuracy."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import pandas as pd
import streamlit as st

from eval.elo import calculate_elo_ratings
from eval.store import EvalStore
from eval.validator import validate_run

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
DB_PATH = str(DATA_DIR / "eval.db")


def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


@st.cache_resource
def get_store() -> EvalStore:
    store = EvalStore(DB_PATH)
    _get_or_create_event_loop().run_until_complete(store.init())
    return store


store = get_store()
loop = _get_or_create_event_loop()
st.header("Leaderboard")

runs = loop.run_until_complete(store.get_all_runs())
comparisons = loop.run_until_complete(store.get_comparisons())

if not runs:
    st.info("No runs yet.")
    st.stop()

pass_number = st.selectbox("Pass", [1, 2])
pass_runs = [r for r in runs if r["pass_number"] == pass_number]

if not pass_runs:
    st.info(f"No Pass {pass_number} runs yet.")
    st.stop()

run_map: dict[int, str] = {}
run_labels: dict[int, str] = {}
for run in pass_runs:
    label = f"{run['model']}/{run['prompt_version']}"
    run_labels[run["id"]] = label
    results = loop.run_until_complete(store.get_results(run["id"]))
    for r in results:
        run_map[r["id"]] = label

if comparisons:
    ratings = calculate_elo_ratings(comparisons, run_map)
else:
    ratings = {label: 1500 for label in set(run_map.values())}

# Compute compliance and accuracy for each run
run_compliance: dict[int, float] = {}
run_accuracy: dict[int, str] = {}
for run in pass_runs:
    if pass_number == 1:
        validation = loop.run_until_complete(validate_run(store, run["id"]))
        run_compliance[run["id"]] = validation.compliance_rate

    reviewed = loop.run_until_complete(store.get_reviewed_count(run["id"]))
    if reviewed > 0:
        field_acc = loop.run_until_complete(store.get_field_accuracy(run["id"]))
        if field_acc:
            avg_acc = sum(field_acc.values()) / len(field_acc)
            results = loop.run_until_complete(store.get_results(run["id"]))
            run_accuracy[run["id"]] = f"{avg_acc * 100:.0f}% ({reviewed} reviewed)"
        else:
            run_accuracy[run["id"]] = "—"
    else:
        run_accuracy[run["id"]] = "—"

leaderboard = []
for run in pass_runs:
    label = run_labels[run["id"]]
    results = loop.run_until_complete(store.get_results(run["id"]))
    total = len(results)
    success = sum(1 for r in results if r["parse_success"])

    wins = sum(
        1
        for c in comparisons
        if (run_map.get(c["result_a_id"]) == label and c["winner"] == "a")
        or (run_map.get(c["result_b_id"]) == label and c["winner"] == "b")
    )
    total_comps = sum(
        1
        for c in comparisons
        if run_map.get(c["result_a_id"]) == label or run_map.get(c["result_b_id"]) == label
    )

    row = {
        "Model/Prompt": label,
        "Elo": round(ratings.get(label, 1500)),
        "Win %": f"{wins / total_comps * 100:.0f}%" if total_comps > 0 else "—",
        "Parse Rate": f"{success}/{total}",
    }

    if pass_number == 1:
        comply = run_compliance.get(run["id"], 0)
        row["Comply%"] = f"{comply * 100:.0f}%"

    row["Accuracy"] = run_accuracy.get(run["id"], "—")
    row["Cost"] = f"${run.get('total_cost_usd', 0) or 0:.4f}"
    row["Latency"] = f"{(run.get('total_duration_ms', 0) or 0) / 1000:.1f}s"

    leaderboard.append(row)

leaderboard.sort(key=lambda x: x["Elo"], reverse=True)
st.dataframe(pd.DataFrame(leaderboard), use_container_width=True, hide_index=True)

if pass_number == 1 and pass_runs:
    st.subheader("Field-Level Population Rate")
    st.caption("Percentage of postings where each field was non-null, by run.")

    fields = [
        "role_archetype",
        "role_level",
        "employment_type",
        "pay_type",
        "pay_min",
        "pay_max",
        "has_commission",
        "has_benefits",
        "tools_mentioned",
        "kpis_mentioned",
        "store_count",
    ]

    field_data = []
    for run in pass_runs:
        label = run_labels[run["id"]]
        results = loop.run_until_complete(store.get_results(run["id"]))
        parsed = [json.loads(r["parsed_result"]) for r in results if r["parsed_result"]]
        total = len(parsed) if parsed else 1

        row = {"Model/Prompt": label}
        for f in fields:
            non_null = sum(
                1 for p in parsed if p.get(f) is not None and p.get(f) != [] and p.get(f) != ""
            )
            row[f] = f"{non_null / total * 100:.0f}%"
        field_data.append(row)

    if field_data:
        st.dataframe(pd.DataFrame(field_data), use_container_width=True, hide_index=True)
