"""CompGraph Dashboard — landing page and Streamlit entrypoint."""

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
    get_last_scrape_timestamps,
    get_per_company_counts,
)

_FRESHNESS_ICONS = {
    "green": ":green_circle:",
    "yellow": ":yellow_circle:",
    "red": ":red_circle:",
    "gray": ":white_circle:",
}

configure_logging()
logger = logging.getLogger(__name__)

st.set_page_config(page_title="CompGraph Dashboard", layout="wide")

st.title("CompGraph Dashboard")
st.caption("Competitive intelligence — pipeline overview")

render_diagnostics_sidebar()


@st.cache_data(ttl=60)
def _load_coverage() -> dict[str, Any]:
    with get_session() as session:
        return dict(get_enrichment_coverage(session))


@st.cache_data(ttl=60)
def _load_company_counts() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_per_company_counts(session))


@st.cache_data(ttl=60)
def _load_freshness() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_last_scrape_timestamps(session))


# --- Data freshness ---
try:
    freshness_data = _load_freshness()
    global_entry = next((e for e in freshness_data if e["slug"] == "__global__"), None)
    global_ts = global_entry["last_scraped_at"] if global_entry else None
    color = freshness_color(global_ts)
    icon = _FRESHNESS_ICONS[color]
    ts_str = global_ts.strftime("%Y-%m-%d %H:%M UTC") if global_ts else "Never"
    st.markdown(f"{icon} **Data as of:** {ts_str}")
except Exception:
    logger.exception("Failed to load freshness timestamps")

# --- Metrics row ---
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

# --- Per-company bar chart ---
st.subheader("Active Postings by Company")
try:
    company_data = _load_company_counts()
except Exception:
    logger.exception("Failed to load company counts")
    st.error("Failed to load company counts. Check server logs for details.")
    company_data = []

if company_data:
    df = pd.DataFrame(company_data).set_index("company")
    st.bar_chart(df["count"])
else:
    st.info("No posting data yet. Run the scraper to populate.")

# --- Refresh ---
if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
