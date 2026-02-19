"""CompGraph Dashboard — System Status landing page."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import streamlit as st

from compgraph.dashboard import configure_logging
from compgraph.dashboard.api import api_get, api_post
from compgraph.dashboard.db import get_session
from compgraph.dashboard.diagnostics import render_diagnostics_sidebar
from compgraph.dashboard.queries import (
    FRESHNESS_ICONS,
    freshness_color,
    get_enrichment_coverage,
    get_last_scrape_timestamps,
)

configure_logging()
logger = logging.getLogger(__name__)

st.set_page_config(page_title="CompGraph Dashboard", layout="wide")

render_diagnostics_sidebar()


def _format_elapsed(started_at: str) -> str:
    """Format an ISO timestamp into a human-readable elapsed string like ' (3m 12s)'."""
    try:
        dt = datetime.fromisoformat(started_at)
        secs = (datetime.now(UTC) - dt).total_seconds()
        mins = int(secs // 60)
        return f" ({mins}m {int(secs % 60)}s)"
    except (ValueError, TypeError):
        return ""


# --- Fetch pipeline status ---
pipeline = api_get("/api/pipeline/status")


# --- System State Banner ---
st.title("CompGraph Dashboard")
st.caption(f"Last refreshed: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")

if pipeline is not None:
    state = pipeline["system_state"]
    if state == "idle":
        st.success("System Idle")
    elif state == "scraping":
        started = pipeline["scrape"].get("current_run", {}).get("started_at")
        elapsed = _format_elapsed(started) if started else ""
        st.info(f"Scraping...{elapsed}")
    elif state == "enriching":
        started = pipeline["enrich"].get("current_run", {}).get("started_at")
        elapsed = _format_elapsed(started) if started else ""
        st.info(f"Enriching...{elapsed}")
    elif state == "error":
        st.error("Error — last pipeline run failed")
    else:
        st.warning(f"Unknown state: {state}")
else:
    st.warning("Cannot reach API — status unavailable")


# --- Stage Cards ---
if pipeline is not None:
    col_scrape, col_enrich = st.columns(2)

    with col_scrape:
        st.subheader("Scrape")
        scrape = pipeline["scrape"]
        scrape_status = scrape["status"]

        if scrape_status == "running" and scrape.get("current_run"):
            cr = scrape["current_run"]
            st.markdown("**Status:** :blue[RUNNING]")
            st.metric("Postings Found", cr.get("total_postings_found", 0))
            co_done = cr.get("companies_succeeded", 0)
            co_fail = cr.get("companies_failed", 0)
            co_total = cr.get("total_companies", co_done + co_fail)
            st.metric("Companies Done", f"{co_done + co_fail}/{co_total}")
        elif scrape["last_completed_at"]:
            try:
                dt = datetime.fromisoformat(scrape["last_completed_at"])
                age = datetime.now(UTC) - dt
                if age > timedelta(hours=1):
                    age_str = f"{int(age.total_seconds() // 3600)}h ago"
                else:
                    age_str = f"{int(age.total_seconds() // 60)}m ago"
            except (ValueError, TypeError):
                age_str = "unknown"
            is_ok = scrape_status in ("success", "completed")
            color = "green" if is_ok else "red"
            st.markdown(f"**Status:** :{color}[{scrape_status.upper()}]")
            st.caption(f"Completed {age_str}")
        else:
            st.markdown("**Status:** :gray[NO RUNS]")

    with col_enrich:
        st.subheader("Enrichment")
        enrich = pipeline["enrich"]
        enrich_status = enrich["status"]

        if enrich_status == "running" and enrich.get("current_run"):
            cr = enrich["current_run"]
            st.markdown("**Status:** :blue[RUNNING]")
            p1_total = cr.get("pass1_total", 0)
            p1_done = cr.get("pass1_succeeded", 0)
            p2_total = cr.get("pass2_total", 0)
            p2_done = cr.get("pass2_succeeded", 0)

            if p1_total > 0:
                st.progress(min(p1_done / p1_total, 1.0), text=f"Pass 1: {p1_done}/{p1_total}")
            elif p1_done > 0:
                st.metric("Pass 1 Processed", p1_done)
            else:
                st.caption("Pass 1: starting...")

            if p2_total > 0:
                st.progress(min(p2_done / p2_total, 1.0), text=f"Pass 2: {p2_done}/{p2_total}")
            elif p2_done > 0:
                st.metric("Pass 2 Processed", p2_done)
        elif enrich["last_completed_at"]:
            try:
                dt = datetime.fromisoformat(enrich["last_completed_at"])
                age = datetime.now(UTC) - dt
                if age > timedelta(hours=1):
                    age_str = f"{int(age.total_seconds() // 3600)}h ago"
                else:
                    age_str = f"{int(age.total_seconds() // 60)}m ago"
            except (ValueError, TypeError):
                age_str = "unknown"
            is_ok = enrich_status in ("success", "completed")
            color = "green" if is_ok else "red"
            st.markdown(f"**Status:** :{color}[{enrich_status.upper()}]")
            st.caption(f"Completed {age_str}")
        else:
            st.markdown("**Status:** :gray[NO RUNS]")


# --- Scheduler Row ---
if pipeline is not None:
    st.divider()
    sched = pipeline["scheduler"]
    sched_col1, sched_col2 = st.columns(2)
    with sched_col1:
        if sched["enabled"]:
            next_run = sched.get("next_run_at")
            if next_run:
                st.markdown(f"**Scheduler:** Enabled — next run at `{next_run}`")
            else:
                st.markdown("**Scheduler:** Enabled — no upcoming run")
        else:
            st.markdown("**Scheduler:** Disabled")
    with sched_col2:
        if sched["enabled"]:
            if st.button("Trigger Now"):
                trigger_result = api_get("/api/scheduler/status")
                if trigger_result and trigger_result.get("schedules"):
                    schedule_id = trigger_result["schedules"][0]["schedule_id"]
                    result = api_post(f"/api/scheduler/jobs/{schedule_id}/trigger")
                    if result is not None:
                        st.success("Pipeline triggered!")
                        time.sleep(1)
                        st.rerun()


# --- Data Freshness ---
st.divider()
st.subheader("Data Freshness")

is_active = pipeline is not None and pipeline["system_state"] in ("scraping", "enriching")
_cache_ttl = 5 if is_active else 60


@st.cache_data(ttl=_cache_ttl)
def _load_freshness() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_last_scrape_timestamps(session))


@st.cache_data(ttl=_cache_ttl)
def _load_coverage() -> dict[str, Any]:
    with get_session() as session:
        return dict(get_enrichment_coverage(session))


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
except Exception:
    logger.exception("Failed to load freshness data")

# --- Enrichment coverage ---
st.subheader("Enrichment Coverage")
try:
    coverage = _load_coverage()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Active", coverage["total_active"])
    c2.metric("Enriched", coverage["enriched"])
    c3.metric("With Brands", coverage["with_brands"])
    c4.metric("Unenriched", coverage["unenriched"])
except Exception:
    logger.exception("Failed to load enrichment coverage")


# --- Auto-refresh ---
st.divider()

if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = is_active
auto_refresh = st.checkbox("Auto-refresh", key="auto_refresh")

refresh_interval = 5 if is_active else 30

col_refresh, _ = st.columns([1, 3])
with col_refresh:
    if st.button("Refresh Now"):
        st.cache_data.clear()
        st.rerun()

if auto_refresh:
    time.sleep(refresh_interval)
    st.cache_data.clear()
    st.rerun()


@st.fragment(run_every=30)
def _status_monitor() -> None:
    status = api_get("/api/pipeline/status", on_error="log")
    if status is not None and status["system_state"] in ("scraping", "enriching"):
        if not st.session_state.get("auto_refresh", False):
            st.session_state.auto_refresh = True
            st.rerun(scope="app")


_status_monitor()
