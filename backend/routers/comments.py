from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
from backend.services.analytics_engine import (
    load_env_value,
    words_from_text,
    title_keywords,
)
from backend.services.youtube_client import fetch_video_comments_data
from backend.services.strategy_service import classify_comment
from glm_comment_report import generate_glm_comment_report

router = APIRouter(prefix="/api/comments", tags=["Audience Intelligence"])

class CommentAnalysisRequest(BaseModel):
    video_ids: List[str]
    max_comments_per_video: int = 50
    api_key: Optional[str] = None

class GLMReportRequest(BaseModel):
    comments_summary: List[Dict[str, Any]]
    sample_comments: List[Dict[str, Any]]
    channel_title: str
    glm_key: Optional[str] = None
    glm_model: Optional[str] = None
    glm_base_url: Optional[str] = None

@router.post("/analyze")
def analyze_video_comments(payload: CommentAnalysisRequest) -> Dict[str, Any]:
    api_key = payload.api_key or load_env_value("YOUTUBE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="YouTube API key required.")

    if not payload.video_ids:
        raise HTTPException(status_code=400, detail="At least one video ID is required.")

    all_comments = []
    for vid in payload.video_ids[:10]:
        try:
            comments = fetch_video_comments_data(
                vid,
                api_key,
                max_comments=payload.max_comments_per_video,
                order="relevance",
            )
            for c in comments:
                primary_type, matched_str = classify_comment(c["comment_text"])
                c["primary_type"] = primary_type
                c["matched_types"] = matched_str
                all_comments.append(c)
        except Exception as e:
            print(f"Warning: could not fetch comments for video {vid}: {e}")

    if not all_comments:
        return {
            "total_comments": 0,
            "category_summary": [],
            "comments": [],
            "content_ideas": [],
        }

    cdf = pd.DataFrame(all_comments)
    # Summary by type
    summary = cdf.groupby("primary_type").agg(
        total_comments=("comment_id", "count"),
        total_likes=("comment_likes", "sum"),
        avg_likes=("comment_likes", "mean"),
        total_replies=("reply_count", "sum"),
    ).round(1).reset_index().sort_values("total_comments", ascending=False).to_dict("records")

    # Generate Content Ideas from Audience Comments
    ideas = []
    useful_types = ["Content request", "Purchase intent", "Feature/course request", "Question", "Confusion", "Complaint", "Comparison", "Exam anxiety"]
    for cat in useful_types:
        cat_comments = cdf[cdf["primary_type"] == cat]
        if not cat_comments.empty:
            # Extract top repeated words
            all_text = " ".join(cat_comments["comment_text"].tolist())
            kws = [w for w in words_from_text(all_text) if len(w) > 3][:3]
            kw_label = " & ".join(kws).title() if kws else "Key Audience Need"
            sample = cat_comments.sort_values("comment_likes", ascending=False).iloc[0]
            ideas.append({
                "category": cat,
                "topic": kw_label,
                "demand_score": len(cat_comments) * 10 + int(cat_comments["comment_likes"].sum()),
                "comment_count": len(cat_comments),
                "sample_comment": sample["comment_text"][:200],
                "author": sample["author"],
                "suggested_title": f"The Ultimate {kw_label} Guide (What Everyone Asked For)",
            })

    ideas = sorted(ideas, key=lambda x: x["demand_score"], reverse=True)

    return {
        "total_comments": len(all_comments),
        "category_summary": summary,
        "comments": all_comments[:150],
        "content_ideas": ideas,
    }

@router.post("/glm-report")
def generate_glm_report(payload: GLMReportRequest) -> Dict[str, Any]:
    api_key = payload.glm_key or load_env_value("GLM_API_KEY") or load_env_value("ZAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="GLM API Key missing. Please provide it in Settings or set GLM_API_KEY in .env.",
        )

    glm_payload = {
        "comment_type_summary": payload.comments_summary,
        "high_signal_comment_samples": payload.sample_comments[:30],
        "channel_title": payload.channel_title,
    }

    report, error = generate_glm_comment_report(
        payload=glm_payload,
        api_key=api_key,
        base_url=payload.glm_base_url or "https://api.z.ai/api/paas/v4/",
        model=payload.glm_model or "glm-5.1",
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "status": "success",
        "report": report,
    }
