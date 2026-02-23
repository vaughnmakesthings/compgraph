"""Page 2: Side-by-side review with Elo voting."""

from __future__ import annotations

import asyncio
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import streamlit as st

from eval.store import EvalStore
from eval.ui.components import render_pass1_diff, render_pass2_diff

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
st.header("Side-by-Side Review")

runs = loop.run_until_complete(store.get_all_runs())
if len(runs) < 2:
    st.info("Need at least 2 completed runs to compare. Go to Run Tests first.")
    st.stop()

run_labels = {r["id"]: f"Run #{r['id']} (Pass {r['pass_number']})" for r in runs}

col1, col2 = st.columns(2)
with col1:
    run_a_id = st.selectbox("Run A", list(run_labels.keys()), format_func=lambda x: run_labels[x])
with col2:
    run_b_id = st.selectbox(
        "Run B",
        list(run_labels.keys()),
        index=min(1, len(runs) - 1),
        format_func=lambda x: run_labels[x],
    )

if run_a_id == run_b_id:
    st.warning("Select two different runs to compare.")
    st.stop()

run_a_data = next(r for r in runs if r["id"] == run_a_id)
run_b_data = next(r for r in runs if r["id"] == run_b_id)
if run_a_data["pass_number"] != run_b_data["pass_number"]:
    st.warning("Select two runs with the same pass number to compare.")
    st.stop()
pass_number = run_a_data["pass_number"]

results_a = loop.run_until_complete(store.get_results(run_a_id))
results_b = loop.run_until_complete(store.get_results(run_b_id))

a_by_posting = {r["posting_id"]: r for r in results_a}
b_by_posting = {r["posting_id"]: r for r in results_b}

common_ids = sorted(set(a_by_posting.keys()) & set(b_by_posting.keys()))
if not common_ids:
    st.warning("No overlapping postings between these runs.")
    st.stop()

current_runs_key = f"{run_a_id}_{run_b_id}"
if st.session_state.get("_runs_key") != current_runs_key:
    st.session_state.review_idx = 0
    st.session_state.swap_map = {pid: random.random() > 0.5 for pid in common_ids}
    st.session_state._runs_key = current_runs_key

idx = st.session_state.review_idx
posting_id = common_ids[idx]

st.progress((idx + 1) / len(common_ids))
st.caption(f"Comparison {idx + 1} of {len(common_ids)}")

corpus = loop.run_until_complete(store.get_corpus())
posting = next((p for p in corpus if p["id"] == posting_id), None)

if posting:
    st.subheader(f"{posting['title']}")
    st.caption(f"{posting.get('company_slug', '')} | {posting.get('location', '')}")
    with st.expander("Full posting text"):
        st.html(
            f'<div style="max-height:500px;overflow-y:auto;padding:1rem;'
            f'background:#1a1a2e;color:#eee;border-radius:8px;font-size:14px;line-height:1.5">'
            f"{posting['full_text']}</div>"
        )

swapped = st.session_state.swap_map.get(posting_id, False)
if swapped:
    left_result, right_result = b_by_posting[posting_id], a_by_posting[posting_id]
else:
    left_result, right_result = a_by_posting[posting_id], b_by_posting[posting_id]

col_left, col_right = st.columns(2)
with col_left:
    st.markdown("**Option A**")
with col_right:
    st.markdown("**Option B**")

parsed_left = json.loads(left_result["parsed_result"]) if left_result.get("parsed_result") else None
parsed_right = (
    json.loads(right_result["parsed_result"]) if right_result.get("parsed_result") else None
)

if pass_number == 1:
    render_pass1_diff(parsed_left, parsed_right)
else:
    render_pass2_diff(parsed_left, parsed_right)

st.divider()
notes = st.text_input("Notes (optional)", key=f"notes_{idx}")

vote_cols = st.columns(4)


def _vote(winner: str):
    """Record a vote and advance."""
    actual_winner = winner
    if swapped:
        if winner == "a":
            actual_winner = "b"
        elif winner == "b":
            actual_winner = "a"
    loop.run_until_complete(
        store.insert_comparison(
            posting_id,
            a_by_posting[posting_id]["id"],
            b_by_posting[posting_id]["id"],
            actual_winner,
            notes,
        )
    )
    st.session_state.review_idx = min(idx + 1, len(common_ids) - 1)
    st.rerun()


with vote_cols[0]:
    if st.button("A is better", key=f"vote_a_{idx}", use_container_width=True):
        _vote("a")
with vote_cols[1]:
    if st.button("B is better", key=f"vote_b_{idx}", use_container_width=True):
        _vote("b")
with vote_cols[2]:
    if st.button("Tie", key=f"vote_tie_{idx}", use_container_width=True):
        _vote("tie")
with vote_cols[3]:
    if st.button("Both bad", key=f"vote_bad_{idx}", use_container_width=True):
        _vote("both_bad")

nav_cols = st.columns(2)
with nav_cols[0]:
    if st.button("← Previous") and idx > 0:
        st.session_state.review_idx = idx - 1
        st.rerun()
with nav_cols[1]:
    if st.button("Next →") and idx < len(common_ids) - 1:
        st.session_state.review_idx = idx + 1
        st.rerun()
