"""Shared UI components for the eval tool."""

from __future__ import annotations

import json

import streamlit as st

from eval.ground_truth import REVIEWABLE_FIELDS


def render_pass1_diff(result_a: dict | None, result_b: dict | None) -> None:
    """Render two Pass 1 results side-by-side with diff highlighting."""
    if not result_a and not result_b:
        st.warning("Both results failed to parse.")
        return

    a = result_a or {}
    b = result_b or {}

    fields = REVIEWABLE_FIELDS

    col_a, col_b = st.columns(2)

    for field in fields:
        val_a = a.get(field)
        val_b = b.get(field)
        differs = val_a != val_b
        marker = " ⚠️" if differs else ""

        with col_a:
            st.text(f"{field}: {_fmt(val_a)}{marker}")
        with col_b:
            st.text(f"{field}: {_fmt(val_b)}{marker}")


def render_pass2_diff(result_a: dict | None, result_b: dict | None) -> None:
    """Render two Pass 2 results side-by-side."""
    a_entities = (result_a or {}).get("entities", [])
    b_entities = (result_b or {}).get("entities", [])

    col_a, col_b = st.columns(2)

    with col_a:
        if a_entities:
            for e in a_entities:
                st.text(f"  {e['entity_name']} ({e['entity_type']}) — {e['confidence']:.2f}")
        else:
            st.text("  (no entities)")

    with col_b:
        if b_entities:
            for e in b_entities:
                st.text(f"  {e['entity_name']} ({e['entity_type']}) — {e['confidence']:.2f}")
        else:
            st.text("  (no entities)")


def _fmt(val) -> str:
    """Format a value for display."""
    if val is None:
        return "null"
    if isinstance(val, list):
        return json.dumps(val) if val else "[]"
    return str(val)
