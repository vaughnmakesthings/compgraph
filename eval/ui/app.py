"""CompGraph LLM Eval — Streamlit entry point."""

import sys
from pathlib import Path

# Ensure project root is on sys.path so pages can import eval.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="CompGraph LLM Eval",
    page_icon="🔬",
    layout="wide",
)

st.title("CompGraph LLM Eval")
st.markdown(
    "Test prompt/model combinations against the enrichment pipeline. Navigate using the sidebar."
)
