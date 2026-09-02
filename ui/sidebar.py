from typing import Dict, Iterable, List, Tuple

import streamlit as st


NAV_SECTIONS: List[Tuple[str, List[str]]] = [
    ("Overview", ["Overview", "Your Channel"]),
    (
        "Research",
        [
            "Competitors",
            "Video Analyzer",
            "Outliers",
            "Trends",
            "Seasonal Intelligence",
            "Search Demand",
            "Audience Intelligence",
            "Content Gap",
        ],
    ),
    ("Create", ["Thumbnail Analyzer", "Title Analyzer", "Content Ideas"]),
    ("Track", ["Historical Data", "Alerts"]),
    ("Settings", ["Settings"]),
]


def render_sidebar_navigation() -> str:
    if "dashboard_page" not in st.session_state:
        st.session_state["dashboard_page"] = "Overview"

    st.markdown("### YouTube Growth")
    st.caption("Simple analytics workspace")
    page_options: List[str] = []
    page_labels: Dict[str, str] = {}
    for section, pages in NAV_SECTIONS:
        for page in pages:
            label = page if section == "Overview" else f"{section} - {page}"
            page_options.append(page)
            page_labels[page] = label

    current = st.session_state.get("dashboard_page", "Overview")
    if current not in page_options:
        current = "Overview"
    selected = st.selectbox(
        "Go to",
        page_options,
        index=page_options.index(current),
        format_func=lambda page: page_labels.get(page, page),
    )
    st.session_state["dashboard_page"] = selected

    return str(st.session_state["dashboard_page"])


def render_global_channel_search(channel_names: Iterable[str]) -> str:
    names = [name for name in dict.fromkeys(str(item) for item in channel_names if str(item).strip())]
    if not names:
        return ""
    current = st.session_state.get("global_channel_filter", "All channels")
    options = ["All channels"] + names
    if current not in options:
        current = "All channels"
    selected = st.selectbox(
        "Global channel search",
        options,
        index=options.index(current),
        key="global_channel_filter",
    )
    return "" if selected == "All channels" else selected
