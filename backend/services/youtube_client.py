import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse
from zoneinfo import ZoneInfo
import requests
import pandas as pd
from backend.services.analytics_engine import (
    YOUTUBE_API_BASE,
    APP_TIMEZONE,
    MAX_VIDEOS,
    sanitize_error_text,
    parse_duration,
    parse_published_at,
    length_bucket,
    video_length_bucket,
    video_type,
    bool_label,
    title_keywords,
    title_hook_words,
    starts_with_pattern,
    classify_content_category,
)

def youtube_network_error_message(error: Exception, api_key: str) -> str:
    details = sanitize_error_text(str(error), [api_key])
    lower_details = details.lower()
    if "10013" in lower_details or "access permissions" in lower_details:
        return (
            "YouTube API connection blocked by Windows firewall, antivirus, proxy, or network permissions. "
            f"Safe details: {details}"
        )
    return f"Could not connect to YouTube API: {details}"

def request_youtube(endpoint: str, api_key: str, **params) -> Dict:
    clean_params = {k: v for k, v in params.items() if v not in (None, "", [])}
    clean_params["key"] = api_key
    try:
        resp = requests.get(f"{YOUTUBE_API_BASE}/{endpoint}", params=clean_params, timeout=30)
    except requests.exceptions.RequestException as err:
        raise RuntimeError(youtube_network_error_message(err, api_key)) from err

    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            msg = resp.text
        msg = sanitize_error_text(msg, [api_key])
        raise RuntimeError(f"YouTube API error ({resp.status_code}): {msg}")

    return resp.json()

def parse_channel_hint(channel_url: str) -> Tuple[str, str]:
    raw = str(channel_url).strip()
    if not raw:
        raise ValueError("Paste a YouTube channel URL or handle first.")

    if raw.startswith("@"):
        return "handle", raw

    if re.fullmatch(r"UC[\w-]{22}", raw):
        return "id", raw

    parsed = urlparse(raw if re.match(r"^https?://", raw) else f"https://{raw}")
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]

    if parsed.query:
        query = parse_qs(parsed.query)
        if "channel_id" in query:
            return "id", query["channel_id"][0]

    if len(path_parts) >= 2 and path_parts[0].lower() == "channel":
        return "id", path_parts[1]

    if path_parts:
        first = path_parts[0]
        if first.startswith("@"):
            return "handle", first
        if first.lower() == "user" and len(path_parts) >= 2:
            return "username", path_parts[1]
        if first.lower() in {"c", "channel", "featured"} and len(path_parts) >= 2:
            return "search", path_parts[1]
        return "search", first

    return "search", raw

def resolve_channel(channel_url: str, api_key: str) -> Dict:
    hint_type, hint = parse_channel_hint(channel_url)

    if hint_type == "id":
        data = request_youtube("channels", api_key, part="snippet,statistics,contentDetails", id=hint)
    elif hint_type == "handle":
        data = request_youtube("channels", api_key, part="snippet,statistics,contentDetails", forHandle=hint)
    elif hint_type == "username":
        data = request_youtube("channels", api_key, part="snippet,statistics,contentDetails", forUsername=hint)
    else:
        search = request_youtube("search", api_key, part="snippet", q=hint, type="channel", maxResults=1)
        if not search.get("items"):
            raise ValueError(f"Could not find a channel for: {channel_url}")
        channel_id = search["items"][0]["snippet"]["channelId"]
        data = request_youtube("channels", api_key, part="snippet,statistics,contentDetails", id=channel_id)

    if not data.get("items"):
        raise ValueError(f"Could not resolve channel: {channel_url}")

    item = data["items"][0]
    uploads_playlist = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    return {
        "id": item["id"],
        "title": item["snippet"]["title"],
        "description": item["snippet"].get("description", ""),
        "published_at": item["snippet"].get("publishedAt"),
        "thumbnail": item["snippet"].get("thumbnails", {}).get("high", {}).get("url") or item["snippet"].get("thumbnails", {}).get("default", {}).get("url"),
        "subscriber_count": int(item.get("statistics", {}).get("subscriberCount", 0)),
        "view_count": int(item.get("statistics", {}).get("viewCount", 0)),
        "video_count": int(item.get("statistics", {}).get("videoCount", 0)),
        "uploads_playlist": uploads_playlist,
    }

def fetch_playlist_video_ids_by_date_range(
    playlist_id: str,
    api_key: str,
    start_date_text: Optional[str] = None,
    end_date_text: Optional[str] = None,
    max_videos: int = MAX_VIDEOS,
) -> List[str]:
    start_utc = None
    end_utc = None
    if start_date_text and end_date_text:
        try:
            start_date = datetime.fromisoformat(start_date_text).date()
            end_date = datetime.fromisoformat(end_date_text).date()
            start_local = datetime.combine(start_date, datetime.min.time(), tzinfo=APP_TIMEZONE)
            end_local = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=APP_TIMEZONE)
            start_utc = start_local.astimezone(timezone.utc)
            end_utc = end_local.astimezone(timezone.utc)
        except Exception:
            pass

    video_ids: List[str] = []
    page_token: Optional[str] = None

    while len(video_ids) < max_videos:
        data = request_youtube(
            "playlistItems",
            api_key,
            part="contentDetails,snippet",
            playlistId=playlist_id,
            maxResults=min(50, max_videos - len(video_ids)),
            pageToken=page_token,
        )

        stop_paging = False
        for item in data.get("items", []):
            content = item.get("contentDetails", {})
            snippet = item.get("snippet", {})
            video_id = content.get("videoId")
            published_text = content.get("videoPublishedAt") or snippet.get("publishedAt")
            if not video_id or not published_text:
                continue

            if start_utc and end_utc:
                published_at = parse_published_at(published_text)
                if published_at >= end_utc:
                    continue
                if published_at < start_utc:
                    stop_paging = True
                    continue

            if video_id not in video_ids:
                video_ids.append(video_id)
            if len(video_ids) >= max_videos:
                break

        if stop_paging or len(video_ids) >= max_videos:
            break
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return video_ids[:max_videos]

def fetch_video_details(video_ids: List[str], api_key: str) -> List[Dict[str, Any]]:
    clean_ids = [v.strip() for v in video_ids if v and isinstance(v, str) and v.strip()]
    if not clean_ids:
        return []
    rows = []
    now_utc = datetime.now(timezone.utc)

    for start in range(0, len(clean_ids), 50):
        batch = clean_ids[start : start + 50]
        data = request_youtube(
            "videos",
            api_key,
            part="snippet,statistics,contentDetails",
            id=",".join(batch),
        )

        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            details = item.get("contentDetails", {})
            title = snippet.get("title", "")
            published_at = parse_published_at(snippet.get("publishedAt", "2020-01-01T00:00:00Z"))
            age_days = max((now_utc - published_at).total_seconds() / 86400, 1)
            duration_seconds = parse_duration(details.get("duration", "PT0S"))
            views = int(stats.get("viewCount", 0))
            tags = snippet.get("tags", [])
            raw_tags_str = ", ".join(tags)

            vtype = video_type(duration_seconds)
            vpd = round(views / age_days, 2)
            content_cat = classify_content_category(title, raw_tags_str)

            rows.append(
                {
                    "video_id": item["id"],
                    "title": title,
                    "source_channel": snippet.get("channelTitle", ""),
                    "source_channel_id": snippet.get("channelId", ""),
                    "upload_date": published_at.date().isoformat(),
                    "published_at": published_at.isoformat(),
                    "views": views,
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "video_age_days": round(age_days, 1),
                    "duration_seconds": duration_seconds,
                    "duration_minutes": round(duration_seconds / 60, 2),
                    "title_length": len(title),
                    "word_count": len(re.findall(r"\w+", title)),
                    "has_number": bool_label(bool(re.search(r"\b\d+\b", title))),
                    "has_question": bool_label("?" in title),
                    "has_year": bool_label(bool(re.search(r"\b20\d{2}\b", title))),
                    "title_length_bucket": length_bucket(len(title)),
                    "video_length_bucket": video_length_bucket(duration_seconds),
                    "video_type": vtype,
                    "content_category": content_cat,
                    "views_per_day": vpd,
                    "keywords": ", ".join(title_keywords(title)),
                    "hook_keywords": ", ".join(title_hook_words(title)),
                    "opening_pattern": starts_with_pattern(title),
                    "youtube_tags": raw_tags_str,
                    "url": f"https://www.youtube.com/watch?v={item['id']}",
                    "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url") or snippet.get("thumbnails", {}).get("medium", {}).get("url") or snippet.get("thumbnails", {}).get("default", {}).get("url"),
                    "ctr": None,
                }
            )

    return rows

def fetch_channel_complete(
    channel_url: str,
    api_key: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_videos: int = MAX_VIDEOS,
) -> Tuple[Dict, List[Dict]]:
    channel = resolve_channel(channel_url, api_key)
    if not channel.get("uploads_playlist"):
        return channel, []
    video_ids = fetch_playlist_video_ids_by_date_range(
        channel["uploads_playlist"],
        api_key,
        start_date,
        end_date,
        max_videos,
    )
    videos = fetch_video_details(video_ids, api_key)
    for v in videos:
        v["channel"] = channel["title"]
        v["channel_id"] = channel["id"]
    return channel, videos

def fetch_video_comments_data(
    video_id: str,
    api_key: str,
    max_comments: int = 100,
    order: str = "time",
) -> List[Dict]:
    rows = []
    page_token: Optional[str] = None
    safe_limit = max(1, min(int(max_comments), 300))

    while len(rows) < safe_limit:
        data = request_youtube(
            "commentThreads",
            api_key,
            part="snippet",
            videoId=video_id,
            maxResults=min(100, safe_limit - len(rows)),
            order=order,
            textFormat="plainText",
            pageToken=page_token,
        )

        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            top_comment = snippet.get("topLevelComment", {})
            c_snippet = top_comment.get("snippet", {})
            published_at = c_snippet.get("publishedAt")
            updated_at = c_snippet.get("updatedAt")

            rows.append(
                {
                    "video_id": video_id,
                    "comment_id": top_comment.get("id", item.get("id", "")),
                    "author": c_snippet.get("authorDisplayName", ""),
                    "comment_text": c_snippet.get("textDisplay", ""),
                    "comment_likes": int(c_snippet.get("likeCount", 0)),
                    "comment_published_at": published_at,
                    "comment_updated_at": updated_at,
                    "reply_count": int(snippet.get("totalReplyCount", 0)),
                }
            )

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return rows
