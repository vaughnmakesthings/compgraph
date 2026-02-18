from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

import requests
import streamlit as st

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Scheduler", layout="wide")
st.title("Scheduler")
st.caption(f"Last refreshed: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")

API_BASE = os.environ.get("COMPGRAPH_API_URL", "http://localhost:8000")


def _api_get(path: str) -> dict[str, Any] | None:
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
    try:
        resp = requests.post(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    except requests.RequestException as exc:
        st.error(f"API error: {exc}")
        return None


# --- Fetch scheduler status ---
status = _api_get("/api/scheduler/status")

if status is None:
    st.error("Could not connect to the API server.")
    st.stop()

if not status["enabled"]:
    st.warning("Scheduler is disabled. Set SCHEDULER_ENABLED=true to enable.")
    st.stop()

# --- Missed run warning ---
if status["missed_run"]:
    st.error(
        "MISSED RUN: No pipeline run completed in the last 56 hours. "
        "Check scheduler health or trigger manually."
    )

# --- Schedule display ---
st.subheader("Pipeline Schedules")

for schedule in status["schedules"]:
    sid = schedule["schedule_id"]
    paused = schedule["paused"]
    next_fire = schedule["next_fire_time"]
    last_fire = schedule["last_fire_time"]

    if paused:
        color = "orange"
        state_label = "PAUSED"
    elif status["missed_run"]:
        color = "red"
        state_label = "MISSED"
    else:
        color = "green"
        state_label = "SCHEDULED"

    st.markdown(f"**{sid}** &mdash; :{color}[{state_label}]")

    c1, c2 = st.columns(2)
    c1.metric("Next Run", next_fire[:19] if next_fire else "N/A")
    c2.metric("Last Run", last_fire[:19] if last_fire else "Never")

    # --- Controls ---
    col_trigger, col_pause, col_resume = st.columns(3)

    with col_trigger:
        if st.button("Trigger Now", key=f"trigger_{sid}", type="primary"):
            result = _api_post(f"/api/scheduler/jobs/{sid}/trigger")
            if result:
                st.success(f"Pipeline triggered: job {result['job_id'][:8]}...")
                time.sleep(0.5)
                st.rerun()

    with col_pause:
        if st.button("Pause", key=f"pause_{sid}", disabled=paused):
            result = _api_post(f"/api/scheduler/jobs/{sid}/pause")
            if result:
                st.info(result["message"])
                time.sleep(0.5)
                st.rerun()

    with col_resume:
        if st.button("Resume", key=f"resume_{sid}", disabled=not paused):
            result = _api_post(f"/api/scheduler/jobs/{sid}/resume")
            if result:
                st.info(result["message"])
                time.sleep(0.5)
                st.rerun()

st.divider()

# --- Last pipeline result ---
st.subheader("Last Pipeline Run")
last_finished = status["last_pipeline_finished_at"]
last_success = status["last_pipeline_success"]

if last_finished:
    color = "green" if last_success else "red"
    label = "SUCCESS" if last_success else "FAILED"
    st.markdown(f"**Result:** :{color}[{label}]")
    finished_str = last_finished[:16] if isinstance(last_finished, str) else last_finished
    st.text(f"Completed at: {finished_str}")
else:
    st.info("No pipeline runs recorded yet.")

st.divider()

col_refresh, _ = st.columns([1, 3])
with col_refresh:
    if st.button("Refresh"):
        st.rerun()
