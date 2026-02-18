"""Brand Intel — client brands and retailers per competitor."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import streamlit as st

from compgraph.dashboard import configure_logging
from compgraph.dashboard.db import get_session
from compgraph.dashboard.diagnostics import render_diagnostics_sidebar
from compgraph.dashboard.queries import get_brand_intel, get_companies, get_retailer_intel

configure_logging()
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Brand Intel", layout="wide")
st.title("Brand Intel")
st.caption(f"Last refreshed: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")

render_diagnostics_sidebar()


@st.cache_data(ttl=60, show_spinner="Loading brands...")
def _load_brands(company_id_str: str) -> list[dict[str, Any]]:
    cid = uuid.UUID(company_id_str)
    with get_session() as session:
        return list(get_brand_intel(session, cid))


@st.cache_data(ttl=60, show_spinner="Loading retailers...")
def _load_retailers(company_id_str: str) -> list[dict[str, Any]]:
    cid = uuid.UUID(company_id_str)
    with get_session() as session:
        return list(get_retailer_intel(session, cid))


@st.cache_data(ttl=120)
def _load_companies() -> list[dict[str, Any]]:
    with get_session() as session:
        return list(get_companies(session))


# --- Load companies ---
try:
    companies = _load_companies()
except Exception:
    logger.exception("Failed to load companies")
    st.error("Failed to load companies. Check server logs for details.")
    companies = []

if not companies:
    st.info("No companies found. Run the scraper first.")
    st.stop()

# --- Tabs per company ---
tab_labels = [c["name"] for c in companies]
tabs = st.tabs(tab_labels)

for tab, company in zip(tabs, companies, strict=True):
    with tab:
        company_id_str = company["id"]

        # Client Brands
        st.subheader("Client Brands")
        try:
            brands = _load_brands(company_id_str)
            if brands:
                df_brands = pd.DataFrame(brands)
                df_brands.columns = ["Brand", "Active Postings", "First Seen"]
                st.dataframe(df_brands, use_container_width=True, hide_index=True)
            else:
                st.info("No client brand mentions found for this company.")
        except Exception:
            logger.exception("Failed to load brand intel for %s", company["name"])
            st.error("Failed to load brand data. Check server logs for details.")

        # Retailers
        st.subheader("Retailers")
        try:
            retailers = _load_retailers(company_id_str)
            if retailers:
                df_retailers = pd.DataFrame(retailers)
                df_retailers.columns = ["Retailer", "Active Postings", "First Seen"]
                st.dataframe(df_retailers, use_container_width=True, hide_index=True)
            else:
                st.info("No retailer mentions found for this company.")
        except Exception:
            logger.exception("Failed to load retailer intel for %s", company["name"])
            st.error("Failed to load retailer data. Check server logs for details.")

# --- Refresh ---
if st.sidebar.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
