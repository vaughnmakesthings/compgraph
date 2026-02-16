"""Pipeline Health — scrape run history, enrichment coverage, and errors."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from compgraph.dashboard import configure_logging
from compgraph.dashboard.db import get_session
from compgraph.dashboard.diagnostics import render_diagnostics_sidebar
from compgraph.dashboard.queries import (
    freshness_color,
    get_enrichment_coverage,
    get_error_summary,
    get_last_scrape_timestamps,
    get_recent_scrape_runs,
)

_FRESHNESS_ICONS = {
    "green": ":green_circle:",
    "yellow": ":yellow_circle:",
    "red": ":red_circle:",
    "gray": ":white_circle:",
}

configure_logging()
logger = logging.getLogger(__name__)

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


@st.cache_data(ttl=60)
def _load_freshness() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_last_scrape_timestamps(session))


# --- Data freshness per company ---
st.subheader("Data Freshness")
try:
    freshness_data = _load_freshness()
    company_entries = [e for e in freshness_data if e["slug"] != "__global__"]
    if company_entries:
        cols = st.columns(len(company_entries))
        for col, entry in zip(cols, company_entries, strict=True):
            ts = entry["last_scraped_at"]
            color = freshness_color(ts)
            icon = _FRESHNESS_ICONS[color]
            ts_str = ts.strftime("%Y-%m-%d %H:%M UTC") if ts else "Never"
            col.markdown(f"{icon} **{entry['name']}**")
            col.caption(f"Last scraped: {ts_str}")
    else:
        st.info("No companies configured.")
except Exception:
    logger.exception("Failed to load freshness timestamps")
    st.error("Failed to load freshness data.")

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

    def _style_row(row: pd.Series) -> list[str]:
        if row.get("has_errors"):
            return ["color: red"] * len(row)
        if row.get("warnings"):
            return ["color: orange"] * len(row)
        if row.get("status") == "completed":
            return ["color: green"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(_style_row, axis=1)
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
