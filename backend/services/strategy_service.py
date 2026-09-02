import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
import pandas as pd
from collections import Counter
from backend.services.analytics_engine import (
    APP_TIMEZONE,
    HOOK_WORDS,
    TREND_TOPIC_KEYWORDS,
    COMMENT_TYPE_RULES,
    QUESTION_WORDS,
    words_from_text,
    title_keywords,
    title_hook_words,
    length_bucket,
    score_1_to_10,
    deterministic_title_analysis,
    classify_trend_topic,
    classify_content_category,
    dedupe_videos_list,
    dedupe_channels_list,
)

def compute_channel_stats(videos: List[Dict]) -> Dict[str, Any]:
    if not videos:
        return {
            "total_videos": 0,
            "total_views": 0,
            "avg_views": 0,
            "median_views": 0,
            "avg_views_per_day": 0,
            "shorts_count": 0,
            "long_count": 0,
            "avg_title_length": 0,
            "avg_duration_minutes": 0,
        }
    df = pd.DataFrame(videos)
    views = pd.to_numeric(df["views"], errors="coerce").fillna(0)
    vpds = pd.to_numeric(df["views_per_day"], errors="coerce").fillna(0)
    durations = pd.to_numeric(df.get("duration_minutes", 0), errors="coerce").fillna(0)
    title_lengths = pd.to_numeric(df.get("title_length", 0), errors="coerce").fillna(0)
    vtypes = df.get("video_type", pd.Series(dtype="string"))

    return {
        "total_videos": len(df),
        "total_views": int(views.sum()),
        "avg_views": round(float(views.mean()), 1),
        "median_views": int(views.median()),
        "avg_views_per_day": round(float(vpds.mean()), 1),
        "shorts_count": int((vtypes == "Shorts").sum()),
        "long_count": int((vtypes == "Long video").sum()),
        "avg_title_length": round(float(title_lengths.mean()), 1),
        "avg_duration_minutes": round(float(durations.mean()), 1),
    }

def compute_outliers(videos: List[Dict], channel_medians: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    if not videos:
        return []
    df = pd.DataFrame(videos)
    if "views_per_day" not in df.columns or "views" not in df.columns:
        return []

    df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
    df["views_per_day"] = pd.to_numeric(df["views_per_day"], errors="coerce").fillna(0.0)

    # Compute median per channel
    outliers = []
    for channel_name, group in df.groupby("channel"):
        ch_median_vpd = max(float(group["views_per_day"].median()), 1.0)
        ch_median_views = max(float(group["views"].median()), 1.0)

        for _, row in group.iterrows():
            vpd_multiplier = round(row["views_per_day"] / ch_median_vpd, 2)
            views_multiplier = round(row["views"] / ch_median_views, 2)
            is_outlier = vpd_multiplier >= 1.8 or views_multiplier >= 2.0
            tier = "Standard"
            if vpd_multiplier >= 10.0 or views_multiplier >= 10.0:
                tier = "10x Mega Viral"
            elif vpd_multiplier >= 5.0 or views_multiplier >= 5.0:
                tier = "5x Super Outlier"
            elif vpd_multiplier >= 2.0 or views_multiplier >= 2.0:
                tier = "2x Outlier"

            row_dict = row.to_dict()
            row_dict["outlier_multiplier"] = vpd_multiplier
            row_dict["views_multiplier"] = views_multiplier
            row_dict["is_outlier"] = is_outlier
            row_dict["outlier_tier"] = tier
            outliers.append(row_dict)

    return sorted(outliers, key=lambda x: x["outlier_multiplier"], reverse=True)

def compute_keyword_breakdown(videos: List[Dict], top_n: int = 25) -> List[Dict[str, Any]]:
    if not videos:
        return []
    df = pd.DataFrame(videos)
    records = []
    for _, row in df.iterrows():
        title = str(row.get("title", ""))
        for kw in title_keywords(title):
            records.append({
                "keyword": kw,
                "views": row.get("views", 0),
                "views_per_day": row.get("views_per_day", 0),
                "channel": row.get("channel", ""),
                "title": title,
                "url": row.get("url", ""),
            })
    if not records:
        return []
    kdf = pd.DataFrame(records)
    grouped = kdf.groupby("keyword").agg(
        uses=("keyword", "size"),
        channels=("channel", "nunique"),
        avg_views=("views", "mean"),
        avg_views_per_day=("views_per_day", "mean"),
        best_title=("title", lambda v: v.iloc[0]),
        best_url=("url", lambda v: v.iloc[0]),
    ).round(1).reset_index()
    return grouped.sort_values(["uses", "avg_views_per_day"], ascending=False).head(top_n).to_dict("records")

def compute_hook_breakdown(videos: List[Dict], top_n: int = 25) -> List[Dict[str, Any]]:
    if not videos:
        return []
    df = pd.DataFrame(videos)
    records = []
    for _, row in df.iterrows():
        title = str(row.get("title", ""))
        for hook in title_hook_words(title):
            records.append({
                "hook": hook,
                "views": row.get("views", 0),
                "views_per_day": row.get("views_per_day", 0),
                "channel": row.get("channel", ""),
                "title": title,
                "url": row.get("url", ""),
            })
    if not records:
        return []
    hdf = pd.DataFrame(records)
    grouped = hdf.groupby("hook").agg(
        uses=("hook", "size"),
        channels=("channel", "nunique"),
        avg_views=("views", "mean"),
        avg_views_per_day=("views_per_day", "mean"),
        best_title=("title", lambda v: v.iloc[0]),
        best_url=("url", lambda v: v.iloc[0]),
    ).round(1).reset_index()
    return grouped.sort_values(["avg_views_per_day", "uses"], ascending=False).head(top_n).to_dict("records")

def compute_monthly_distribution(videos: List[Dict]) -> List[Dict[str, Any]]:
    if not videos:
        return []
    df = pd.DataFrame(videos)
    if "published_at" not in df.columns:
        return []
    published = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    df = df[published.notna()].copy()
    if df.empty:
        return []
    df["published_at"] = published[published.notna()]
    df["month"] = df["published_at"].dt.tz_convert(APP_TIMEZONE).dt.strftime("%Y-%m")
    df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
    df["views_per_day"] = pd.to_numeric(df["views_per_day"], errors="coerce").fillna(0.0)

    rows = []
    for (month, channel), group in df.groupby(["month", "channel"], sort=True):
        top_v = group.sort_values("views", ascending=False).iloc[0]
        rows.append({
            "month": month,
            "channel": channel,
            "total_videos": int(len(group)),
            "total_views": int(group["views"].sum()),
            "avg_views": round(float(group["views"].mean()), 1),
            "avg_views_per_day": round(float(group["views_per_day"].mean()), 1),
            "shorts": int((group.get("video_type") == "Shorts").sum()),
            "long_videos": int((group.get("video_type") == "Long video").sum()),
            "top_video_title": top_v.get("title", ""),
            "top_video_views": int(top_v.get("views", 0)),
            "top_video_url": top_v.get("url", ""),
        })
    return sorted(rows, key=lambda x: (x["month"], x["total_views"]), reverse=True)

def compute_content_gap(own_channel_title: str, all_videos: List[Dict]) -> Dict[str, Any]:
    if not all_videos:
        return {"category_pivot": [], "opportunities": [], "summary": []}

    df = pd.DataFrame(all_videos)
    if "content_category" not in df.columns:
        df["content_category"] = df.apply(lambda r: classify_content_category(r.get("title", ""), r.get("youtube_tags", "")), axis=1)

    # Category breakdown by channel
    summary_rows = []
    for (channel, cat), group in df.groupby(["channel", "content_category"]):
        top_v = group.sort_values("views", ascending=False).iloc[0]
        summary_rows.append({
            "channel": channel,
            "category": cat,
            "videos": len(group),
            "total_views": int(group["views"].sum()),
            "avg_views": round(float(group["views"].mean()), 1),
            "best_video": top_v.get("title", ""),
            "best_video_views": int(top_v.get("views", 0)),
            "best_video_url": top_v.get("url", ""),
        })

    # Pivot for channels x categories
    pivot_dict: Dict[str, Dict[str, Any]] = {}
    for r in summary_rows:
        ch = r["channel"]
        if ch not in pivot_dict:
            pivot_dict[ch] = {"channel": ch, "Academic": 0, "Non-academic / Strategy": 0, "Other / mixed": 0, "total_videos": 0, "total_views": 0}
        pivot_dict[ch][r["category"]] = r["videos"]
        pivot_dict[ch]["total_videos"] += r["videos"]
        pivot_dict[ch]["total_views"] += r["total_views"]

    pivot_list = list(pivot_dict.values())

    # Topic level opportunities
    records = []
    for _, row in df.iterrows():
        for kw in title_keywords(row.get("title", ""))[:6]:
            records.append({
                "channel": row.get("channel", ""),
                "category": row.get("content_category", "Other"),
                "topic": kw,
                "views": row.get("views", 0),
                "title": row.get("title", ""),
                "url": row.get("url", ""),
            })

    opportunities = []
    if records:
        kdf = pd.DataFrame(records)
        own_topics = set(kdf[kdf["channel"] == own_channel_title]["topic"].tolist()) if own_channel_title else set()
        comp_df = kdf[kdf["channel"] != own_channel_title]
        comp_gap = comp_df[~comp_df["topic"].isin(own_topics)]

        if not comp_gap.empty:
            grouped = comp_gap.groupby(["category", "topic"]).agg(
                competitor_videos=("topic", "size"),
                competitor_views=("views", "sum"),
                competitor_channels=("channel", "nunique"),
                best_video=("title", lambda v: v.iloc[0]),
                best_url=("url", lambda v: v.iloc[0]),
            ).round(1).reset_index().sort_values(["competitor_views", "competitor_videos"], ascending=False)
            opportunities = grouped.head(20).to_dict("records")

    return {
        "category_pivot": pivot_list,
        "opportunities": opportunities,
        "summary": summary_rows,
    }

def generate_title_suggestions(video_description: str, benchmark_videos: List[Dict]) -> List[Dict[str, Any]]:
    desc_words = words_from_text(video_description)
    core_topic = " ".join(desc_words[:3]).title() if desc_words else "Strategy"
    current_year = datetime.now().year

    # Extract top performing hook patterns
    top_hooks = ["Complete Guide", "Avoid Mistakes", "Step-by-Step", "Secret Method", "Stop Doing This"]
    if benchmark_videos:
        bdf = pd.DataFrame(benchmark_videos)
        if "hook_keywords" in bdf.columns:
            all_hooks = [h.strip() for hs in bdf["hook_keywords"].dropna() for h in hs.split(",") if h.strip()]
            common_hooks = [h.title() for h, _ in Counter(all_hooks).most_common(5)]
            if common_hooks:
                top_hooks = common_hooks

    templates = [
        f"{core_topic} in {current_year}: The Complete Step-by-Step Blueprint",
        f"Stop Making These 3 {core_topic} Mistakes (What Actually Works)",
        f"How I Mastered {core_topic} in 30 Days: Full Breakdown",
        f"The Truth About {core_topic} Nobody Tells You",
        f"{core_topic} Masterclass: 5 Secrets for 10x Results",
    ]

    suggestions = []
    for i, title in enumerate(templates, 1):
        analysis = deterministic_title_analysis(title)
        suggestions.append({
            "rank": i,
            "title": title,
            "hook_type": analysis["hook_type"],
            "clarity_score": analysis["clarity_score"],
            "curiosity_score": analysis["curiosity_score"],
            "urgency_score": analysis["urgency_score"],
            "specificity_score": analysis["specificity_score"],
            "orientation": analysis["orientation"],
        })
    return suggestions

def classify_comment(comment_text: str) -> Tuple[str, str]:
    text = f" {str(comment_text).lower()} "
    words = set(words_from_text(text))
    matched_types = []

    if "?" in text or words & QUESTION_WORDS:
        matched_types.append("Question")

    for comment_type, phrases in COMMENT_TYPE_RULES:
        for phrase in phrases:
            p_clean = phrase.lower()
            if " " in p_clean:
                if p_clean in text:
                    matched_types.append(comment_type)
                    break
            elif p_clean in words:
                matched_types.append(comment_type)
                break

    if not matched_types:
        matched_types.append("General")

    priority = [
        "Purchase intent", "Content request", "Feature/course request", "Complaint",
        "Confusion", "Comparison", "Exam anxiety", "Question", "Praise", "General",
    ]
    primary_type = next((ct for ct in priority if ct in matched_types), "General")
    return primary_type, ", ".join(dict.fromkeys(matched_types))
