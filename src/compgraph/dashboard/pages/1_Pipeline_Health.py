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
    get_enrichment_pass_breakdown,
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
def _load_pass_breakdown() -> dict[str, Any]:
    with get_session() as session:
        return dict(get_enrichment_pass_breakdown(session))


@st.cache_data(ttl=_cache_ttl)
def _load_errors() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_error_summary(session))


@st.cache_data(ttl=_cache_ttl)
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
    st.error("Failed to load enrichment pass breakdown. Check server logs for details.")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Total Active", "—")
    p2.metric("Unenriched", "—")
    p3.metric("Pass 1 Only", "—")
    p4.metric("Pass 1 + 2 (Complete)", "—")

# --- Active enrichment run (best-effort API call) ---
_enrich_data = api_get("/api/enrich/status", on_error="log")
if _enrich_data is not None:
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
        # Token usage metrics
        _tok_in = _enrich_data.get("total_input_tokens", 0)
        _tok_out = _enrich_data.get("total_output_tokens", 0)
        _api_calls = _enrich_data.get("total_api_calls", 0)
        _dedup_saved = _enrich_data.get("total_dedup_saved", 0)
        if _tok_in or _tok_out or _api_calls:
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Input Tokens", f"{_tok_in:,}")
            t2.metric("Output Tokens", f"{_tok_out:,}")
            t3.metric("API Calls", f"{_api_calls:,}")
            t4.metric("Dedup Saved", f"{_dedup_saved:,}")
        if _enrich_data.get("circuit_breaker_tripped"):
            st.warning(
                f"Circuit breaker tripped: {_enrich_data.get('error_summary', 'unknown reason')}"
            )
    elif _enrich_status in ("completed", "failed"):
        with st.expander(
            f"Last enrichment run: {_enrich_status.upper()} "
            f"({_enrich_data.get('finished_at', 'unknown')})"
        ):
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
            _tok_in = _enrich_data.get("total_input_tokens", 0)
            _tok_out = _enrich_data.get("total_output_tokens", 0)
            _api_calls = _enrich_data.get("total_api_calls", 0)
            _dedup_saved = _enrich_data.get("total_dedup_saved", 0)
            if _tok_in or _tok_out or _api_calls:
                t1, t2, t3, t4 = st.columns(4)
                t1.metric("Input Tokens", f"{_tok_in:,}")
                t2.metric("Output Tokens", f"{_tok_out:,}")
                t3.metric("API Calls", f"{_api_calls:,}")
                t4.metric("Dedup Saved", f"{_dedup_saved:,}")
            if _enrich_data.get("circuit_breaker_tripped"):
                st.warning(
                    f"Circuit breaker tripped: "
                    f"{_enrich_data.get('error_summary', 'unknown reason')}"
                )
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
