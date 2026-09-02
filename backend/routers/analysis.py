import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.analytics_engine import (
    load_env_value,
    dedupe_channels_list,
    dedupe_videos_list,
    deterministic_title_analysis,
)
from backend.services.youtube_client import (
    resolve_channel,
    fetch_channel_complete,
    fetch_video_details,
)
from backend.services.strategy_service import (
    compute_channel_stats,
    compute_outliers,
    compute_keyword_breakdown,
    compute_hook_breakdown,
    compute_monthly_distribution,
    compute_content_gap,
    generate_title_suggestions,
)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

class AnalyzeRequest(BaseModel):
    own_channel_url: str
    competitor_urls: List[str] = []
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_videos_per_channel: int = 50
    video_description: Optional[str] = ""
    api_key: Optional[str] = None

@router.post("/run")
def run_full_analysis(payload: AnalyzeRequest) -> Dict[str, Any]:
    api_key = payload.api_key or load_env_value("YOUTUBE_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="YouTube API Key is required. Please provide it in Settings or set YOUTUBE_API_KEY in .env.",
        )

    own_url = payload.own_channel_url.strip()
    if not own_url:
        raise HTTPException(status_code=400, detail="Own channel URL is required.")

    # 1. Fetch own channel
    try:
        own_channel, own_videos = fetch_channel_complete(
            own_url,
            api_key,
            payload.start_date,
            payload.end_date,
            payload.max_videos_per_channel,
        )
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Failed to fetch own channel: {str(err)}")

    # 2. Fetch competitor channels
    competitor_channels = []
    competitor_videos = []
    for c_url in payload.competitor_urls[:5]:
        c_clean = c_url.strip()
        if not c_clean:
            continue
        try:
            c_chan, c_vids = fetch_channel_complete(
                c_clean,
                api_key,
                payload.start_date,
                payload.end_date,
                payload.max_videos_per_channel,
            )
            competitor_channels.append(c_chan)
            competitor_videos.extend(c_vids)
        except Exception as e:
            # Non-blocking, continue with remaining competitors
            print(f"Warning: failed to load competitor {c_clean}: {e}")

    competitor_channels = dedupe_channels_list(competitor_channels)
    competitor_videos = dedupe_videos_list(competitor_videos)
    all_videos = dedupe_videos_list(own_videos + competitor_videos)

    # 3. Compute statistics & analytics
    own_stats = compute_channel_stats(own_videos)
    competitors_stats = [
        {
            "channel": c["title"],
            "id": c["id"],
            "thumbnail": c.get("thumbnail"),
            "subscriber_count": c.get("subscriber_count", 0),
            "stats": compute_channel_stats([v for v in competitor_videos if v.get("channel") == c["title"]]),
        }
        for c in competitor_channels
    ]

    outliers = compute_outliers(all_videos)
    top_keywords = compute_keyword_breakdown(all_videos, top_n=30)
    top_hooks = compute_hook_breakdown(all_videos, top_n=30)
    monthly_trend = compute_monthly_distribution(all_videos)
    content_gap = compute_content_gap(own_channel.get("title", ""), all_videos)
    title_suggestions = generate_title_suggestions(payload.video_description or "", all_videos)

    return {
        "status": "success",
        "own_channel": own_channel,
        "own_videos": own_videos,
        "own_stats": own_stats,
        "competitor_channels": competitor_channels,
        "competitor_videos": competitor_videos,
        "competitors_stats": competitors_stats,
        "all_videos": all_videos,
        "outliers": outliers,
        "top_keywords": top_keywords,
        "top_hooks": top_hooks,
        "monthly_trend": monthly_trend,
        "content_gap": content_gap,
        "title_suggestions": title_suggestions,
        "summary": {
            "total_channels": 1 + len(competitor_channels),
            "total_videos_analyzed": len(all_videos),
            "total_outliers_found": len([o for o in outliers if o.get("is_outlier")]),
        },
    }

@router.get("/video-details")
def get_video_details(video_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    key = api_key or load_env_value("YOUTUBE_API_KEY")
    if not key:
        raise HTTPException(status_code=400, detail="YouTube API key required. Please configure it in Settings.")
    
    vid_clean = (video_id or "").strip()
    if not vid_clean:
        raise HTTPException(status_code=400, detail="Video ID or YouTube URL is required.")

    try:
        vids = fetch_video_details([vid_clean], key)
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Failed to fetch video details: {str(err)}")

    if not vids:
        raise HTTPException(status_code=404, detail=f"Video '{vid_clean}' not found.")
    
    video = vids[0]
    title_eval = deterministic_title_analysis(video.get("title", ""))
    return {
        "video": video,
        "title_analysis": title_eval,
    }

