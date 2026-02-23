"""Page 5: Prompt Diff — compare accuracy between runs using ground truth."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import pandas as pd
import streamlit as st

from eval.ground_truth import (
    compute_diff_report,
    export_error_patterns_csv,
    extract_ground_truth,
    score_candidate_run,
)
from eval.store import EvalStore

st.set_page_config(layout="wide")

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

st.header("Prompt Diff")

# --- Run selectors ---
reviewed_runs = loop.run_until_complete(store.get_runs_with_reviews())
all_runs = loop.run_until_complete(store.get_all_runs())

if not reviewed_runs:
    st.info(
        "No runs have field reviews yet. Review some postings on the Accuracy Review page first."
    )
    st.stop()


def _run_label(r: dict) -> str:
    return f"{r['model']}/{r['prompt_version']} (Pass {r['pass_number']}, run #{r['id']})"


col_bl, col_cand, col_btn = st.columns([2, 2, 1])

with col_bl:
    bl_labels = {r["id"]: _run_label(r) for r in reviewed_runs}
    baseline_id = st.selectbox(
        "Ground Truth Source (reviewed run)",
        list(bl_labels.keys()),
        format_func=lambda x: bl_labels[x],
    )

# Filter candidate to same pass_number
baseline_run = next(r for r in reviewed_runs if r["id"] == baseline_id)
candidate_runs = [r for r in all_runs if r["pass_number"] == baseline_run["pass_number"]]

with col_cand:
    cand_labels = {r["id"]: _run_label(r) for r in candidate_runs}
    candidate_id = st.selectbox(
        "Candidate run",
        list(cand_labels.keys()),
        format_func=lambda x: cand_labels[x],
        index=None,
        placeholder="(self-score if none selected)",
    )

with col_btn:
    st.write("")  # spacer
    run_diff = st.button("Run Diff", type="primary", use_container_width=True)

if not run_diff:
    st.caption("Select runs and click 'Run Diff' to compare.")
    st.stop()

# --- Compute diff ---
with st.spinner("Extracting ground truth and scoring..."):
    ground_truth = loop.run_until_complete(extract_ground_truth(store, baseline_id))

    if not ground_truth:
        st.error(
            f"No usable field reviews found for run #{baseline_id}. "
            "Review some postings first (mark correct/wrong with corrections)."
        )
        st.stop()

    candidate_run = None
    if candidate_id and candidate_id != baseline_id:
        candidate_run = next((r for r in all_runs if r["id"] == candidate_id), None)
        scores, bl_accuracy = loop.run_until_complete(
            score_candidate_run(store, ground_truth, candidate_id, baseline_id)
        )
        report = compute_diff_report(scores, baseline_run, candidate_run, bl_accuracy)
    else:
        # Self-score mode
        scores, _ = loop.run_until_complete(score_candidate_run(store, ground_truth, baseline_id))
        report = compute_diff_report(scores, baseline_run, None, None)

# --- Threshold warning ---
if report.threshold_warning:
    st.warning(
        f"Only {report.reviewed_posting_count} postings reviewed (recommended: 10+). "
        "Results may not generalize."
    )

# --- Metric cards ---
m1, m2, m3 = st.columns(3)
with m1:
    if report.overall_baseline_accuracy is not None:
        st.metric("Baseline", f"{report.overall_baseline_accuracy * 100:.1f}%")
    else:
        st.metric(
            "Accuracy",
            f"{report.overall_candidate_accuracy * 100:.1f}%"
            if report.overall_candidate_accuracy is not None
            else "N/A",
        )

with m2:
    if report.overall_candidate_accuracy is not None and report.candidate_label:
        st.metric("Candidate", f"{report.overall_candidate_accuracy * 100:.1f}%")

with m3:
    if report.overall_delta is not None:
        delta_pp = report.overall_delta * 100
        st.metric("Delta", f"{delta_pp:+.1f}pp", delta=f"{delta_pp:+.1f}pp")

ci_text = ""
if report.overall_confidence_interval:
    lo, hi = report.overall_confidence_interval
    ci_text = f" — 95% CI: [{lo * 100:.1f}%, {hi * 100:.1f}%]"

st.caption(
    f"Ground truth: {report.reviewed_posting_count} postings, "
    f"{sum(d.reviewed_count for d in report.field_diffs)} fields{ci_text}"
)

# --- Per-field accuracy table ---
st.subheader("Per-Field Accuracy")

rows = []
for d in report.field_diffs:
    row = {
        "Field": d.field_name,
        "Candidate %": round(d.candidate_accuracy * 100, 1),
        "Reviews": d.reviewed_count,
    }
    if d.confidence_interval:
        lo, hi = d.confidence_interval
        row["95% CI"] = f"[{lo * 100:.1f}%, {hi * 100:.1f}%]"
    else:
        row["95% CI"] = ""
    if report.candidate_label:
        row["Baseline %"] = (
            round(d.baseline_accuracy * 100, 1) if d.baseline_accuracy is not None else None
        )
        row["Delta (pp)"] = round(d.delta * 100, 1) if d.delta is not None else None
        row["Regressions"] = d.regressions
        row["Improvements"] = d.improvements
    rows.append(row)

if rows:
    df = pd.DataFrame(rows)

    column_config = {
        "Candidate %": st.column_config.ProgressColumn(
            "Candidate %", min_value=0, max_value=100, format="%.1f%%"
        ),
    }
    if report.candidate_label:
        column_config["Baseline %"] = st.column_config.ProgressColumn(
            "Baseline %", min_value=0, max_value=100, format="%.1f%%"
        )
        column_config["Delta (pp)"] = st.column_config.NumberColumn("Delta (pp)", format="%+.1f")

    # Reorder columns for diff mode
    if report.candidate_label:
        col_order = [
            "Field",
            "Baseline %",
            "Candidate %",
            "Delta (pp)",
            "95% CI",
            "Reviews",
            "Regressions",
            "Improvements",
        ]
        df = df[[c for c in col_order if c in df.columns]]

    st.dataframe(df, use_container_width=True, hide_index=True, column_config=column_config)

# --- Regressions drilldown ---
if report.candidate_label:
    regression_scores = [s for s in scores if s.is_regression]
    if regression_scores:
        st.subheader("Regressions")
        st.caption("Fields that were correct in baseline but wrong in candidate.")

        # Group regressions by field
        from collections import defaultdict

        by_field: dict[str, list] = defaultdict(list)
        for s in regression_scores:
            by_field[s.field_name].append(s)

        corpus = loop.run_until_complete(store.get_corpus())
        corpus_map = {p["id"]: p for p in corpus}

        for field_name, field_regs in by_field.items():
            with st.expander(f"{field_name} ({len(field_regs)} regressions)"):
                for s in field_regs:
                    posting = corpus_map.get(s.posting_id, {})
                    title = posting.get("title", s.posting_id)
                    st.markdown(
                        f"**{title}** — "
                        f"candidate: `{s.candidate_value}`, "
                        f"truth: `{s.ground_truth_value}`"
                    )

# --- Error patterns ---
any_errors = any(d.error_patterns for d in report.field_diffs)
if any_errors:
    st.subheader("Error Patterns")

    pattern_rows = []
    for d in report.field_diffs:
        for pattern, count in d.error_patterns:
            pattern_rows.append(
                {
                    "Field": d.field_name,
                    "Pattern": pattern,
                    "Count": count,
                }
            )

    if pattern_rows:
        st.dataframe(
            pd.DataFrame(pattern_rows),
            use_container_width=True,
            hide_index=True,
        )

        # CSV download
        csv_content = export_error_patterns_csv(report)
        st.download_button(
            "Download Error Patterns CSV",
            csv_content,
            file_name="prompt_diff_errors.csv",
            mime="text/csv",
        )
