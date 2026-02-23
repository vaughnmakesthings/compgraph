"""Page 1: Run evaluation tests."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import streamlit as st

from eval.config import DEFAULT_CONCURRENCY, MODELS
from eval.prompts import list_prompts
from eval.runner import run_evaluation
from eval.store import EvalStore

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
DB_PATH = str(DATA_DIR / "eval.db")
CORPUS_PATH = str(DATA_DIR / "corpus.json")


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


st.header("Run Evaluation")

if not Path(CORPUS_PATH).exists():
    st.error("No corpus found at `data/corpus.json`. Run `scripts/export_corpus.py` first.")
    st.stop()

store = get_store()

col1, col2, col3 = st.columns(3)

with col1:
    pass_number = st.selectbox("Pass", [1, 2])

with col2:
    model = st.selectbox("Model", list(MODELS.keys()))

with col3:
    prompt_versions = list_prompts(pass_number)
    prompt_version = st.selectbox("Prompt Version", prompt_versions)

concurrency = st.slider("Concurrency", min_value=1, max_value=20, value=DEFAULT_CONCURRENCY)

if st.button("Run Evaluation", type="primary"):
    progress_bar = st.progress(0)
    status = st.empty()

    def on_progress(completed: int, total: int):
        progress_bar.progress(completed / total)
        status.text(f"Processing {completed}/{total} postings...")

    loop = _get_or_create_event_loop()
    with st.spinner("Running evaluation..."):
        summary = loop.run_until_complete(
            run_evaluation(
                store=store,
                pass_number=pass_number,
                model=model,
                prompt_version=prompt_version,
                corpus_path=CORPUS_PATH,
                concurrency=concurrency,
                on_progress=on_progress,
            )
        )

    progress_bar.progress(1.0)
    st.success(
        f"Done! {summary.succeeded}/{summary.total} succeeded, "
        f"${summary.total_cost_usd:.4f} total cost, "
        f"{summary.total_duration_ms / 1000:.1f}s"
    )

# --- Run history ---
st.subheader("Run History")

loop = _get_or_create_event_loop()
runs = loop.run_until_complete(store.get_all_runs())
if runs:
    import pandas as pd

    df = pd.DataFrame(runs)
    for i, run in enumerate(runs):
        results = loop.run_until_complete(store.get_results(run["id"]))
        total = len(results)
        success = sum(1 for r in results if r["parse_success"])
        df.loc[i, "success_rate"] = f"{success}/{total}" if total > 0 else "—"

    display_cols = [
        "id",
        "pass_number",
        "model",
        "prompt_version",
        "success_rate",
        "total_cost_usd",
        "total_duration_ms",
    ]
    st.dataframe(
        df[[c for c in display_cols if c in df.columns]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No runs yet. Run your first evaluation above.")
