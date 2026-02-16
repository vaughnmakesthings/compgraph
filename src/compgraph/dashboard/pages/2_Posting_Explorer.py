"""Posting Explorer — search, filter, and inspect individual postings."""

import uuid

import pandas as pd
import streamlit as st

from compgraph.dashboard.db import get_session
from compgraph.dashboard.queries import (
    get_companies,
    get_posting_detail,
    get_role_archetypes,
    search_postings,
)

st.set_page_config(page_title="Posting Explorer", layout="wide")
st.title("Posting Explorer")


@st.cache_data(ttl=120)
def _load_companies() -> list[dict]:
    with get_session() as session:
        return get_companies(session)


@st.cache_data(ttl=120)
def _load_archetypes() -> list[str]:
    with get_session() as session:
        return get_role_archetypes(session)


# --- Sidebar filters ---
companies = _load_companies()
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

archetypes = _load_archetypes()
archetype_options = ["All", *archetypes]
selected_archetype = st.sidebar.selectbox("Role Archetype", archetype_options)
role_archetype = None if selected_archetype == "All" else selected_archetype

enrichment_choice = st.sidebar.radio("Enrichment", ["All", "Enriched", "Unenriched"])
has_enrichment = None
if enrichment_choice == "Enriched":
    has_enrichment = True
elif enrichment_choice == "Unenriched":
    has_enrichment = False


# --- Search ---
@st.cache_data(ttl=60)
def _search(
    _company_id: str | None,
    _is_active: bool | None,
    _role_archetype: str | None,
    _has_enrichment: bool | None,
) -> list[dict]:
    cid = uuid.UUID(_company_id) if _company_id else None
    with get_session() as session:
        return search_postings(
            session,
            company_id=cid,
            is_active=_is_active,
            role_archetype=_role_archetype,
            has_enrichment=_has_enrichment,
        )


results = _search(
    str(company_id) if company_id else None,
    is_active,
    role_archetype,
    has_enrichment,
)

st.subheader(f"Results ({len(results)})")

if results:
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Detail expanders ---
    st.subheader("Posting Details")
    for row in results[:20]:
        title = row["title"] or "(no title)"
        label = f"{row['company']} — {title}"
        with st.expander(label):
            with get_session() as session:
                detail = get_posting_detail(session, uuid.UUID(row["posting_id"]))
            if detail:
                col1, col2 = st.columns(2)
                col1.write(f"**Status:** {'Active' if detail['is_active'] else 'Inactive'}")
                col1.write(f"**First seen:** {detail['first_seen_at']}")
                col1.write(f"**Last seen:** {detail.get('last_seen_at', 'N/A')}")
                col2.write(f"**Location:** {detail.get('location', 'N/A')}")
                if "role_archetype" in detail:
                    col2.write(f"**Role:** {detail['role_archetype']}")
                    pay_str = ""
                    if detail.get("pay_min") or detail.get("pay_max"):
                        pay_str = f"${detail.get('pay_min', '?')} - ${detail.get('pay_max', '?')}"
                        if detail.get("pay_frequency"):
                            pay_str += f" ({detail['pay_frequency']})"
                    col2.write(f"**Pay:** {pay_str or 'N/A'}")
                    col2.write(f"**Enrichment:** {detail.get('enrichment_version', 'N/A')}")

                if detail.get("brand_mentions"):
                    st.write("**Brand Mentions:**")
                    for bm in detail["brand_mentions"]:
                        conf = f" ({bm['confidence']:.0%})" if bm.get("confidence") else ""
                        st.write(f"- {bm['entity_name']} [{bm['entity_type']}]{conf}")

                if detail.get("full_text"):
                    st.write("**Full Text (truncated):**")
                    st.text(detail["full_text"][:2000])
else:
    st.info("No postings match the current filters.")

# --- Refresh ---
if st.sidebar.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
