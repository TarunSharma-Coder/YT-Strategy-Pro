from typing import Any, Iterable

import pandas as pd
import streamlit as st

from ui.styles import escape_html, format_compact_number


def outlier_badge(value: Any) -> str:
    try:
        score = float(value or 0)
    except (TypeError, ValueError):
        score = 0
    if score >= 2:
        return '<span class="yt-pill hot">High outlier</span>'
    if score >= 1.25:
        return '<span class="yt-pill">Rising</span>'
    return '<span class="yt-pill">Normal</span>'


def render_video_card(row: pd.Series) -> None:
    thumbnail = str(row.get("thumbnail") or "").strip()
    title = escape_html(row.get("title", "Untitled video"))
    channel = escape_html(row.get("channel", ""))
    upload_date = escape_html(row.get("upload_date", ""))
    views = format_compact_number(row.get("views", 0))
    views_per_day = row.get("views_per_day", 0)
    url = str(row.get("url") or "").strip()
    outlier = row.get("outlier_score", 0)
    try:
        views_day_text = f"{float(views_per_day or 0):,.1f}/day"
    except (TypeError, ValueError):
        views_day_text = "0/day"

    with st.container(border=True):
        if thumbnail and thumbnail.lower() != "nan":
            st.image(thumbnail)
        st.markdown(
            f"""
            <div class="yt-video-card">
              <div class="yt-video-title">{title}</div>
              <div class="yt-meta">{channel} · {upload_date}</div>
              <div>
                <span class="yt-pill">{views} views</span>
                <span class="yt-pill">{views_day_text}</span>
                {outlier_badge(outlier)}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if url and url.lower() != "nan":
            st.link_button("Open video", url, icon=":material/open_in_new:")


def render_video_card_grid(videos: pd.DataFrame, limit: int = 6, columns: int = 3) -> None:
    if videos.empty:
        st.caption("No videos available.")
        return

    columns = max(1, min(columns, 4))
    rows: Iterable[pd.Series] = [
        row for _, row in videos.head(limit).iterrows()
    ]
    for start in range(0, len(rows), columns):
        cols = st.columns(columns)
        for col, row in zip(cols, rows[start : start + columns]):
            with col:
                render_video_card(row)
