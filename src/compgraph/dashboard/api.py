"""Shared API helpers for dashboard pages to communicate with the FastAPI backend."""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

import requests
import streamlit as st

logger = logging.getLogger(__name__)

API_BASE = os.environ.get("COMPGRAPH_API_URL", "http://localhost:8000")


def api_get(path: str, *, on_error: Literal["st", "log"] = "st") -> dict[str, Any] | None:
    """GET from FastAPI, return JSON or None on error.

    Args:
        path: API path (e.g. "/api/pipeline/status").
        on_error: Error reporting mode — "st" for st.error(), "log" for logger.warning().
    """
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=5)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    except requests.RequestException as exc:
        if on_error == "st":
            st.error(f"API error: {exc}")
        else:
            logger.warning("API request failed: %s", exc)
        return None


def api_post(path: str) -> dict[str, Any] | None:
    """POST to FastAPI, return JSON or None on error."""
    try:
        resp = requests.post(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    except requests.RequestException as exc:
        st.error(f"API error: {exc}")
        return None
