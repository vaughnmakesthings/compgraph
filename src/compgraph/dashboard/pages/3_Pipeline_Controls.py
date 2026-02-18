"""Pipeline Controls — start, pause, stop, and monitor scrape pipeline runs."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import pandas as pd
import requests
import streamlit as st

from compgraph.dashboard.db import get_session
from compgraph.dashboard.queries import get_latest_pipeline_status

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Pipeline Controls", layout="wide")
st.title("Pipeline Controls")

API_BASE = os.environ.get("COMPGRAPH_API_URL", "http://localhost:8000")

# --- Status color mapping ---
STATUS_COLORS: dict[str, str] = {
    "pending": "gray",
    "running": "blue",
    "paused": "orange",
    "stopping": "orange",
    "success": "green",
    "partial": "orange",
    "failed": "red",
    "cancelled": "red",
}

COMPANY_STATE_ICONS: dict[str, str] = {
    "pending": "\u23f3",
    "running": "\U0001f3c3",
    "completed": "\u2705",
    "failed": "\u274c",
    "skipped": "\u23ed\ufe0f",
}


def _api_get(path: str) -> dict[str, Any] | None:
    """GET from FastAPI, return JSON or None on error."""
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=5)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    except requests.RequestException as exc:
        st.error(f"API error: {exc}")
        return None


def _api_post(path: str) -> dict[str, Any] | None:
    """POST to FastAPI, return JSON or None on error."""
    try:
        resp = requests.post(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    except requests.RequestException as exc:
        st.error(f"API error: {exc}")
        return None


# --- Fetch current status from DB (works for both API and scheduler triggers) ---
with get_session() as _db_session:
    status_data = get_latest_pipeline_status(_db_session)

if status_data is None:
    st.info("No pipeline runs found. Start a scrape to begin.")
    pipeline_status: str | None = None
else:
    pipeline_status = str(status_data["status"])


# --- Status display ---
if status_data is not None and pipeline_status is not None:
    st.subheader("Current Run")

    color = STATUS_COLORS.get(pipeline_status, "gray")
    st.markdown(f"**Status:** :{color}[{pipeline_status.upper()}]")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Postings Found", status_data["total_postings_found"])
    m2.metric("Snapshots", status_data["total_snapshots_created"])
    m3.metric("Succeeded", status_data["companies_succeeded"])
    m4.metric("Errors", status_data["total_errors"])

    # Per-company progress
    company_states: dict[str, str] = status_data.get("company_states", {})
    if company_states:
        st.subheader("Per-Company Progress")
        rows = []
        for slug, state in company_states.items():
            icon = COMPANY_STATE_ICONS.get(state, "")
            result = status_data["company_results"].get(slug)
            postings = result["postings_found"] if result else 0
            snapshots = result["snapshots_created"] if result else 0
            rows.append(
                {
                    "Company": slug,
                    "State": f"{icon} {state}",
                    "Postings": postings,
                    "Snapshots": snapshots,
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()

# --- Control buttons ---
st.subheader("Controls")

is_active = pipeline_status in ("running", "paused", "stopping")
is_terminal = pipeline_status in ("success", "partial", "failed", "cancelled", None)

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("Start Scrape", disabled=not is_terminal, type="primary"):
        result = _api_post("/api/scrape/trigger")
        if result:
            st.success(f"Started run {result['run_id'][:8]}...")
            time.sleep(0.5)
            st.rerun()

with col2:
    if pipeline_status == "running":
        if st.button("Pause"):
            result = _api_post("/api/scrape/pause")
            if result:
                st.info(result["message"])
                time.sleep(0.5)
                st.rerun()
    elif pipeline_status == "paused":
        if st.button("Resume"):
            result = _api_post("/api/scrape/resume")
            if result:
                st.info(result["message"])
                time.sleep(0.5)
                st.rerun()

with col3:
    if st.button("Stop", disabled=pipeline_status not in ("running", "paused")):
        result = _api_post("/api/scrape/stop")
        if result:
            st.warning(result["message"])
            time.sleep(0.5)
            st.rerun()

with col4:
    if st.button(
        "Force Stop",
        disabled=pipeline_status not in ("running", "paused", "stopping"),
    ):
        result = _api_post("/api/scrape/force-stop")
        if result:
            st.error(result["message"])
            time.sleep(0.5)
            st.rerun()

st.divider()

# --- Auto-refresh ---
auto_refresh = st.checkbox("Auto-refresh (3s)", value=is_active)

col_refresh, _ = st.columns([1, 3])
with col_refresh:
    if st.button("Refresh Now"):
        st.rerun()

if auto_refresh and is_active:
    time.sleep(3)
    st.rerun()
