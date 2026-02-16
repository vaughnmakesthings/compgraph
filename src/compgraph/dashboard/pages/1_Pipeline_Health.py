"""Pipeline Health — scrape run history, enrichment coverage, and errors."""

import logging

import pandas as pd
import streamlit as st

from compgraph.dashboard.db import get_session
from compgraph.dashboard.queries import (
    get_enrichment_coverage,
    get_error_summary,
    get_recent_scrape_runs,
)

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Pipeline Health", layout="wide")
st.title("Pipeline Health")


@st.cache_data(ttl=60)
def _load_scrape_runs() -> list[dict]:
    with get_session() as session:
        return get_recent_scrape_runs(session)


@st.cache_data(ttl=60)
def _load_coverage() -> dict:
    with get_session() as session:
        return get_enrichment_coverage(session)


@st.cache_data(ttl=60)
def _load_errors() -> list[dict]:
    with get_session() as session:
        return get_error_summary(session)


# --- Enrichment coverage ---
st.subheader("Enrichment Coverage")
try:
    coverage = _load_coverage()
except Exception:
    logger.exception("Failed to load enrichment coverage")
    st.error("Failed to load enrichment coverage. Check server logs for details.")
    coverage = {"total_active": "—", "enriched": "—", "with_brands": "—", "unenriched": "—"}

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Active", coverage["total_active"])
c2.metric("Enriched", coverage["enriched"])
c3.metric("With Brands", coverage["with_brands"])
c4.metric("Unenriched", coverage["unenriched"])

# --- Recent scrape runs ---
st.subheader("Recent Scrape Runs")
try:
    runs = _load_scrape_runs()
except Exception:
    logger.exception("Failed to load scrape runs")
    st.error("Failed to load scrape runs. Check server logs for details.")
    runs = []

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
errors_loaded = True
try:
    errors = _load_errors()
except Exception:
    logger.exception("Failed to load error summary")
    st.error("Failed to load error summary. Check server logs for details.")
    errors = []
    errors_loaded = False

if errors:
    st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
elif errors_loaded:
    st.success("No errors in the last 7 days.")

# --- Refresh ---
if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
