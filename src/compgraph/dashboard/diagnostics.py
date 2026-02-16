"""Dashboard diagnostics — health checks and sidebar component."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import streamlit as st
from sqlalchemy import text
from sqlalchemy.pool import QueuePool

from compgraph.dashboard.db import engine, get_session


@st.cache_data(ttl=30)
def collect_diagnostics() -> dict:
    """Collect dashboard health diagnostics (cached 30s to reduce DB load on reruns)."""
    start = time.perf_counter()
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    ping_ms = (time.perf_counter() - start) * 1000

    pool = engine.pool
    pool_stats: dict = {}
    if isinstance(pool, QueuePool):
        pool_stats = {
            "pool_size": pool.size(),
            "pool_checked_in": pool.checkedin(),
            "pool_checked_out": pool.checkedout(),
            "pool_overflow": pool.overflow(),
        }

    return {
        "db_connected": db_ok,
        "db_ping_ms": round(ping_ms, 1),
        **pool_stats,
        "last_refresh": datetime.now(UTC).strftime("%H:%M:%S"),
    }


def render_diagnostics_sidebar() -> None:
    """Render diagnostics expander in sidebar. Call from every page."""
    with st.sidebar.expander("Diagnostics", expanded=False):
        try:
            diag = collect_diagnostics()
            if diag["db_connected"]:
                st.success(f"DB connected ({diag['db_ping_ms']}ms)")
            else:
                st.error("DB connection failed")
            if "pool_size" in diag:
                st.caption(
                    f"Pool: {diag['pool_checked_out']}/{diag['pool_size']} active, "
                    f"{diag['pool_overflow']} overflow"
                )
            st.caption(f"Last check: {diag['last_refresh']}")
        except Exception as exc:
            st.error(f"Diagnostics unavailable: {exc}")
