import html
from typing import Any

import streamlit as st


COLORS = {
    "background": "#F7F8FB",
    "surface": "#FFFFFF",
    "surface_2": "#F1F5F9",
    "border": "#E2E8F0",
    "text": "#0F172A",
    "muted": "#64748B",
    "accent": "#E11D48",
    "accent_2": "#2563EB",
    "warning": "#D97706",
    "success": "#059669",
}


def apply_dashboard_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --yt-bg: #F7F8FB;
            --yt-surface: #FFFFFF;
            --yt-surface-2: #F1F5F9;
            --yt-border: #E2E8F0;
            --yt-text: #0F172A;
            --yt-muted: #64748B;
            --yt-accent: #E11D48;
            --yt-blue: #2563EB;
            --yt-green: #059669;
            --yt-warning: #D97706;
        }

        .stApp {
            background: var(--yt-bg);
            color: var(--yt-text);
        }

        [data-testid="stSidebar"] {
            background: #FFFFFF;
            border-right: 1px solid var(--yt-border);
        }

        [data-testid="stSidebar"] * {
            color: var(--yt-text);
        }

        [data-testid="stSidebar"] .stTextInput input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] .stDateInput input {
            background: #FFFFFF;
            border: 1px solid var(--yt-border);
            color: var(--yt-text);
        }

        h1, h2, h3 {
            letter-spacing: 0;
            color: var(--yt-text);
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 3rem;
            max-width: 1380px;
        }

        [data-testid="stMetric"],
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border-color: var(--yt-border);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }

        [data-testid="stMetricLabel"] p,
        .stCaptionContainer,
        .stMarkdown p {
            color: var(--yt-muted);
        }

        .yt-kicker {
            color: var(--yt-muted);
            font-size: 0.78rem;
            font-weight: 650;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .yt-page-title {
            font-size: 2rem;
            line-height: 1.12;
            margin: 0.2rem 0 0.4rem;
            color: var(--yt-text);
        }

        .yt-card {
            background: #FFFFFF;
            border: 1px solid var(--yt-border);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }

        .yt-soft-card {
            background: #FFFFFF;
            border: 1px solid var(--yt-border);
            border-radius: 8px;
            padding: 0.85rem;
        }

        .yt-video-card {
            min-height: 100%;
        }

        .yt-video-card img {
            width: 100%;
            aspect-ratio: 16 / 9;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid var(--yt-border);
        }

        .yt-video-title {
            color: var(--yt-text);
            font-size: 0.96rem;
            line-height: 1.25;
            font-weight: 700;
            margin: 0.65rem 0 0.35rem;
        }

        .yt-meta {
            color: var(--yt-muted);
            font-size: 0.78rem;
        }

        .yt-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            border: 1px solid var(--yt-border);
            padding: 0.18rem 0.52rem;
            margin: 0.35rem 0.25rem 0 0;
            color: var(--yt-text);
            background: #F8FAFC;
            font-size: 0.76rem;
            font-weight: 650;
        }

        .yt-pill.hot {
            border-color: #FDA4AF;
            background: #FFF1F2;
            color: #9F1239;
        }

        .yt-section-title {
            font-size: 1.05rem;
            font-weight: 750;
            color: var(--yt-text);
            margin: 0.2rem 0 0.7rem;
        }

        .yt-nav-caption {
            color: var(--yt-muted);
            font-size: 0.78rem;
            margin-bottom: 0.4rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def escape_html(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def format_compact_number(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0
    if abs(number) >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}B"
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if abs(number) >= 1_000:
        return f"{number / 1_000:.1f}K"
    return f"{int(number):,}"
