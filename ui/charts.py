from typing import Dict

import altair as alt
import pandas as pd
import streamlit as st


TIMEFRAME_DAYS: Dict[str, int] = {
    "7D": 7,
    "28D": 28,
    "90D": 90,
    "1Y": 365,
    "2Y": 730,
}


def filter_videos_by_timeframe(videos: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if videos.empty or "published_at" not in videos.columns:
        return videos.copy()
    days = TIMEFRAME_DAYS.get(timeframe, 28)
    frame = videos.copy()
    published = pd.to_datetime(frame["published_at"], utc=True, errors="coerce")
    if published.dropna().empty:
        return frame
    end = published.max()
    start = end - pd.Timedelta(days=days)
    return frame[published >= start].copy()


def render_growth_chart(videos: pd.DataFrame) -> None:
    if videos.empty or "published_at" not in videos.columns:
        st.caption("No growth data available.")
        return

    chart_df = videos.copy()
    chart_df["date"] = pd.to_datetime(chart_df["published_at"], utc=True, errors="coerce").dt.date
    chart_df["views"] = pd.to_numeric(chart_df.get("views", 0), errors="coerce").fillna(0)
    chart_df = chart_df.dropna(subset=["date"])
    if chart_df.empty:
        st.caption("No growth data available.")
        return

    chart_df = (
        chart_df.groupby("date", as_index=False)
        .agg(daily_views=("views", "sum"), videos_uploaded=("views", "size"))
        .sort_values("date")
    )
    chart_df["cumulative_views"] = chart_df["daily_views"].cumsum()

    chart = (
        alt.Chart(chart_df)
        .mark_area(line=True, opacity=0.28, color="#FF3D57")
        .encode(
            x=alt.X("date:T", title="Upload date"),
            y=alt.Y("cumulative_views:Q", title="Cumulative views from uploads"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("daily_views:Q", title="Daily upload views", format=","),
                alt.Tooltip("cumulative_views:Q", title="Cumulative views", format=","),
                alt.Tooltip("videos_uploaded:Q", title="Videos uploaded"),
            ],
        )
        .interactive()
        .properties(height=390)
    )
    st.altair_chart(chart)


def render_competitor_activity_chart(videos: pd.DataFrame) -> None:
    if videos.empty or "channel" not in videos.columns:
        st.caption("No competitor activity available.")
        return
    frame = videos.copy()
    frame["views"] = pd.to_numeric(frame.get("views", 0), errors="coerce").fillna(0)
    summary = (
        frame.groupby("channel", as_index=False)
        .agg(videos=("video_id", "nunique"), total_views=("views", "sum"))
        .sort_values("total_views", ascending=False)
        .head(12)
    )
    chart = (
        alt.Chart(summary)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#22D3EE")
        .encode(
            x=alt.X("channel:N", title="Channel", sort="-y"),
            y=alt.Y("total_views:Q", title="Total views"),
            tooltip=[
                alt.Tooltip("channel:N", title="Channel"),
                alt.Tooltip("videos:Q", title="Videos"),
                alt.Tooltip("total_views:Q", title="Total views", format=","),
            ],
        )
        .properties(height=300)
    )
    st.altair_chart(chart)


def render_month_topic_heatmap(month_topic: pd.DataFrame) -> None:
    if month_topic.empty:
        st.caption("No seasonal data available.")
        return
    chart = (
        alt.Chart(month_topic)
        .mark_rect(cornerRadius=2)
        .encode(
            x=alt.X("month_name:N", title="Month", sort=list(month_topic["month_name"].drop_duplicates())),
            y=alt.Y("topic:N", title="Topic", sort="-color"),
            color=alt.Color("demand_score:Q", title="Demand", scale=alt.Scale(scheme="reds")),
            tooltip=[
                alt.Tooltip("month_name:N", title="Month"),
                alt.Tooltip("topic:N", title="Topic"),
                alt.Tooltip("videos:Q", title="Videos"),
                alt.Tooltip("total_views:Q", title="Views", format=","),
                alt.Tooltip("demand_score:Q", title="Demand score", format=".1f"),
            ],
        )
        .properties(height=420)
    )
    st.altair_chart(chart)
