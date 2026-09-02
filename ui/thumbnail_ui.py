from typing import Dict

import streamlit as st


def render_thumbnail_score_panel(result: Dict) -> None:
    analysis = result.get("analysis", {})
    if not result.get("ok"):
        st.metric("Packaging score", "Not ready", border=True)
        st.caption("Upload a thumbnail and run analysis to see score details.")
        return

    score = result.get("packaging_score", 0)
    st.metric("Packaging score", f"{score}/100", border=True)
    score_rows = [
        ("Readability", analysis.get("readability_score", 0)),
        ("Visual hierarchy", analysis.get("visual_hierarchy_score", 0)),
        ("Curiosity", analysis.get("curiosity_score", 0)),
        ("Clutter", analysis.get("clutter_score", 0)),
        ("Alignment", analysis.get("title_thumbnail_alignment_score", 0)),
        ("Complementarity", analysis.get("complementarity_score", 0)),
        ("Mobile readability", analysis.get("mobile_readability_score", 0)),
    ]

    for label, value in score_rows:
        st.metric(label, f"{value}/10", border=True)
