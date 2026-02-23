"""Page 4: Field-level accuracy review — confirm or correct model extractions."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import streamlit as st

from eval.ground_truth import REVIEWABLE_FIELDS
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

# --- Header row: title + run selector + progress ---
head_col1, head_col2 = st.columns([1, 2])
with head_col1:
    st.header("Accuracy Review")
with head_col2:
    runs = loop.run_until_complete(store.get_all_runs())
    if not runs:
        st.info("No runs yet. Run an evaluation first.")
        st.stop()
    run_labels = {
        r["id"]: f"{r['model']}/{r['prompt_version']} (Pass {r['pass_number']})" for r in runs
    }
    selected_run_id = st.selectbox(
        "Run",
        list(run_labels.keys()),
        format_func=lambda x: run_labels[x],
        label_visibility="collapsed",
    )

results = loop.run_until_complete(store.get_results(selected_run_id))
corpus = loop.run_until_complete(store.get_corpus())
corpus_map = {p["id"]: p for p in corpus}

parsed_results = [r for r in results if r["parsed_result"]]
if not parsed_results:
    st.warning("No successfully parsed results in this run.")
    st.stop()

if st.session_state.get("_active_run") != selected_run_id:
    st.session_state._active_run = selected_run_id
    st.session_state.review_idx = 0

reviewed_count = loop.run_until_complete(store.get_reviewed_count(selected_run_id))
total_count = len(parsed_results)

# Progress + controls row
prog_col1, prog_col2 = st.columns([3, 1])
with prog_col1:
    st.progress(reviewed_count / total_count if total_count > 0 else 0)
    st.caption(f"{reviewed_count}/{total_count} reviewed")
with prog_col2:
    skip_reviewed = st.checkbox("Skip reviewed", value=False)

idx = st.session_state.get("review_idx", 0)
idx = min(idx, len(parsed_results) - 1)

if skip_reviewed:
    found = False
    for i in range(idx, len(parsed_results)):
        existing_reviews = loop.run_until_complete(store.get_field_reviews(parsed_results[i]["id"]))
        if not existing_reviews:
            idx = i
            found = True
            break
    if not found:
        st.success("All postings in this run have been reviewed!")
        st.stop()

result = parsed_results[idx]
posting = corpus_map.get(result["posting_id"], {})
parsed = (
    json.loads(result["parsed_result"])
    if isinstance(result["parsed_result"], str)
    else result["parsed_result"]
)

existing_reviews = loop.run_until_complete(store.get_field_reviews(result["id"]))
review_map = {r["field_name"]: r for r in existing_reviews}

# --- Main two-column layout ---
col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.subheader(posting.get("title", "Unknown"))
    st.caption(f"{posting.get('company_slug', '')} | {posting.get('location', '')}")

    full_text = posting.get("full_text", "")
    st.html(
        f'<div style="height:600px;overflow-y:auto;padding:1rem;'
        f'background:#1a1a2e;color:#eee;border-radius:8px;font-size:14px;line-height:1.5">'
        f"{full_text}</div>"
    )

with col_right:
    # Header with nav
    r_head1, r_head2 = st.columns([2, 1])
    with r_head1:
        st.subheader("Model Extraction")
    with r_head2:
        st.caption(f"Posting {idx + 1}/{len(parsed_results)}")

    if st.button(
        "Mark All Correct", key=f"mark_all_{idx}", use_container_width=True, type="primary"
    ):
        for field_name in REVIEWABLE_FIELDS:
            value = parsed.get(field_name)
            model_value = json.dumps(value) if value is not None else None
            loop.run_until_complete(
                store.upsert_field_review(
                    result_id=result["id"],
                    field_name=field_name,
                    model_value=model_value,
                    is_correct=1,
                )
            )
        st.session_state.review_idx = min(idx + 1, len(parsed_results) - 1)
        st.rerun()

    # Compact field list — single row per field
    for field_name in REVIEWABLE_FIELDS:
        value = parsed.get(field_name)
        display_value = (
            json.dumps(value)
            if isinstance(value, (list, dict))
            else str(value)
            if value is not None
            else "null"
        )

        existing = review_map.get(field_name)
        if existing:
            if existing["is_correct"] == -1:
                status = "na"
            elif existing["is_correct"] and existing.get("correct_value"):
                status = "improved"
            elif existing["is_correct"]:
                status = "correct"
            else:
                status = "wrong"
        else:
            status = "pending"

        # 5-column compact row: field | value | ✓ | ✗ | —
        c1, c2, c3, c4, c5 = st.columns([5, 6, 1, 1, 1], vertical_alignment="center")

        with c1:
            if status == "correct":
                st.markdown(f":green[**{field_name}**]")
            elif status == "improved":
                st.markdown(f":blue[**{field_name}**]")
            elif status == "wrong":
                st.markdown(f":red[**{field_name}**]")
            elif status == "na":
                st.markdown(f":gray[**{field_name}**]")
            else:
                st.markdown(f"**{field_name}**")

        with c2:
            if status == "na":
                st.markdown(":gray[can't assess]")
            elif status == "improved" and existing and existing.get("correct_value"):
                st.markdown(f"{display_value} :blue[→ {existing['correct_value']}]")
            elif status == "wrong" and existing and existing.get("correct_value"):
                st.markdown(f"~~{display_value}~~ :green[{existing['correct_value']}]")
            else:
                st.code(display_value, language=None)

        with c3:
            if st.button(
                "\u2713",
                key=f"ok_{field_name}_{idx}",
                type="primary" if status in ("correct", "improved") else "secondary",
                help="Correct (type a better value below first to mark as improvable)",
            ):
                model_value = json.dumps(value) if value is not None else None
                # Check if there's an improvement suggestion in the correction box
                improve_val = st.session_state.get(f"fix_{field_name}_{idx}", "")
                loop.run_until_complete(
                    store.upsert_field_review(
                        result_id=result["id"],
                        field_name=field_name,
                        model_value=model_value,
                        is_correct=1,
                        correct_value=improve_val if improve_val else None,
                    )
                )
                st.session_state.pop(f"show_correction_{field_name}", None)
                st.rerun()

        with c4:
            if st.button(
                "\u2717",
                key=f"x_{field_name}_{idx}",
                type="primary" if status == "wrong" else "secondary",
            ):
                st.session_state[f"show_correction_{field_name}"] = True
                st.rerun()

        with c5:
            if st.button(
                "\u2014",
                key=f"na_{field_name}_{idx}",
                help="Can't assess — info not in posting text",
                type="primary" if status == "na" else "secondary",
            ):
                model_value = json.dumps(value) if value is not None else None
                loop.run_until_complete(
                    store.upsert_field_review(
                        result_id=result["id"],
                        field_name=field_name,
                        model_value=model_value,
                        is_correct=-1,
                    )
                )
                st.rerun()

        # Correction input inline below the row
        show_box = (
            st.session_state.get(f"show_correction_{field_name}")
            or status == "wrong"
            or status == "improved"
        )
        if show_box:
            fix_c1, fix_c2 = st.columns([5, 1])
            with fix_c1:
                correct_val = st.text_input(
                    "Correct value",
                    value=existing.get("correct_value", "") if existing else "",
                    key=f"fix_{field_name}_{idx}",
                    label_visibility="collapsed",
                    placeholder=f"Better value for {field_name} (then click ✓ or Save)",
                )
            with fix_c2:
                if st.button("Save", key=f"save_{field_name}_{idx}"):
                    model_value = json.dumps(value) if value is not None else None
                    loop.run_until_complete(
                        store.upsert_field_review(
                            result_id=result["id"],
                            field_name=field_name,
                            model_value=model_value,
                            is_correct=0,
                            correct_value=correct_val if correct_val else None,
                        )
                    )
                    st.session_state.pop(f"show_correction_{field_name}", None)
                    st.rerun()

# Navigation at bottom
st.divider()
nav1, nav2, nav3 = st.columns([1, 1, 1])
with nav1:
    if st.button("← Previous", disabled=idx == 0, use_container_width=True):
        st.session_state.review_idx = idx - 1
        st.rerun()
with nav2:
    st.markdown(
        f"<div style='text-align:center;padding-top:6px'>{idx + 1} / {len(parsed_results)}</div>",
        unsafe_allow_html=True,
    )
with nav3:
    if st.button("Next →", disabled=idx >= len(parsed_results) - 1, use_container_width=True):
        st.session_state.review_idx = idx + 1
        st.rerun()
