"""Pipeline Health — scrape run history, enrichment coverage, and errors."""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd
import streamlit as st

from compgraph.dashboard import configure_logging
from compgraph.dashboard.db import get_session
from compgraph.dashboard.diagnostics import render_diagnostics_sidebar
from compgraph.dashboard.queries import (
    FRESHNESS_ICONS,
    freshness_color,
    get_enrichment_coverage,
    get_enrichment_pass_breakdown,
    get_error_summary,
    get_last_scrape_timestamps,
    get_recent_scrape_runs,
)

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
def _load_pass_breakdown() -> dict[str, Any]:
    with get_session() as session:
        return dict(get_enrichment_pass_breakdown(session))


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
            icon = FRESHNESS_ICONS[color]
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

# --- Enrichment pass breakdown ---
try:
    breakdown = _load_pass_breakdown()
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Total Active", breakdown["total_active"])
    p2.metric("Unenriched", breakdown["unenriched"])
    p3.metric("Pass 1 Only", breakdown["pass1_only"])
    p4.metric("Pass 1 + 2 (Complete)", breakdown["fully_enriched"])
except Exception:
    logger.exception("Failed to load enrichment pass breakdown")

# --- Active enrichment run (best-effort API call) ---
try:
    import requests as _req

    _api_base = os.environ.get("COMPGRAPH_API_URL", "http://localhost:8000")
    _enrich_resp = _req.get(f"{_api_base}/api/enrich/status", timeout=3)
    if _enrich_resp.status_code == 200:
        _enrich_data = _enrich_resp.json()
        _enrich_status = _enrich_data.get("status", "idle")
        if _enrich_status not in ("idle", "completed", "failed"):
            st.info(
                f"Enrichment: **{_enrich_status.upper()}** "
                f"(started {_enrich_data.get('started_at', 'unknown')})"
            )
            if _enrich_data.get("pass1_result"):
                _p1r = _enrich_data["pass1_result"]
                st.caption(
                    f"Pass 1: {_p1r['succeeded']} succeeded, "
                    f"{_p1r['failed']} failed, {_p1r['skipped']} skipped"
                )
            if _enrich_data.get("pass2_result"):
                _p2r = _enrich_data["pass2_result"]
                st.caption(
                    f"Pass 2: {_p2r['succeeded']} succeeded, "
                    f"{_p2r['failed']} failed, {_p2r['skipped']} skipped"
                )
except Exception:
    logger.debug("Enrichment status API unavailable", exc_info=True)

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
        if row.get("scrape_status") == "completed":
            return ["color: green"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(_style_row, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)
    st.caption("Status shows scrape phase only. Enrichment runs separately after scrape completes.")
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
