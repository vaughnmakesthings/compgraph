"""CompGraph Dashboard — landing page and Streamlit entrypoint."""

import pandas as pd
import streamlit as st

from compgraph.dashboard.db import get_session
from compgraph.dashboard.queries import get_enrichment_coverage, get_per_company_counts

st.set_page_config(page_title="CompGraph Dashboard", layout="wide")

st.title("CompGraph Dashboard")
st.caption("Competitive intelligence — pipeline overview")


@st.cache_data(ttl=60)
def _load_coverage() -> dict:
    with get_session() as session:
        return get_enrichment_coverage(session)


@st.cache_data(ttl=60)
def _load_company_counts() -> list[dict]:
    with get_session() as session:
        return get_per_company_counts(session)


# --- Metrics row ---
try:
    coverage = _load_coverage()
except Exception as exc:
    st.error(f"Failed to load enrichment coverage: {exc}")
    coverage = {"total_active": "—", "enriched": "—", "with_brands": "—", "unenriched": "—"}

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Active", coverage["total_active"])
c2.metric("Enriched", coverage["enriched"])
c3.metric("With Brands", coverage["with_brands"])
c4.metric("Unenriched", coverage["unenriched"])

# --- Per-company bar chart ---
st.subheader("Active Postings by Company")
try:
    company_data = _load_company_counts()
except Exception as exc:
    st.error(f"Failed to load company counts: {exc}")
    company_data = []

if company_data:
    df = pd.DataFrame(company_data).set_index("company")
    st.bar_chart(df["count"])
else:
    st.info("No posting data yet. Run the scraper to populate.")

# --- Refresh ---
if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
