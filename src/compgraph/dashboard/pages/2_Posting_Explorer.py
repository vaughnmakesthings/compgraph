"""Posting Explorer — search, filter, and inspect individual postings."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import pandas as pd
import streamlit as st

from compgraph.dashboard import configure_logging
from compgraph.dashboard.db import get_session
from compgraph.dashboard.diagnostics import render_diagnostics_sidebar
from compgraph.dashboard.queries import (
    freshness_color,
    get_companies,
    get_last_scrape_timestamps,
    get_posting_detail,
    get_role_archetypes,
    search_postings,
)

_FRESHNESS_ICONS = {
    "green": ":green_circle:",
    "yellow": ":yellow_circle:",
    "red": ":red_circle:",
    "gray": ":white_circle:",
}

configure_logging()
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Posting Explorer", layout="wide")
st.title("Posting Explorer")

render_diagnostics_sidebar()


@st.cache_data(ttl=60)
def _load_freshness() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_last_scrape_timestamps(session))


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


@st.cache_data(ttl=120)
def _load_companies() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_companies(session))


@st.cache_data(ttl=120)
def _load_archetypes() -> list[str]:
    with get_session() as session:
        return list(get_role_archetypes(session))


# --- Sidebar filters ---
try:
    companies = _load_companies()
except Exception:
    logger.exception("Failed to load companies")
    st.error("Failed to load companies. Check server logs for details.")
    companies = []

company_options = {"All": None} | {c["name"]: c["id"] for c in companies}
selected_company = st.sidebar.selectbox("Company", list(company_options.keys()))
company_id = company_options[selected_company]
if company_id is not None:
    company_id = uuid.UUID(company_id)

status_choice = st.sidebar.radio("Status", ["All", "Active", "Inactive"])
is_active = None
if status_choice == "Active":
    is_active = True
elif status_choice == "Inactive":
    is_active = False

try:
    archetypes = _load_archetypes()
except Exception:
    logger.exception("Failed to load archetypes")
    st.error("Failed to load archetypes. Check server logs for details.")
    archetypes = []

archetype_options = ["All", *archetypes]
selected_archetype = st.sidebar.selectbox("Role Archetype", archetype_options)
role_archetype = None if selected_archetype == "All" else selected_archetype

enrichment_choice = st.sidebar.radio("Enrichment", ["All", "Enriched", "Unenriched"])
has_enrichment = None
if enrichment_choice == "Enriched":
    has_enrichment = True
elif enrichment_choice == "Unenriched":
    has_enrichment = False

# Guard: role_archetype filter is meaningless when filtering for unenriched postings
if has_enrichment is False and role_archetype is not None:
    role_archetype = None
    st.sidebar.warning("Role archetype filter ignored — unenriched postings have no archetype.")


# --- Search ---
@st.cache_data(ttl=60, show_spinner="Searching postings...")
def _search(
    _company_id: str | None,
    _is_active: bool | None,
    _role_archetype: str | None,
    _has_enrichment: bool | None,
) -> list[dict[str, Any]]:
    cid = uuid.UUID(_company_id) if _company_id else None
    with get_session() as session:
        return list(
            search_postings(
                session,
                company_id=cid,
                is_active=_is_active,
                role_archetype=_role_archetype,
                has_enrichment=_has_enrichment,
            )
        )


try:
    results = _search(
        str(company_id) if company_id else None,
        is_active,
        role_archetype,
        has_enrichment,
    )
except Exception:
    logger.exception("Posting search failed")
    st.error("Search failed. Check server logs for details.")
    results = []

st.subheader(f"Results ({len(results)})")
if len(results) == 100:
    st.warning("Showing first 100 results. Refine filters to narrow down.")

if results:
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Detail expanders (single session to avoid N+1) ---
    st.subheader("Posting Details")
    if len(results) > 20:
        st.info("Showing details for the first 20 postings.")
    with get_session() as session:
        for row in results[:20]:
            title = row["title"] or "(no title)"
            label = f"{row['company']} — {title}"
            with st.expander(label):
                detail = get_posting_detail(session, uuid.UUID(row["posting_id"]))
                if detail:
                    col1, col2 = st.columns(2)
                    col1.write(f"**Status:** {'Active' if detail['is_active'] else 'Inactive'}")
                    first_seen = detail["first_seen_at"]
                    if hasattr(first_seen, "strftime"):
                        first_seen = first_seen.strftime("%Y-%m-%d %H:%M")
                    col1.write(f"**First seen:** {first_seen}")
                    last_seen = detail.get("last_seen_at")
                    if last_seen and hasattr(last_seen, "strftime"):
                        last_seen = last_seen.strftime("%Y-%m-%d %H:%M")
                    col1.write(f"**Last seen:** {last_seen or 'N/A'}")
                    col2.write(f"**Location:** {detail.get('location', 'N/A')}")
                    if "role_archetype" in detail:
                        col2.write(f"**Role:** {detail['role_archetype']}")
                        pay_str = ""
                        pay_min = detail.get("pay_min")
                        pay_max = detail.get("pay_max")
                        if pay_min is not None or pay_max is not None:
                            min_s = f"${pay_min:.2f}" if pay_min is not None else "?"
                            max_s = f"${pay_max:.2f}" if pay_max is not None else "?"
                            pay_str = f"{min_s} - {max_s}"
                            if detail.get("pay_frequency"):
                                pay_str += f" ({detail['pay_frequency'].capitalize()})"
                        col2.write(f"**Pay:** {pay_str or 'N/A'}")
                        col2.write(f"**Enrichment:** {detail.get('enrichment_version', 'N/A')}")

                    if detail.get("brand_mentions"):
                        st.write("**Brand Mentions:**")
                        for bm in detail["brand_mentions"]:
                            conf = ""
                            if bm.get("confidence") is not None:
                                conf = f" ({bm['confidence']:.0%})"
                            st.write(f"- {bm['entity_name']} [{bm['entity_type']}]{conf}")

                    if detail.get("full_text"):
                        st.write("**Full Text (truncated):**")
                        text = detail["full_text"]
                        if len(text) > 2000:
                            text = text[:2000].rsplit(" ", 1)[0] + "…"
                        st.text(text)
                else:
                    st.warning("Could not load details for this posting.")
else:
    st.info("No postings match the current filters.")

# --- Refresh ---
if st.sidebar.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
