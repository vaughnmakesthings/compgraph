"""Pipeline Health — scrape run history, enrichment coverage, and errors."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from compgraph.dashboard import configure_logging
from compgraph.dashboard.db import get_session
from compgraph.dashboard.diagnostics import render_diagnostics_sidebar
from compgraph.dashboard.queries import (
    get_enrichment_coverage,
    get_error_summary,
    get_recent_scrape_runs,
)

configure_logging()

st.set_page_config(page_title="Pipeline Health", layout="wide")
st.title("Pipeline Health")

render_diagnostics_sidebar()


@st.cache_data(ttl=60)
def _load_scrape_runs() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_recent_scrape_runs(session))


@st.cache_data(ttl=60)
def _load_coverage() -> dict[str, Any]:
    with get_session() as session:
        return dict(get_enrichment_coverage(session))


@st.cache_data(ttl=60)
def _load_errors() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_error_summary(session))


# --- Enrichment coverage ---
st.subheader("Enrichment Coverage")
coverage = _load_coverage()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Active", coverage["total_active"])
c2.metric("Enriched", coverage["enriched"])
c3.metric("With Brands", coverage["with_brands"])
c4.metric("Unenriched", coverage["unenriched"])

# --- Recent scrape runs ---
st.subheader("Recent Scrape Runs")
runs = _load_scrape_runs()
if runs:
    df = pd.DataFrame(runs)

    def _style_status(val: str) -> str:
        if val == "completed":
            return "color: green"
        if val == "failed":
            return "color: red"
        return ""

    styled = df.style.map(_style_status, subset=["status"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.info("No scrape runs recorded yet.")

# --- Error summary ---
st.subheader("Errors (Last 7 Days)")
errors = _load_errors()
if errors:
    st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
else:
    st.success("No errors in the last 7 days.")

# --- Refresh ---
if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
