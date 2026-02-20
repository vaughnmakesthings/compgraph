"""Pipeline Health — scrape run history, enrichment coverage, and errors."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import streamlit as st

from compgraph.dashboard import configure_logging
from compgraph.dashboard.api import api_get
from compgraph.dashboard.db import get_session
from compgraph.dashboard.diagnostics import render_diagnostics_sidebar
from compgraph.dashboard.queries import (
    FRESHNESS_ICONS,
    freshness_color,
    get_enrichment_coverage,
    get_error_summary,
    get_last_scrape_timestamps,
    get_recent_scrape_runs,
)

configure_logging()
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Pipeline Health", layout="wide")
st.title("Pipeline Health")
st.caption(f"Last refreshed: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")

render_diagnostics_sidebar()

_pipeline_status = api_get("/api/pipeline/status", on_error="log")
_is_active = _pipeline_status is not None and _pipeline_status.get("system_state") in (
    "scraping",
    "enriching",
)
_cache_ttl = 5 if _is_active else 60


@st.cache_data(ttl=_cache_ttl)
def _load_scrape_runs() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_recent_scrape_runs(session))


@st.cache_data(ttl=_cache_ttl)
def _load_coverage() -> dict[str, Any]:
    with get_session() as session:
        return dict(get_enrichment_coverage(session))


@st.cache_data(ttl=_cache_ttl)
def _load_errors() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_error_summary(session))


@st.cache_data(ttl=_cache_ttl)
def _load_freshness() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_last_scrape_timestamps(session))


def _render_enrichment_details(data: dict[str, Any]) -> None:
    p1r = data.get("pass1_result")
    if isinstance(p1r, dict):
        st.caption(
            f"Pass 1: {p1r.get('succeeded', 0)} succeeded, "
            f"{p1r.get('failed', 0)} failed, {p1r.get('skipped', 0)} skipped"
        )
    p2r = data.get("pass2_result")
    if isinstance(p2r, dict):
        st.caption(
            f"Pass 2: {p2r.get('succeeded', 0)} succeeded, "
            f"{p2r.get('failed', 0)} failed, {p2r.get('skipped', 0)} skipped"
        )
    tok_in = data.get("total_input_tokens", 0) or 0
    tok_out = data.get("total_output_tokens", 0) or 0
    api_calls = data.get("total_api_calls", 0) or 0
    dedup_saved = data.get("total_dedup_saved", 0) or 0
    if tok_in or tok_out or api_calls:
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Input Tokens", f"{tok_in:,}")
        t2.metric("Output Tokens", f"{tok_out:,}")
        t3.metric("API Calls", f"{api_calls:,}")
        t4.metric("Dedup Saved", f"{dedup_saved:,}")
    if data.get("circuit_breaker_tripped"):
        st.warning(f"Circuit breaker tripped: {data.get('error_summary', 'unknown reason')}")


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
c1.metric("Total Active", coverage.get("total_active", "—"))
c2.metric("Enriched", coverage.get("enriched", "—"))
c3.metric("With Brands", coverage.get("with_brands", "—"))
c4.metric("Unenriched", coverage.get("unenriched", "—"))

# --- Enrichment pass breakdown (uses same cached coverage data) ---
p1, p2, p3, p4 = st.columns(4)
p1.metric("Total Active", coverage.get("total_active", "—"))
p2.metric("Unenriched", coverage.get("unenriched", "—"))
p3.metric("Pass 1 Only", coverage.get("pass1_only", "—"))
p4.metric("Pass 1 + 2 (Complete)", coverage.get("fully_enriched", "—"))

# --- Active enrichment run (best-effort API call) ---
_enrich_data = api_get("/api/enrich/status", on_error="log")
if _enrich_data is not None:
    _enrich_status = _enrich_data.get("status", "idle")
    if _enrich_status not in ("idle", "success", "partial", "failed"):
        st.info(
            f"Enrichment: **{_enrich_status.upper()}** "
            f"(started {_enrich_data.get('started_at', 'unknown')})"
        )
        _render_enrichment_details(_enrich_data)
    elif _enrich_status in ("success", "partial", "failed"):
        with st.expander(
            f"Last enrichment run: {_enrich_status.upper()} "
            f"({_enrich_data.get('finished_at', 'unknown')})"
        ):
            _render_enrichment_details(_enrich_data)
            if _enrich_data.get("error_summary") and not _enrich_data.get(
                "circuit_breaker_tripped"
            ):
                st.error(f"Error: {_enrich_data['error_summary']}")

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
