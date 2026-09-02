import base64
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import requests
import streamlit as st

from thumbnail_analyzer import (
    analyze_thumbnail_package,
    calculate_packaging_score as calculate_uploaded_thumbnail_packaging_score,
    validate_thumbnail_image,
)
from glm_comment_report import (
    DEFAULT_GLM_BASE_URL,
    DEFAULT_GLM_MODEL,
    generate_glm_comment_report,
)
from ui.charts import (
    filter_videos_by_timeframe,
    render_competitor_activity_chart,
    render_growth_chart,
    render_month_topic_heatmap,
)
from ui.metric_cards import render_metric_cards
from ui.sidebar import render_global_channel_search, render_sidebar_navigation
from ui.styles import apply_dashboard_theme, format_compact_number
from ui.thumbnail_ui import render_thumbnail_score_panel
from ui.video_cards import render_video_card_grid


APP_DIR = os.path.dirname(os.path.abspath(__file__))
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_VISION_MODEL = "gpt-5"
MAX_VIDEOS = 100
MAX_COMPETITORS = 5
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
DATE_FILTER_OPTIONS = [
    "All latest 100",
    "Today",
    "Yesterday",
    "Last week to date",
    "Last month",
    "Last 3 months",
]

STOPWORDS = {
    "a", "about", "after", "all", "an", "and", "are", "as", "at", "be",
    "best", "but", "by", "can", "day", "do", "does", "for", "from", "get",
    "how", "i", "in", "into", "is", "it", "its", "me", "my", "new", "not",
    "of", "on", "or", "our", "the", "this", "to", "vs", "we", "what",
    "when", "why", "with", "you", "your",
}

HOOK_WORDS = {
    "avoid", "before", "beginner", "beginners", "case", "checklist",
    "complete", "easy", "explained", "fast", "free", "guide", "hidden",
    "ideas", "mistake", "mistakes", "proven", "secret", "secrets", "simple",
    "step", "truth", "tricks", "tutorial",
}

ACADEMIC_KEYWORDS = {
    "academic", "admission", "assignment", "board", "chapter", "class",
    "college", "concept", "course", "cuet", "degree", "exam", "exams",
    "formula", "jee", "lecture", "lesson", "mock", "neet", "notes", "paper",
    "practice", "pyq", "question", "questions", "revision", "school",
    "semester", "solution", "solutions", "study", "syllabus", "test",
    "university",
}

STRATEGY_KEYWORDS = {
    "career", "case", "checklist", "content", "earn", "growth", "guide",
    "hack", "hacks", "ideas", "income", "interview", "job", "jobs",
    "marketing", "mistake", "mistakes", "motivation", "plan", "planning",
    "productivity", "roadmap", "salary", "secret", "secrets", "startup",
    "strategy", "success", "tips", "tricks", "youtube",
}

TREND_TOPIC_KEYWORDS = {
    "CAT 2027": ["cat 2027", "cat2027"],
    "CAT Preparation": ["cat preparation", "prepare for cat", "cat strategy", "cat prep", "cat study plan"],
    "Mock Analysis": ["mock analysis", "mock test", "cat mock", "mock score", "analyse mock", "analyze mock"],
    "VARC": ["varc", "verbal ability", "reading comprehension", "rc strategy", "vocabulary"],
    "LRDI": ["lrdi", "dilr", "logical reasoning", "data interpretation"],
    "Quant": ["quant", "quantitative aptitude", "arithmetic", "algebra", "geometry"],
    "IIM Admission": ["iim", "iim admission", "iim selection", "iim cutoff", "iim call"],
    "Profile Evaluation": ["profile evaluation", "profile review", "academic profile", "iim profile"],
    "Motivation": ["motivation", "motivational", "success story"],
    "Study Plan": ["study plan", "timetable", "schedule", "routine", "daily plan"],
    "Career Roadmap": ["career", "roadmap", "salary", "job", "interview"],
    "YouTube Growth": ["youtube growth", "views", "subscribers", "content strategy"],
}

COMMENT_TYPE_RULES = [
    (
        "Content request",
        [
            "make video", "video banao", "video banaye", "next video", "please make",
            "please cover", "cover this", "topic par", "request", "needed", "need video",
            "can you make", "please explain",
        ],
    ),
    (
        "Feature/course request",
        [
            "course", "batch", "class", "classes", "live class", "test series", "notes",
            "pdf", "worksheet", "material", "mentorship", "feature", "playlist",
        ],
    ),
    (
        "Purchase intent",
        [
            "price", "fee", "fees", "cost", "buy", "purchase", "payment", "paid",
            "enroll", "enrol", "join", "subscription", "discount", "coupon",
        ],
    ),
    (
        "Complaint",
        [
            "bad", "wrong", "fake", "scam", "worst", "not good", "problem", "issue",
            "error", "late", "boring", "waste", "disappointed", "not working",
            "audio problem", "sound problem",
        ],
    ),
    (
        "Confusion",
        [
            "confuse", "confused", "confusing", "doubt", "unclear", "not understand",
            "samajh", "samajh nahi", "samajh nhi", "clear nahi", "clear nhi",
            "kaise", "meaning",
        ],
    ),
    (
        "Comparison",
        [
            " vs ", "versus", "compare", "comparison", "better than", "which is better",
            "difference between", "best between", "better option",
        ],
    ),
    (
        "Exam anxiety",
        [
            "exam", "marks", "score", "percentile", "rank", "fail", "failure",
            "stress", "anxiety", "fear", "nervous", "panic", "selection", "cutoff",
            "attempt", "mock", "result", "last minute",
        ],
    ),
    (
        "Praise",
        [
            "thanks", "thank you", "helpful", "amazing", "great", "best", "excellent",
            "awesome", "super", "good", "nice", "love", "valuable", "clear explanation",
        ],
    ),
]

QUESTION_WORDS = {
    "what", "why", "how", "when", "where", "which", "who", "can", "should",
    "kya", "kaise", "kab", "kon", "konsa", "kaun", "kyu", "kyun",
}


def load_env_value(env_key: str) -> str:
    env_value = os.getenv(env_key, "").strip()
    if env_value:
        return env_value.strip('"').strip("'")

    try:
        secret_value = str(st.secrets.get(env_key, "")).strip()
        if secret_value:
            return secret_value.strip('"').strip("'")
    except Exception:
        pass

    env_paths = []
    for env_path in [os.path.join(APP_DIR, ".env"), os.path.abspath(".env")]:
        if env_path not in env_paths:
            env_paths.append(env_path)

    for env_path in env_paths:
        if not os.path.exists(env_path):
            continue

        with open(env_path, "r", encoding="utf-8-sig") as env_file:
            for line in env_file:
                clean_line = line.strip()
                if not clean_line or clean_line.startswith("#"):
                    continue
                if clean_line.lower().startswith("export "):
                    clean_line = clean_line[7:].strip()
                key, separator, value = clean_line.partition("=")
                if separator and key.strip() == env_key:
                    return value.strip().strip('"').strip("'")

    return ""


def load_sidebar_secret(secret_key: str) -> str:
    try:
        return str(st.session_state.get(secret_key, "")).strip()
    except Exception:
        return ""


def load_api_key() -> str:
    return load_env_value("YOUTUBE_API_KEY")


def load_openai_api_key() -> str:
    return load_sidebar_secret("openai_api_key_input") or load_env_value("OPENAI_API_KEY")


def load_glm_api_key() -> str:
    return (
        load_sidebar_secret("glm_api_key_input")
        or load_env_value("GLM_API_KEY")
        or load_env_value("ZAI_API_KEY")
    )


def openai_api_cache_key() -> str:
    api_key = load_openai_api_key()
    if not api_key:
        return "missing"
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def glm_api_cache_key() -> str:
    api_key = load_glm_api_key()
    if not api_key:
        return "missing"
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def sanitize_error_text(text: str, secrets: Optional[List[str]] = None) -> str:
    clean = str(text or "")
    for secret in secrets or []:
        if secret:
            clean = clean.replace(secret, "***")
    clean = re.sub(r"([?&]key=)[^&\s)'\"]+", r"\1***", clean)
    clean = re.sub(r"([?&]access_token=)[^&\s)'\"]+", r"\1***", clean)
    return clean


def youtube_network_error_message(error: Exception, api_key: str) -> str:
    details = sanitize_error_text(str(error), [api_key])
    lower_details = details.lower()
    if "10013" in lower_details or "access permissions" in lower_details:
        return (
            "YouTube API connection blocked by Windows firewall, antivirus, proxy, or network permissions. "
            "Allow Python/VS Code network access, then run the app again. "
            f"Safe details: {details}"
        )
    return (
        "Could not connect to YouTube API. Check internet, VPN/proxy, firewall, and Google API access. "
        f"Safe details: {details}"
    )


def request_youtube(endpoint: str, api_key: str, **params) -> Dict:
    params = {key: value for key, value in params.items() if value not in (None, "", [])}
    params["key"] = api_key
    try:
        response = requests.get(f"{YOUTUBE_API_BASE}/{endpoint}", params=params, timeout=30)
    except requests.exceptions.RequestException as error:
        raise RuntimeError(youtube_network_error_message(error, api_key)) from error

    if response.status_code != 200:
        try:
            message = response.json()["error"]["message"]
        except Exception:
            message = response.text
        message = sanitize_error_text(message, [api_key])
        raise RuntimeError(f"YouTube API error ({response.status_code}): {message}")

    return response.json()


def parse_channel_hint(channel_url: str) -> Tuple[str, str]:
    raw = channel_url.strip()
    if not raw:
        raise ValueError("Paste a YouTube channel URL first.")

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


@st.cache_data(show_spinner=False, ttl=3600)
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
    uploads_playlist = item["contentDetails"]["relatedPlaylists"]["uploads"]
    return {
        "id": item["id"],
        "title": item["snippet"]["title"],
        "description": item["snippet"].get("description", ""),
        "published_at": item["snippet"].get("publishedAt"),
        "thumbnail": item["snippet"].get("thumbnails", {}).get("high", {}).get("url"),
        "subscriber_count": int(item.get("statistics", {}).get("subscriberCount", 0)),
        "view_count": int(item.get("statistics", {}).get("viewCount", 0)),
        "video_count": int(item.get("statistics", {}).get("videoCount", 0)),
        "uploads_playlist": uploads_playlist,
    }


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_latest_video_ids(playlist_id: str, api_key: str, limit: int = MAX_VIDEOS) -> List[str]:
    video_ids: List[str] = []
    page_token: Optional[str] = None

    while len(video_ids) < limit:
        data = request_youtube(
            "playlistItems",
            api_key,
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=min(50, limit - len(video_ids)),
            pageToken=page_token,
        )
        video_ids.extend(
            item["contentDetails"]["videoId"]
            for item in data.get("items", [])
            if item.get("contentDetails", {}).get("videoId")
        )
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return video_ids[:limit]


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_playlist_video_ids_by_date_range(
    playlist_id: str,
    api_key: str,
    start_date_text: str,
    end_date_text: str,
    max_videos: int,
) -> List[str]:
    start_date = datetime.fromisoformat(start_date_text).date()
    end_date = datetime.fromisoformat(end_date_text).date()
    start_local = datetime.combine(start_date, datetime.min.time(), tzinfo=APP_TIMEZONE)
    end_local = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=APP_TIMEZONE)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    video_ids: List[str] = []
    page_token: Optional[str] = None

    while len(video_ids) < max_videos:
        data = request_youtube(
            "playlistItems",
            api_key,
            part="contentDetails,snippet",
            playlistId=playlist_id,
            maxResults=50,
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


def parse_duration(duration: str) -> int:
    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?",
        duration,
    )
    if not match:
        return 0
    parts = {key: int(value or 0) for key, value in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


def parse_published_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def words_from_text(text: str) -> List[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]{2,}", text.lower())
    return [word for word in words if word not in STOPWORDS and not word.isdigit()]


def title_keywords(title: str) -> List[str]:
    return words_from_text(title)


def title_hook_words(title: str) -> List[str]:
    words = words_from_text(title)
    hooks = [word for word in words if word in HOOK_WORDS]
    if "?" in title:
        hooks.append("question")
    if re.search(r"\b\d+\b", title):
        hooks.append("number")
    if re.search(r"\b20\d{2}\b", title):
        hooks.append("year")
    return hooks


def score_1_to_10(value: float) -> int:
    return max(1, min(10, int(round(value))))


def title_orientation(title: str) -> str:
    words = set(title_keywords(title))
    search_signals = {
        "how", "what", "why", "guide", "explained", "tutorial", "strategy",
        "tips", "course", "syllabus", "cutoff", "admission", "review",
    }
    browse_signals = {
        "secret", "truth", "mistake", "mistakes", "avoid", "stop", "before",
        "hidden", "shocking", "nobody", "watch", "this",
    }
    search_score = len(words & search_signals)
    browse_score = len(words & browse_signals) + ("?" in title) + bool(re.search(r"\b\d+\b", title))
    if search_score > browse_score:
        return "Search-oriented"
    if browse_score > search_score:
        return "Browse-oriented"
    return "Balanced"


def title_hook_type(title: str) -> str:
    clean = title.lower()
    if "?" in title:
        return "Question"
    if re.search(r"\b\d+\b", title):
        return "Number/list"
    if any(word in clean for word in ["mistake", "avoid", "stop", "wrong"]):
        return "Problem/avoidance"
    if any(word in clean for word in ["secret", "truth", "hidden", "nobody"]):
        return "Curiosity"
    if any(word in clean for word in ["complete", "guide", "explained", "tutorial"]):
        return "Educational"
    if any(word in clean for word in ["before", "now", "today", "last minute"]):
        return "Urgency"
    return "Direct"


def deterministic_title_analysis(title: str) -> Dict:
    title = str(title or "").strip()
    words = re.findall(r"\w+", title)
    title_length = len(title)
    word_count = len(words)
    has_number = bool(re.search(r"\b\d+\b", title))
    has_question = "?" in title
    has_year = bool(re.search(r"\b20\d{2}\b", title))
    lower_title = title.lower()
    keyword_count = len(title_keywords(title))
    hook_words = title_hook_words(title)

    clarity = 10
    if title_length < 25 or title_length > 85:
        clarity -= 2
    if word_count < 4 or word_count > 13:
        clarity -= 1
    if keyword_count < 2:
        clarity -= 2
    if any(symbol in title for symbol in ["!!!", "???", "🔥"]):
        clarity -= 1

    curiosity = 4 + len(hook_words) * 1.4
    if has_question:
        curiosity += 1.5
    if any(word in lower_title for word in ["secret", "truth", "before", "mistake", "avoid", "hidden", "stop"]):
        curiosity += 2

    specificity = 3 + min(keyword_count, 5)
    if has_number:
        specificity += 1.5
    if has_year:
        specificity += 1
    if any(word in lower_title for word in ["cat", "iim", "mock", "percentile", "varc", "lrdi", "quant"]):
        specificity += 1

    urgency = 2
    if any(word in lower_title for word in ["now", "today", "before", "last", "stop", "avoid", "deadline", "2026", "2027"]):
        urgency += 4
    if any(word in lower_title for word in ["mistake", "mistakes", "killing", "fail", "low score"]):
        urgency += 2

    emotion = 3
    if any(word in lower_title for word in ["mistake", "secret", "truth", "fear", "stress", "confused", "stop", "avoid", "killing"]):
        emotion += 4
    if any(word in lower_title for word in ["easy", "simple", "complete", "best"]):
        emotion += 1

    search_orientation = title_orientation(title)
    return {
        "title_length": title_length,
        "word_count": word_count,
        "has_number": "Yes" if has_number else "No",
        "has_question": "Yes" if has_question else "No",
        "has_year": "Yes" if has_year else "No",
        "hook_type": title_hook_type(title),
        "hook_words": ", ".join(hook_words[:6]) if hook_words else "None",
        "curiosity_score": score_1_to_10(curiosity),
        "clarity_score": score_1_to_10(clarity),
        "specificity_score": score_1_to_10(specificity),
        "urgency_score": score_1_to_10(urgency),
        "emotion_score": score_1_to_10(emotion),
        "orientation": search_orientation,
    }


@st.cache_data(show_spinner=False, ttl=86400)
def fetch_thumbnail_bytes(thumbnail_url: str) -> Tuple[bytes, str]:
    if not thumbnail_url:
        return b"", ""
    response = requests.get(thumbnail_url, timeout=30)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
    return response.content, content_type


def thumbnail_data_url(image_bytes: bytes, mime_type: str) -> str:
    if not image_bytes:
        return ""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type or 'image/jpeg'};base64,{encoded}"


def safe_json_from_text(text: str) -> Dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def extract_openai_text(response_json: Dict) -> str:
    if response_json.get("output_text"):
        return response_json["output_text"]

    chunks = []
    for output in response_json.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    return "\n".join(chunks)


def default_thumbnail_ai_analysis(error: str = "") -> Dict:
    return {
        "visible_text": "",
        "thumbnail_text_word_count": 0,
        "face_present": "Unknown",
        "approximate_face_count": 0,
        "dominant_emotion": "Unknown",
        "visual_clutter_score": 5,
        "readability_score": 5,
        "visual_hierarchy_score": 5,
        "thumbnail_curiosity_score": 5,
        "simplicity_score": 5,
        "thumbnail_style": "Other",
        "alignment_score": 5,
        "complementarity_score": 5,
        "redundancy_score": 5,
        "curiosity_gap_score": 5,
        "message_clarity_score": 5,
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
        "improved_title": "",
        "thumbnail_text_angle": "",
        "analysis_error": error,
    }


def normalize_ai_analysis(raw: Dict) -> Dict:
    result = default_thumbnail_ai_analysis()
    result.update(raw or {})

    score_keys = [
        "visual_clutter_score", "readability_score", "visual_hierarchy_score",
        "thumbnail_curiosity_score", "simplicity_score", "alignment_score",
        "complementarity_score", "redundancy_score", "curiosity_gap_score",
        "message_clarity_score",
    ]
    for key in score_keys:
        result[key] = score_1_to_10(float(result.get(key, 5) or 5))

    try:
        result["thumbnail_text_word_count"] = int(result.get("thumbnail_text_word_count", 0) or 0)
    except Exception:
        result["thumbnail_text_word_count"] = 0
    try:
        result["approximate_face_count"] = int(result.get("approximate_face_count", 0) or 0)
    except Exception:
        result["approximate_face_count"] = 0

    allowed_styles = {
        "Face + Text", "Text Heavy", "Object Focused", "Screenshot/UI",
        "Comparison", "Reaction", "Minimal", "Other",
    }
    if result.get("thumbnail_style") not in allowed_styles:
        result["thumbnail_style"] = "Other"

    for key in ["strengths", "weaknesses", "recommendations"]:
        value = result.get(key, [])
        if isinstance(value, str):
            value = [value]
        result[key] = list(value)[:3]

    return result


@st.cache_data(show_spinner=False, ttl=604800)
def analyze_thumbnail_image_with_ai(
    title: str,
    image_bytes: bytes,
    mime_type: str,
    video_id: str,
    views: int,
    views_per_day: float,
    api_key_status: str,
) -> Dict:
    api_key = load_openai_api_key()
    if not api_key:
        return default_thumbnail_ai_analysis("OPENAI_API_KEY missing. Add it in the sidebar or in the project .env file to enable vision thumbnail analysis.")
    if not image_bytes:
        return default_thumbnail_ai_analysis("Thumbnail image missing.")
    data_url = thumbnail_data_url(image_bytes, mime_type)

    prompt = f"""
Analyze this YouTube video package. Do not identify any person by name. Return valid JSON only.

Video metadata:
- video_id: {video_id}
- title: {title}
- views: {views}
- views_per_day: {views_per_day}

Return this exact JSON shape:
{{
  "visible_text": "text visible on thumbnail, or empty",
  "thumbnail_text_word_count": 0,
  "face_present": "Yes/No/Unclear",
  "approximate_face_count": 0,
  "dominant_emotion": "short emotion label",
  "visual_clutter_score": 1,
  "readability_score": 1,
  "visual_hierarchy_score": 1,
  "thumbnail_curiosity_score": 1,
  "simplicity_score": 1,
  "thumbnail_style": "Face + Text/Text Heavy/Object Focused/Screenshot/UI/Comparison/Reaction/Minimal/Other",
  "alignment_score": 1,
  "complementarity_score": 1,
  "redundancy_score": 1,
  "curiosity_gap_score": 1,
  "message_clarity_score": 1,
  "strengths": ["specific strength 1", "specific strength 2", "specific strength 3"],
  "weaknesses": ["specific weakness 1", "specific weakness 2", "specific weakness 3"],
  "recommendations": ["specific improvement 1", "specific improvement 2", "specific improvement 3"],
  "improved_title": "one improved title suggestion",
  "thumbnail_text_angle": "one thumbnail text or visual angle suggestion"
}}

Scoring rules: 1 means weak, 10 means strong. Redundancy score is inverse: higher means unnecessary repetition.
"""
    payload = {
        "model": load_env_value("OPENAI_VISION_MODEL") or DEFAULT_OPENAI_VISION_MODEL,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url, "detail": "low"},
                ],
            }
        ],
        "text": {"format": {"type": "json_object"}},
    }
    try:
        response = requests.post(
            OPENAI_RESPONSES_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=90,
        )
        if response.status_code != 200:
            return default_thumbnail_ai_analysis(f"OpenAI API error ({response.status_code}): {response.text[:300]}")
        parsed = safe_json_from_text(extract_openai_text(response.json()))
        if not parsed:
            return default_thumbnail_ai_analysis("AI returned malformed JSON.")
        return normalize_ai_analysis(parsed)
    except Exception as error:
        return default_thumbnail_ai_analysis(f"AI analysis failed: {error}")


@st.cache_data(show_spinner=False, ttl=604800)
def analyze_thumbnail_with_ai(
    title: str,
    thumbnail_url: str,
    video_id: str,
    views: int,
    views_per_day: float,
    api_key_status: str,
) -> Dict:
    if not thumbnail_url:
        return default_thumbnail_ai_analysis("Thumbnail URL missing.")
    try:
        image_bytes, mime_type = fetch_thumbnail_bytes(thumbnail_url)
    except Exception as error:
        return default_thumbnail_ai_analysis(f"Thumbnail download failed: {error}")

    return analyze_thumbnail_image_with_ai(
        title,
        image_bytes,
        mime_type,
        video_id,
        views,
        views_per_day,
        api_key_status,
    )


@st.cache_data(show_spinner=False, ttl=604800)
def analyze_uploaded_thumbnail_with_sdk(
    title: str,
    image_bytes: bytes,
    filename: str,
    mime_type: str,
    api_key_status: str,
    model: str,
) -> Dict:
    return analyze_thumbnail_package(
        title=title,
        image_bytes=image_bytes,
        filename=filename,
        mime_type=mime_type,
        api_key=load_openai_api_key(),
        model=model or DEFAULT_OPENAI_VISION_MODEL,
    )


def compact_text(value: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def build_glm_comment_payload(
    filtered_comments: pd.DataFrame,
    summary: pd.DataFrame,
    trend: pd.DataFrame,
    idea_df: pd.DataFrame,
    all_videos: pd.DataFrame,
) -> Dict:
    summary_records = []
    if not summary.empty:
        summary_records = summary.head(12).to_dict("records")

    trend_records = []
    if not trend.empty:
        trend_records = trend.sort_values("comments", ascending=False).head(25).to_dict("records")

    idea_records = []
    if not idea_df.empty:
        wanted_cols = [
            "idea_rank", "comment_type", "topic_keyword", "title_1", "title_2",
            "long_tail_keywords", "demand_score", "comments", "videos", "why_make_this",
        ]
        available_cols = [column for column in wanted_cols if column in idea_df.columns]
        idea_records = idea_df[available_cols].head(10).to_dict("records")

    sample_cols = [
        "comment_type", "matched_types", "video_title", "comment_text",
        "comment_likes", "reply_count",
    ]
    available_sample_cols = [column for column in sample_cols if column in filtered_comments.columns]
    comment_samples = []
    if available_sample_cols:
        sample_comments = filtered_comments.sort_values(
            ["comment_likes", "reply_count"],
            ascending=False,
        )[available_sample_cols].head(40)
        for row in sample_comments.to_dict("records"):
            row["comment_text"] = compact_text(row.get("comment_text", ""), 260)
            row["video_title"] = compact_text(row.get("video_title", ""), 140)
            comment_samples.append(row)

    video_context = []
    if not all_videos.empty:
        context_cols = ["channel", "title", "video_type", "views", "views_per_day", "url"]
        available_context_cols = [column for column in context_cols if column in all_videos.columns]
        if available_context_cols:
            top_videos = dedupe_videos(all_videos).sort_values("views", ascending=False).head(25)
            for row in top_videos[available_context_cols].to_dict("records"):
                row["title"] = compact_text(row.get("title", ""), 140)
                video_context.append(row)

    return {
        "comment_type_summary": summary_records,
        "comment_trend": trend_records,
        "current_rule_based_ideas": idea_records,
        "high_signal_comment_samples": comment_samples,
        "top_channel_video_context": video_context,
    }


@st.cache_data(show_spinner=False, ttl=86400)
def generate_cached_glm_comment_report(
    payload: Dict,
    api_key_status: str,
    base_url: str,
    model: str,
) -> Dict:
    report, error = generate_glm_comment_report(
        payload=payload,
        api_key=load_glm_api_key(),
        base_url=base_url or DEFAULT_GLM_BASE_URL,
        model=model or DEFAULT_GLM_MODEL,
    )
    return {"report": report, "error": error}


def packaging_intelligence_score(title_analysis: Dict, thumbnail_analysis: Dict) -> int:
    score = (
        title_analysis.get("clarity_score", 5) * 10 * 0.20
        + title_analysis.get("curiosity_score", 5) * 10 * 0.20
        + thumbnail_analysis.get("readability_score", 5) * 10 * 0.15
        + thumbnail_analysis.get("visual_hierarchy_score", 5) * 10 * 0.15
        + thumbnail_analysis.get("complementarity_score", 5) * 10 * 0.20
        + (11 - thumbnail_analysis.get("redundancy_score", 5)) * 10 * 0.10
    )
    return max(0, min(100, int(round(score))))


def redundancy_label(score: int) -> str:
    if score <= 3:
        return "Low"
    if score <= 6:
        return "Medium"
    return "High"


def analysis_dict_to_frame(data: Dict, labels: Dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Metric": label, "Value": data.get(key, "")} for key, label in labels.items()]
    )


def safe_ratio_score(value: float, best_value: float, fallback: float = 50.0) -> float:
    if best_value <= 0:
        return fallback
    return round(max(0.0, min(100.0, (value / best_value) * 100)), 2)


def rank_band(score: float) -> str:
    if score >= 80:
        return "Strong fit"
    if score >= 65:
        return "Good fit"
    if score >= 50:
        return "Average fit"
    return "Needs improvement"


def term_performance_table(
    videos: pd.DataFrame,
    extractor,
    term_column: str,
    wanted_terms: Optional[set] = None,
) -> pd.DataFrame:
    records = []
    for _, row in videos.iterrows():
        terms = set(extractor(str(row.get("title", ""))))
        if wanted_terms is not None:
            terms = terms & wanted_terms
        for term in terms:
            records.append(
                {
                    term_column: term,
                    "views": row.get("views", 0),
                    "views_per_day": row.get("views_per_day", 0),
                    "title": row.get("title", ""),
                    "channel": row.get("channel", ""),
                }
            )

    if not records:
        return pd.DataFrame(
            columns=[term_column, "uses", "channels", "avg_views", "avg_views_per_day", "best_title"]
        )

    term_df = pd.DataFrame(records)
    return (
        term_df.groupby(term_column)
        .agg(
            uses=(term_column, "size"),
            channels=("channel", "nunique"),
            avg_views=("views", "mean"),
            avg_views_per_day=("views_per_day", "mean"),
            best_title=("title", lambda values: values.iloc[0]),
        )
        .round(2)
        .reset_index()
        .sort_values(["avg_views_per_day", "uses"], ascending=False)
    )


def build_youtube_data_fit_report(title: str, videos: pd.DataFrame, packaging_score: int) -> Tuple[Dict, pd.DataFrame]:
    if videos.empty:
        return {
            "youtube_data_fit_score": 0,
            "rank_band": "No data",
            "keyword_score": 0,
            "hook_score": 0,
            "length_bucket_score": 0,
            "similar_video_score": 0,
            "matched_keywords": "None",
            "matched_hooks": "None",
            "title_length_bucket": length_bucket(len(title or "")),
            "benchmark_videos": 0,
            "benchmark_channels": 0,
            "benchmark_note": "Analyse channels first to compare this package with YouTube data.",
        }, pd.DataFrame()

    data = prepare_video_frame(dedupe_videos(videos)).copy()
    if data.empty:
        return build_youtube_data_fit_report(title, pd.DataFrame(), packaging_score)

    for column, default in {
        "title": "",
        "channel": "",
        "video_type": "",
        "views": 0,
        "views_per_day": 0.0,
        "url": "",
        "video_id": "",
    }.items():
        if column not in data.columns:
            data[column] = default
    data["views"] = pd.to_numeric(data["views"], errors="coerce").fillna(0).astype(int)
    data["views_per_day"] = pd.to_numeric(data["views_per_day"], errors="coerce").fillna(0.0)

    custom_keywords = set(title_keywords(title))
    custom_hooks = set(title_hook_words(title))
    title_bucket = length_bucket(len(title or ""))

    all_keyword_perf = term_performance_table(data, title_keywords, "keyword")
    if not all_keyword_perf.empty and custom_keywords:
        matched_keyword_perf = term_performance_table(data, title_keywords, "keyword", custom_keywords)
        keyword_score = safe_ratio_score(
            matched_keyword_perf["avg_views_per_day"].mean() if not matched_keyword_perf.empty else 0,
            all_keyword_perf["avg_views_per_day"].max(),
            fallback=45.0,
        )
        matched_keywords = ", ".join(matched_keyword_perf["keyword"].head(8).tolist()) or "None"
    else:
        keyword_score = 45.0
        matched_keywords = "None"

    all_hook_perf = term_performance_table(data, title_hook_words, "hook_keyword")
    if not all_hook_perf.empty and custom_hooks:
        matched_hook_perf = term_performance_table(data, title_hook_words, "hook_keyword", custom_hooks)
        hook_score = safe_ratio_score(
            matched_hook_perf["avg_views_per_day"].mean() if not matched_hook_perf.empty else 0,
            all_hook_perf["avg_views_per_day"].max(),
            fallback=45.0,
        )
        matched_hooks = ", ".join(matched_hook_perf["hook_keyword"].head(8).tolist()) or "None"
    else:
        hook_score = 45.0
        matched_hooks = "None"

    bucket_df = bucket_table(data, "title_length_bucket") if "title_length_bucket" in data.columns else pd.DataFrame()
    if not bucket_df.empty and title_bucket in bucket_df["title_length_bucket"].values:
        bucket_avg = float(bucket_df.loc[bucket_df["title_length_bucket"] == title_bucket, "avg_views_per_day"].iloc[0])
        length_bucket_score = safe_ratio_score(bucket_avg, float(bucket_df["avg_views_per_day"].max()), fallback=50.0)
    else:
        length_bucket_score = 50.0

    def matching_terms(row_title: str) -> List[str]:
        row_terms = set(title_keywords(row_title)) | set(title_hook_words(row_title))
        return sorted((custom_keywords | custom_hooks) & row_terms)

    data["matched_terms_list"] = data["title"].apply(matching_terms)
    data["matched_term_count"] = data["matched_terms_list"].apply(len)
    similar = data[data["matched_term_count"] > 0].copy()
    if not similar.empty:
        best_vpd = max(float(data["views_per_day"].max()), 1.0)
        similar["match_strength"] = similar["matched_term_count"] * 10 + similar["views_per_day"].apply(lambda value: safe_ratio_score(value, best_vpd, fallback=0))
        similar = similar.sort_values(["match_strength", "views_per_day"], ascending=False)
        similar_video_score = safe_ratio_score(float(similar.head(5)["views_per_day"].mean()), best_vpd, fallback=45.0)
        similar_display = similar.head(10).copy()
        similar_display["matched_terms"] = similar_display["matched_terms_list"].apply(lambda terms: ", ".join(terms))
        similar_display = similar_display[
            ["channel", "title", "video_type", "views", "views_per_day", "matched_terms", "url"]
        ].reset_index(drop=True)
    else:
        similar_video_score = 40.0
        similar_display = pd.DataFrame(
            columns=["channel", "title", "video_type", "views", "views_per_day", "matched_terms", "url"]
        )

    final_score = round(
        packaging_score * 0.45
        + keyword_score * 0.25
        + hook_score * 0.15
        + length_bucket_score * 0.10
        + similar_video_score * 0.05,
        1,
    )
    report = {
        "youtube_data_fit_score": final_score,
        "rank_band": rank_band(final_score),
        "keyword_score": round(keyword_score, 1),
        "hook_score": round(hook_score, 1),
        "length_bucket_score": round(length_bucket_score, 1),
        "similar_video_score": round(similar_video_score, 1),
        "matched_keywords": matched_keywords,
        "matched_hooks": matched_hooks,
        "title_length_bucket": title_bucket,
        "benchmark_videos": int(data["video_id"].nunique()) if "video_id" in data.columns else len(data),
        "benchmark_channels": int(data["channel"].nunique()) if "channel" in data.columns else 0,
        "benchmark_note": "Score compares this package with the current analysed channel + competitor dataset. It is not CTR or views prediction.",
    }
    return report, similar_display


def starts_with_pattern(title: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title)
    return " ".join(words[:3]).lower() if words else ""


def length_bucket(title_length: int) -> str:
    if title_length < 45:
        return "Short (<45 chars)"
    if title_length <= 70:
        return "Medium (45-70 chars)"
    return "Long (>70 chars)"


def video_length_bucket(seconds: int) -> str:
    if seconds <= 60:
        return "Shorts (<1 min)"
    if seconds < 480:
        return "Short video (1-8 min)"
    if seconds <= 1200:
        return "Standard (8-20 min)"
    return "Long-form (>20 min)"


def video_type(seconds: int) -> str:
    return "Shorts" if seconds <= 60 else "Long video"


def bool_label(value: bool) -> str:
    return "Yes" if value else "No"


def date_filter_window(option: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    now_local = datetime.now(APP_TIMEZONE)
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    if option == "Today":
        start_local = today_start
        end_local = now_local
    elif option == "Yesterday":
        start_local = today_start - timedelta(days=1)
        end_local = today_start
    elif option == "Last week to date":
        start_local = now_local - timedelta(days=7)
        end_local = now_local
    elif option == "Last month":
        start_local = now_local - timedelta(days=30)
        end_local = now_local
    elif option == "Last 3 months":
        start_local = now_local - timedelta(days=90)
        end_local = now_local
    else:
        return None, None

    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def filter_videos_by_date(videos: pd.DataFrame, option: str) -> pd.DataFrame:
    if videos.empty or option == "All latest 100":
        return videos.copy()

    start_utc, end_utc = date_filter_window(option)
    if start_utc is None or end_utc is None:
        return videos.copy()

    df = videos.copy()
    published = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    mask = (published >= start_utc) & (published < end_utc)
    return df[mask].reset_index(drop=True)


def date_filter_caption(option: str) -> str:
    start_utc, end_utc = date_filter_window(option)
    if start_utc is None or end_utc is None:
        return "Showing fetched latest 100 videos per channel."

    start_local = start_utc.astimezone(APP_TIMEZONE).strftime("%Y-%m-%d %H:%M")
    end_local = end_utc.astimezone(APP_TIMEZONE).strftime("%Y-%m-%d %H:%M")
    return f"Showing videos from {start_local} to {end_local} IST."


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_video_details(video_ids: Tuple[str, ...], api_key: str) -> pd.DataFrame:
    rows = []

    for start in range(0, len(video_ids), 50):
        batch = video_ids[start : start + 50]
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
            published_at = parse_published_at(snippet["publishedAt"])
            age_days = max((datetime.now(timezone.utc) - published_at).total_seconds() / 86400, 1)
            duration_seconds = parse_duration(details.get("duration", "PT0S"))
            views = int(stats.get("viewCount", 0))
            tags = snippet.get("tags", [])

            rows.append(
                {
                    "video_id": item["id"],
                    "title": title,
                    "source_channel": snippet.get("channelTitle", ""),
                    "source_channel_id": snippet.get("channelId", ""),
                    "upload_date": published_at.date().isoformat(),
                    "published_at": published_at,
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
                    "video_type": video_type(duration_seconds),
                    "views_per_day": round(views / age_days, 2),
                    "keywords": ", ".join(title_keywords(title)),
                    "hook_keywords": ", ".join(title_hook_words(title)),
                    "opening_pattern": starts_with_pattern(title),
                    "youtube_tags": ", ".join(tags),
                    "url": f"https://www.youtube.com/watch?v={item['id']}",
                    "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                    "ctr": None,
                }
            )

    if not rows:
        return pd.DataFrame()

    return dedupe_videos(pd.DataFrame(rows)).sort_values("published_at", ascending=False)


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_channel_video_ids_by_date(
    channel_id: str,
    api_key: str,
    published_after: str,
    published_before: str,
    max_videos: int,
) -> List[str]:
    video_ids: List[str] = []
    page_token: Optional[str] = None

    while len(video_ids) < max_videos:
        data = request_youtube(
            "search",
            api_key,
            part="id",
            channelId=channel_id,
            type="video",
            order="date",
            publishedAfter=published_after,
            publishedBefore=published_before,
            maxResults=min(50, max_videos - len(video_ids)),
            pageToken=page_token,
        )
        for item in data.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if video_id and video_id not in video_ids:
                video_ids.append(video_id)
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return video_ids[:max_videos]


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_channel_videos_by_date_range(
    channel_id: str,
    channel_title: str,
    api_key: str,
    start_date_text: str,
    end_date_text: str,
    max_videos: int,
) -> pd.DataFrame:
    start_date = datetime.fromisoformat(start_date_text).date()
    end_date = datetime.fromisoformat(end_date_text).date()
    start_local = datetime.combine(start_date, datetime.min.time(), tzinfo=APP_TIMEZONE)
    end_local = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=APP_TIMEZONE)
    published_after = start_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    published_before = end_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    video_ids = fetch_channel_video_ids_by_date(
        channel_id,
        api_key,
        published_after,
        published_before,
        max_videos,
    )
    if not video_ids:
        return pd.DataFrame()

    videos = fetch_video_details(tuple(video_ids), api_key)
    if videos.empty:
        return videos

    videos = prepare_video_frame(videos).copy()
    videos["channel"] = channel_title
    videos["channel_id"] = channel_id
    return videos


def extract_search_tags(row: pd.Series) -> List[str]:
    tags = []
    raw_tags = str(row.get("youtube_tags", "") or "")
    for tag in raw_tags.split(","):
        clean = " ".join(tag.strip().lower().split())
        if clean and clean not in STOPWORDS:
            tags.append(clean)
    if not tags:
        tags = title_keywords(str(row.get("title", "")))
    return tags


def top_terms_from_rows(rows: pd.DataFrame, extractor, top_n: int = 8) -> str:
    counter: Counter = Counter()
    for _, row in rows.iterrows():
        counter.update(set(extractor(row)))
    return ", ".join(term for term, _ in counter.most_common(top_n)) or "None"


def top_title_keywords_from_rows(rows: pd.DataFrame, top_n: int = 8) -> str:
    counter: Counter = Counter()
    for title in rows.get("title", pd.Series(dtype="string")).fillna(""):
        counter.update(set(title_keywords(str(title))))
    return ", ".join(term for term, _ in counter.most_common(top_n)) or "None"


def build_monthly_competitor_summary(videos: pd.DataFrame) -> pd.DataFrame:
    if videos.empty:
        return pd.DataFrame(
            columns=[
                "month", "channel", "total_videos", "total_views", "avg_views",
                "avg_views_per_day", "shorts", "long_videos", "trending_keywords",
                "trending_tags", "top_video_title", "top_video_views", "top_video_url",
            ]
        )

    df = prepare_video_frame(dedupe_videos(videos)).copy()
    published = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    df = df[published.notna()].copy()
    df["published_at"] = published[published.notna()]
    df["month"] = df["published_at"].dt.tz_convert(APP_TIMEZONE).dt.strftime("%Y-%m")
    df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
    df["views_per_day"] = pd.to_numeric(df["views_per_day"], errors="coerce").fillna(0.0)

    rows = []
    for (month, channel), group in df.groupby(["month", "channel"], sort=True):
        top_video = group.sort_values("views", ascending=False).iloc[0]
        rows.append(
            {
                "month": month,
                "channel": channel,
                "total_videos": int(group["video_id"].nunique()),
                "total_views": int(group["views"].sum()),
                "avg_views": round(float(group["views"].mean()), 2),
                "avg_views_per_day": round(float(group["views_per_day"].mean()), 2),
                "shorts": int(group["video_type"].eq("Shorts").sum()) if "video_type" in group.columns else 0,
                "long_videos": int(group["video_type"].eq("Long video").sum()) if "video_type" in group.columns else 0,
                "trending_keywords": top_title_keywords_from_rows(group, top_n=8),
                "trending_tags": top_terms_from_rows(group, extract_search_tags, top_n=8),
                "top_video_title": top_video.get("title", ""),
                "top_video_views": int(top_video.get("views", 0)),
                "top_video_url": top_video.get("url", ""),
            }
        )

    return pd.DataFrame(rows).sort_values(["month", "total_views"], ascending=[True, False]).reset_index(drop=True)


def build_monthly_term_report(videos: pd.DataFrame, term_type: str, top_n_per_month: int = 10) -> pd.DataFrame:
    if videos.empty:
        return pd.DataFrame(
            columns=["month", "channel", term_type, "videos", "total_views", "avg_views_per_day", "best_title", "best_url"]
        )

    df = prepare_video_frame(dedupe_videos(videos)).copy()
    published = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    df = df[published.notna()].copy()
    df["published_at"] = published[published.notna()]
    df["month"] = df["published_at"].dt.tz_convert(APP_TIMEZONE).dt.strftime("%Y-%m")
    df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
    df["views_per_day"] = pd.to_numeric(df["views_per_day"], errors="coerce").fillna(0.0)

    records = []
    for _, row in df.iterrows():
        terms = title_keywords(str(row.get("title", ""))) if term_type == "keyword" else extract_search_tags(row)
        for term in set(terms):
            records.append(
                {
                    "month": row.get("month", ""),
                    "channel": row.get("channel", ""),
                    term_type: term,
                    "views": row.get("views", 0),
                    "views_per_day": row.get("views_per_day", 0),
                    "title": row.get("title", ""),
                    "url": row.get("url", ""),
                }
            )

    if not records:
        return pd.DataFrame(
            columns=["month", "channel", term_type, "videos", "total_views", "avg_views_per_day", "best_title", "best_url"]
        )

    terms_df = pd.DataFrame(records).sort_values("views", ascending=False)
    grouped = (
        terms_df.groupby(["month", "channel", term_type])
        .agg(
            videos=(term_type, "size"),
            total_views=("views", "sum"),
            avg_views_per_day=("views_per_day", "mean"),
            best_title=("title", lambda values: values.iloc[0]),
            best_url=("url", lambda values: values.iloc[0]),
        )
        .round(2)
        .reset_index()
        .sort_values(["month", "channel", "total_views", "videos"], ascending=[True, True, False, False])
    )
    grouped["rank"] = grouped.groupby(["month", "channel"])["total_views"].rank(method="first", ascending=False)
    return grouped[grouped["rank"] <= top_n_per_month].drop(columns=["rank"]).reset_index(drop=True)


def build_competitor_time_trend(videos: pd.DataFrame, granularity: str) -> pd.DataFrame:
    if videos.empty:
        return pd.DataFrame(
            columns=[
                "period", "period_label", "channel", "videos_uploaded",
                "total_views", "avg_views", "avg_views_per_day",
            ]
        )

    df = prepare_video_frame(dedupe_videos(videos)).copy()
    published = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    df = df[published.notna()].copy()
    if df.empty:
        return pd.DataFrame(
            columns=[
                "period", "period_label", "channel", "videos_uploaded",
                "total_views", "avg_views", "avg_views_per_day",
            ]
        )

    df["published_at"] = published[published.notna()].dt.tz_convert(APP_TIMEZONE)
    df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
    df["views_per_day"] = pd.to_numeric(df["views_per_day"], errors="coerce").fillna(0.0)

    if granularity == "Month wise":
        df["period"] = pd.to_datetime(df["published_at"].dt.strftime("%Y-%m-01"))
        df["period_label"] = df["published_at"].dt.strftime("%Y-%m")
    else:
        df["period"] = pd.to_datetime(df["published_at"].dt.date)
        df["period_label"] = df["published_at"].dt.strftime("%Y-%m-%d")

    trend = (
        df.groupby(["period", "period_label", "channel"])
        .agg(
            videos_uploaded=("video_id", "nunique"),
            total_views=("views", "sum"),
            avg_views=("views", "mean"),
            avg_views_per_day=("views_per_day", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values(["period", "channel"])
    )
    return trend


def uploaded_videos_export_sheet(videos: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "upload_date", "channel", "title", "video_type", "views", "likes", "comments",
        "views_per_day", "video_age_days", "duration_minutes", "title_length",
        "word_count", "has_number", "has_question", "has_year", "keywords",
        "hook_keywords", "youtube_tags", "url", "thumbnail", "video_id",
    ]
    if videos.empty:
        return pd.DataFrame(columns=columns)

    df = prepare_video_frame(dedupe_videos(videos)).copy()
    if "published_at" in df.columns:
        published = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df["_sort_date"] = published
        if "upload_date" not in df.columns:
            df["upload_date"] = published.dt.date
    elif "upload_date" in df.columns:
        df["_sort_date"] = pd.to_datetime(df["upload_date"], errors="coerce")
    else:
        df["_sort_date"] = pd.NaT
        df["upload_date"] = pd.NaT

    for column in columns:
        if column not in df.columns:
            df[column] = ""

    df["upload_date"] = pd.to_datetime(df["upload_date"], errors="coerce").dt.date
    numeric_columns = [
        "views", "likes", "comments", "views_per_day", "video_age_days",
        "duration_minutes", "title_length", "word_count",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    return (
        df.sort_values("_sort_date", ascending=False, na_position="last")[columns]
        .reset_index(drop=True)
    )


def dedupe_videos(videos: pd.DataFrame) -> pd.DataFrame:
    if videos.empty or "video_id" not in videos.columns:
        return videos
    return videos.drop_duplicates(subset=["video_id"], keep="first").reset_index(drop=True)


def dedupe_channels(channels: List[Dict]) -> List[Dict]:
    unique_channels = []
    seen_ids = set()
    for channel in channels:
        if channel["id"] not in seen_ids:
            seen_ids.add(channel["id"])
            unique_channels.append(channel)
    return unique_channels


def filter_videos_by_type(videos: pd.DataFrame, selected_type: str) -> pd.DataFrame:
    if selected_type == "Shorts":
        return videos[videos["video_type"] == "Shorts"].copy()
    if selected_type == "Long videos":
        return videos[videos["video_type"] == "Long video"].copy()
    return videos.copy()


def load_channel_videos(channel_url: str, api_key: str) -> Tuple[Dict, pd.DataFrame]:
    channel = resolve_channel(channel_url, api_key)
    video_ids = fetch_latest_video_ids(channel["uploads_playlist"], api_key)
    if not video_ids:
        raise ValueError(f"No public videos found for {channel['title']}.")
    videos = fetch_video_details(tuple(video_ids), api_key)
    videos.insert(0, "channel", channel["title"])
    videos.insert(1, "channel_id", channel["id"])
    return channel, videos


def load_channel_videos_for_date_range(
    channel_url: str,
    api_key: str,
    start_date_text: str,
    end_date_text: str,
    max_videos: int,
) -> Tuple[Dict, pd.DataFrame]:
    channel = resolve_channel(channel_url, api_key)
    video_ids = fetch_playlist_video_ids_by_date_range(
        channel["uploads_playlist"],
        api_key,
        start_date_text,
        end_date_text,
        max_videos,
    )
    if not video_ids:
        return channel, pd.DataFrame()

    videos = fetch_video_details(tuple(video_ids), api_key)
    if videos.empty:
        return channel, videos
    videos.insert(0, "channel", channel["title"])
    videos.insert(1, "channel_id", channel["id"])
    return channel, videos


@st.cache_data(show_spinner=False, ttl=1800)
def fetch_video_comments(video_id: str, api_key: str, max_comments: int = 100, order: str = "time") -> pd.DataFrame:
    rows = []
    page_token: Optional[str] = None
    safe_limit = max(1, min(int(max_comments), 500))

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
            comment_snippet = top_comment.get("snippet", {})
            published_at = comment_snippet.get("publishedAt")
            updated_at = comment_snippet.get("updatedAt")

            rows.append(
                {
                    "video_id": video_id,
                    "comment_id": top_comment.get("id", item.get("id", "")),
                    "author": comment_snippet.get("authorDisplayName", ""),
                    "comment_text": comment_snippet.get("textDisplay", ""),
                    "comment_likes": int(comment_snippet.get("likeCount", 0)),
                    "comment_published_at": parse_published_at(published_at) if published_at else None,
                    "comment_updated_at": parse_published_at(updated_at) if updated_at else None,
                    "reply_count": int(snippet.get("totalReplyCount", 0)),
                }
            )

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return pd.DataFrame(rows)


def classify_comment_text(comment_text: str) -> Tuple[str, str]:
    text = f" {str(comment_text).lower()} "
    words = set(words_from_text(text))
    matched_types = []

    if "?" in text or words & QUESTION_WORDS:
        matched_types.append("Question")

    for comment_type, phrases in COMMENT_TYPE_RULES:
        for phrase in phrases:
            phrase = phrase.lower()
            if " " in phrase:
                if phrase in text:
                    matched_types.append(comment_type)
                    break
            elif phrase in words:
                matched_types.append(comment_type)
                break

    if not matched_types:
        matched_types.append("General")

    priority = [
        "Purchase intent", "Content request", "Feature/course request", "Complaint",
        "Confusion", "Comparison", "Exam anxiety", "Question", "Praise", "General",
    ]
    primary_type = next(comment_type for comment_type in priority if comment_type in matched_types)
    return primary_type, ", ".join(dict.fromkeys(matched_types))


def enrich_comment_analysis(comments: pd.DataFrame, selected_videos: pd.DataFrame) -> pd.DataFrame:
    if comments.empty:
        return pd.DataFrame(
            columns=[
                "channel", "video_title", "video_type", "video_views", "video_url", "comment_type",
                "matched_types", "comment_text", "comment_likes", "reply_count", "comment_published_at",
            ]
        )

    video_columns = ["video_id", "channel", "title", "video_type", "views", "url"]
    available_columns = [column for column in video_columns if column in selected_videos.columns]
    videos_lookup = selected_videos[available_columns].drop_duplicates("video_id")

    enriched = comments.merge(videos_lookup, on="video_id", how="left")
    classified = enriched["comment_text"].apply(classify_comment_text)
    enriched["comment_type"] = classified.apply(lambda item: item[0])
    enriched["matched_types"] = classified.apply(lambda item: item[1])
    enriched["comment_date"] = pd.to_datetime(
        enriched["comment_published_at"], utc=True, errors="coerce"
    ).dt.tz_convert(APP_TIMEZONE).dt.date
    enriched = enriched.rename(
        columns={
            "title": "video_title",
            "views": "video_views",
            "url": "video_url",
        }
    )
    return enriched


def comment_type_summary(comments: pd.DataFrame) -> pd.DataFrame:
    if comments.empty:
        return pd.DataFrame(columns=["comment_type", "comments", "unique_videos", "avg_likes", "total_replies"])

    return (
        comments.groupby("comment_type")
        .agg(
            comments=("comment_id", "count"),
            unique_videos=("video_id", "nunique"),
            avg_likes=("comment_likes", "mean"),
            total_replies=("reply_count", "sum"),
        )
        .round(2)
        .reset_index()
        .sort_values("comments", ascending=False)
    )


def comment_time_trend(comments: pd.DataFrame, time_frame: str) -> pd.DataFrame:
    if comments.empty:
        return pd.DataFrame(columns=["period", "comment_type", "comments"])

    trend = comments.dropna(subset=["comment_published_at"]).copy()
    if trend.empty:
        return pd.DataFrame(columns=["period", "comment_type", "comments"])

    published = pd.to_datetime(trend["comment_published_at"], utc=True, errors="coerce").dt.tz_convert(APP_TIMEZONE)
    if time_frame == "Hour of day":
        trend["period"] = published.dt.hour.astype(str).str.zfill(2) + ":00"
    elif time_frame == "Week":
        iso = published.dt.isocalendar()
        trend["period"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    elif time_frame == "Month":
        trend["period"] = published.dt.strftime("%Y-%m")
    else:
        trend["period"] = published.dt.strftime("%Y-%m-%d")

    return (
        trend.groupby(["period", "comment_type"])
        .size()
        .reset_index(name="comments")
        .sort_values(["period", "comments"], ascending=[True, False])
    )


def top_comment_examples(comments: pd.DataFrame, selected_type: str, limit: int = 20) -> pd.DataFrame:
    if comments.empty:
        return pd.DataFrame()

    filtered = comments[comments["comment_type"] == selected_type].copy()
    if filtered.empty:
        return pd.DataFrame()

    columns = [
        "comment_type", "channel", "video_title", "comment_text", "comment_likes",
        "reply_count", "comment_date", "video_url",
    ]
    return (
        filtered.sort_values(["comment_likes", "reply_count"], ascending=False)
        .head(limit)[columns]
        .reset_index(drop=True)
    )


def comment_topic_keywords(comment_text: str, video_title: str = "", max_keywords: int = 5) -> List[str]:
    extra_stopwords = {
        "sir", "mam", "maam", "bro", "please", "pls", "plz", "video", "videos",
        "make", "banao", "banaye", "hai", "hain", "nahi", "nhi", "kya", "kaise",
        "thank", "thanks", "good", "nice", "complete", "full", "guide", "details",
        "join", "joining", "joined", "now", "want", "need",
    }
    keywords = []
    for word in words_from_text(f"{comment_text} {video_title}"):
        if word in extra_stopwords or len(word) < 3:
            continue
        if word not in keywords:
            keywords.append(word)
    return keywords[:max_keywords]


def title_case_topic(topic: str) -> str:
    clean_topic = " ".join(str(topic).split())
    if not clean_topic:
        return "Student Demand"

    acronyms = {"cat", "iim", "mba", "varc", "lrdi", "dilr", "qa", "cuet", "jee", "neet"}
    return " ".join(word.upper() if word.lower() in acronyms else word.title() for word in clean_topic.split())


def comment_idea_title(comment_type: str, topic: str) -> str:
    topic_title = title_case_topic(topic)
    templates = {
        "Question": f"{topic_title} Explained: Your Top Questions Answered",
        "Content request": f"Complete {topic_title} Guide: What Students Asked For",
        "Complaint": f"Common {topic_title} Problems and How to Fix Them",
        "Confusion": f"{topic_title} Confusion Clear: Simple Step-by-Step Explanation",
        "Praise": f"More {topic_title} Tips That Students Found Helpful",
        "Purchase intent": f"{topic_title}: Fees, Course Details and Is It Worth It?",
        "Comparison": f"{topic_title} Comparison: Which Option Is Better?",
        "Exam anxiety": f"{topic_title} Strategy: Reduce Stress and Improve Score",
        "Feature/course request": f"{topic_title} Resources: Notes, Course, Practice Plan",
        "General": f"{topic_title}: What Your Audience Wants Next",
    }
    return templates.get(comment_type, templates["General"])


def channel_context_keywords(topic: str, all_videos: Optional[pd.DataFrame] = None, limit: int = 8) -> List[str]:
    related = []
    topic_words = set(words_from_text(topic))
    generic_keywords = {"complete", "guide", "full", "best", "latest", "video", "videos"}

    if topic:
        related.append(topic)

    if all_videos is None or all_videos.empty:
        return related[:limit]

    videos = prepare_video_frame(all_videos)
    try:
        strong_keywords = keyword_table(videos, top_n=50)["keyword"].tolist()
    except Exception:
        strong_keywords = []

    for keyword in strong_keywords:
        if keyword in generic_keywords:
            continue
        if keyword not in related:
            related.append(keyword)

    for _, row in videos.sort_values("views_per_day", ascending=False).head(80).iterrows():
        search_text = f"{row.get('title', '')} {row.get('keywords', '')} {row.get('youtube_tags', '')}".lower()
        if topic_words and not any(word in search_text for word in topic_words):
            continue

        for keyword in title_keywords(search_text):
            if keyword in generic_keywords:
                continue
            if keyword not in related:
                related.append(keyword)
            if len(related) >= limit:
                return related[:limit]

    return related[:limit]


def comment_long_tail_keywords(comment_type: str, topic: str, related_keywords: List[str]) -> List[str]:
    topic_clean = title_case_topic(topic).lower()
    related = [keyword for keyword in related_keywords if keyword and keyword.lower() != topic_clean]
    first_related = related[0] if related else "strategy"
    second_related = related[1] if len(related) > 1 else "guide"

    templates = {
        "Question": [
            f"{topic_clean} questions answered",
            f"how to understand {topic_clean}",
            f"{topic_clean} doubts clear",
            f"{topic_clean} explained for beginners",
            f"{topic_clean} {first_related} guide",
        ],
        "Content request": [
            f"{topic_clean} complete guide",
            f"{topic_clean} step by step strategy",
            f"{topic_clean} {first_related} roadmap",
            f"best way to prepare {topic_clean}",
            f"{topic_clean} {second_related} tips",
        ],
        "Complaint": [
            f"{topic_clean} common problems",
            f"{topic_clean} mistakes to avoid",
            f"why {topic_clean} is not working",
            f"{topic_clean} problem solution",
            f"{topic_clean} better method",
        ],
        "Confusion": [
            f"{topic_clean} simple explanation",
            f"{topic_clean} confusion clear",
            f"{topic_clean} basics for beginners",
            f"{topic_clean} step by step",
            f"{topic_clean} easy method",
        ],
        "Praise": [
            f"{topic_clean} advanced tips",
            f"{topic_clean} more examples",
            f"{topic_clean} practical guide",
            f"{topic_clean} success strategy",
            f"{topic_clean} next steps",
        ],
        "Purchase intent": [
            f"{topic_clean} fees",
            f"{topic_clean} review",
            f"{topic_clean} worth it",
            f"{topic_clean} price and details",
            f"{topic_clean} how to join",
        ],
        "Comparison": [
            f"{topic_clean} comparison",
            f"{topic_clean} vs {first_related}",
            f"{topic_clean} which is better",
            f"{topic_clean} best option",
            f"{topic_clean} difference explained",
        ],
        "Exam anxiety": [
            f"{topic_clean} exam strategy",
            f"{topic_clean} stress management",
            f"{topic_clean} last minute plan",
            f"{topic_clean} score improvement",
            f"{topic_clean} preparation mistakes",
        ],
        "Feature/course request": [
            f"{topic_clean} notes pdf",
            f"{topic_clean} practice plan",
            f"{topic_clean} details",
            f"{topic_clean} study material",
            f"{topic_clean} test series",
        ],
    }
    keywords = templates.get(comment_type, templates["Content request"])
    cleaned_keywords = [
        re.sub(r"\b(\w+)\s+\1\b", r"\1", keyword).strip()
        for keyword in keywords
    ]
    return list(dict.fromkeys(cleaned_keywords))[:5]


def comment_title_options(comment_type: str, topic: str, related_keywords: List[str]) -> List[str]:
    topic_title = title_case_topic(topic)
    current_year = datetime.now().year
    related = [title_case_topic(keyword) for keyword in related_keywords if keyword and keyword != topic]
    first_related = related[0] if related else "Strategy"

    templates = {
        "Question": [
            f"{topic_title} Explained: Your Top Questions Answered",
            f"All {topic_title} Doubts Clear in One Video",
            f"{topic_title} Q&A: What Students Are Asking Right Now",
            f"How to Understand {topic_title}: Simple Guide for {current_year}",
            f"{topic_title} Confusion? Watch This Before You Decide",
        ],
        "Content request": [
            f"Complete {topic_title} Guide: What Students Asked For",
            f"{topic_title} Step-by-Step Roadmap for {current_year}",
            f"How to Master {topic_title}: Beginner to Advanced Plan",
            f"{topic_title} Strategy That Actually Works",
            f"Before You Start {topic_title}, Watch This Full Guide",
        ],
        "Complaint": [
            f"Common {topic_title} Problems and How to Fix Them",
            f"{topic_title} Mistakes Students Keep Making",
            f"Why {topic_title} Is Not Working for You",
            f"{topic_title} Problem Solved: Do This Instead",
            f"Avoid These {topic_title} Mistakes in {current_year}",
        ],
        "Confusion": [
            f"{topic_title} Confusion Clear: Simple Step-by-Step Explanation",
            f"{topic_title} Explained Like a Beginner",
            f"Still Confused About {topic_title}? Watch This",
            f"{topic_title} Basics to Advanced: Easy Method",
            f"{topic_title} Full Concept Clear in One Video",
        ],
        "Praise": [
            f"More {topic_title} Tips That Students Found Helpful",
            f"{topic_title}: Advanced Tips After Your Positive Response",
            f"{topic_title} Part 2: More Examples and Strategy",
            f"What Works Best in {topic_title}: Real Student Feedback",
            f"{topic_title} Practical Guide with Examples",
        ],
        "Purchase intent": [
            f"{topic_title}: Fees, Course Details and Is It Worth It?",
            f"{topic_title} Course Review: Price, Value and Who Should Join",
            f"Before You Buy {topic_title}, Watch This Honest Guide",
            f"{topic_title} Payment, Features and Complete Details",
            f"Is {topic_title} Worth It in {current_year}?",
        ],
        "Comparison": [
            f"{topic_title} vs {first_related}: Which Is Better?",
            f"{topic_title} Comparison: Best Option for Students",
            f"{topic_title} Difference Explained with Pros and Cons",
            f"Which Should You Choose: {topic_title} or {first_related}?",
            f"{topic_title} Best Option Guide for {current_year}",
        ],
        "Exam anxiety": [
            f"{topic_title} Strategy: Reduce Stress and Improve Score",
            f"{topic_title} Last-Minute Plan for Serious Students",
            f"Low Score in {topic_title}? Do This Next",
            f"{topic_title} Exam Anxiety: Practical Recovery Plan",
            f"{topic_title} Score Improvement Roadmap for {current_year}",
        ],
        "Feature/course request": [
            f"{topic_title} Resources: Notes, Course and Practice Plan",
            f"Complete {topic_title} Study Material and Roadmap",
            f"{topic_title} Notes, PDF and Test Plan Explained",
            f"How to Use {topic_title} Resources for Better Results",
            f"{topic_title} Course Details: What Should Be Included?",
        ],
    }
    return templates.get(comment_type, templates["Content request"])[:5]


def comment_idea_reason(comment_type: str, comments_count: int, unique_videos: int, keyword: str) -> str:
    reason_map = {
        "Question": "Audience is repeatedly asking for answers, so a Q&A/explainer video can capture direct search demand.",
        "Content request": "Viewers are directly requesting this topic, so demand is already validated in comments.",
        "Complaint": "Complaints reveal friction points; a problem-solving video can build trust and reduce objections.",
        "Confusion": "Confusion comments show the audience needs a simpler explanation or beginner-friendly walkthrough.",
        "Praise": "Positive comments show this angle already resonates, so a follow-up can extend a proven topic.",
        "Purchase intent": "Buying/joining language shows high commercial intent; clarify pricing, value, and next steps.",
        "Comparison": "Comparison comments show viewers are deciding between options, which is strong title demand.",
        "Exam anxiety": "Stress and score-related comments show emotional urgency; strategy content can perform well.",
        "Feature/course request": "Resource/course requests show viewers want something practical beyond the current video.",
        "General": "This keyword appears repeatedly in comments, so it can be tested as a future topic.",
    }
    return (
        f"{comments_count} comment(s) across {unique_videos} video(s) mention `{keyword}`. "
        + reason_map.get(comment_type, reason_map["General"])
    )


def comment_content_ideas(
    comments: pd.DataFrame,
    all_videos: Optional[pd.DataFrame] = None,
    top_n: int = 10,
) -> pd.DataFrame:
    if comments.empty:
        return pd.DataFrame(
            columns=[
                "idea_rank", "comment_type", "topic_keyword", "title_1", "title_2",
                "title_3", "title_4", "title_5", "long_tail_keywords", "demand_score",
                "comments", "videos", "avg_likes", "total_replies", "why_make_this",
                "sample_comment", "source_video", "video_url",
            ]
        )

    records = []
    useful_types = {
        "Question", "Content request", "Complaint", "Confusion", "Praise",
        "Purchase intent", "Comparison", "Exam anxiety", "Feature/course request",
    }
    priority_weight = {
        "Purchase intent": 20,
        "Content request": 18,
        "Feature/course request": 16,
        "Question": 14,
        "Confusion": 13,
        "Exam anxiety": 12,
        "Comparison": 11,
        "Complaint": 10,
        "Praise": 7,
        "General": 4,
    }

    for _, row in comments.iterrows():
        matched_types = [
            item.strip()
            for item in str(row.get("matched_types", row.get("comment_type", ""))).split(",")
            if item.strip()
        ]
        if not matched_types:
            matched_types = [row.get("comment_type", "General")]

        comment_types = [comment_type for comment_type in matched_types if comment_type in useful_types]
        if not comment_types:
            comment_types = [row.get("comment_type", "General")]

        keywords = comment_topic_keywords(row.get("comment_text", ""), row.get("video_title", ""))
        if not keywords:
            keywords = title_keywords(row.get("video_title", ""))[:3] or ["audience demand"]

        for comment_type in dict.fromkeys(comment_types):
            for keyword in keywords[:4]:
                records.append(
                    {
                        "comment_type": comment_type,
                        "topic_keyword": keyword,
                        "comment_id": row.get("comment_id", ""),
                        "video_id": row.get("video_id", ""),
                        "comment_likes": row.get("comment_likes", 0),
                        "reply_count": row.get("reply_count", 0),
                        "comment_text": row.get("comment_text", ""),
                        "video_title": row.get("video_title", ""),
                        "video_url": row.get("video_url", ""),
                    }
                )

    if not records:
        return pd.DataFrame()

    idea_source = pd.DataFrame(records)
    best_rows = idea_source.loc[
        idea_source.groupby(["comment_type", "topic_keyword"])["comment_likes"].idxmax()
    ][["comment_type", "topic_keyword", "comment_text", "video_title", "video_url"]]
    best_rows = best_rows.rename(
        columns={"comment_text": "sample_comment", "video_title": "source_video"}
    )

    grouped = (
        idea_source.groupby(["comment_type", "topic_keyword"])
        .agg(
            comments=("comment_id", "nunique"),
            videos=("video_id", "nunique"),
            avg_likes=("comment_likes", "mean"),
            total_replies=("reply_count", "sum"),
        )
        .round(2)
        .reset_index()
        .merge(best_rows, on=["comment_type", "topic_keyword"], how="left")
    )
    grouped["demand_score"] = grouped.apply(
        lambda row: round(
            row["comments"] * 6
            + row["videos"] * 10
            + row["avg_likes"] * 2
            + row["total_replies"] * 2
            + priority_weight.get(row["comment_type"], 4),
            1,
        ),
        axis=1,
    )
    grouped["related_channel_keywords"] = grouped["topic_keyword"].apply(
        lambda keyword: channel_context_keywords(keyword, all_videos, limit=8)
    )
    grouped["long_tail_keywords"] = grouped.apply(
        lambda row: ", ".join(
            comment_long_tail_keywords(
                row["comment_type"],
                row["topic_keyword"],
                row["related_channel_keywords"],
            )
        ),
        axis=1,
    )
    title_options = grouped.apply(
        lambda row: comment_title_options(
            row["comment_type"],
            row["topic_keyword"],
            row["related_channel_keywords"],
        ),
        axis=1,
    )
    for index in range(5):
        grouped[f"title_{index + 1}"] = title_options.apply(lambda titles: titles[index] if len(titles) > index else "")

    grouped["why_make_this"] = grouped.apply(
        lambda row: comment_idea_reason(
            row["comment_type"],
            int(row["comments"]),
            int(row["videos"]),
            row["topic_keyword"],
        ),
        axis=1,
    )
    grouped = grouped.sort_values(
        ["demand_score", "comments", "videos"],
        ascending=False,
    ).head(top_n)
    grouped.insert(0, "idea_rank", range(1, len(grouped) + 1))
    return grouped[
        [
            "idea_rank", "comment_type", "topic_keyword", "title_1", "title_2",
            "title_3", "title_4", "title_5", "long_tail_keywords", "demand_score",
            "comments", "videos", "avg_likes", "total_replies", "why_make_this",
            "sample_comment", "source_video", "video_url",
        ]
    ].reset_index(drop=True)


def parse_competitor_urls(raw_urls: str) -> List[str]:
    if not raw_urls.strip():
        return []

    channel_pattern = re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/[^\s,;]+|"
        r"(?:https?://)?(?:www\.)?youtube\.com/channel/UC[\w-]{22}|"
        r"@[A-Za-z0-9._-]+|"
        r"\bUC[\w-]{22}\b",
        re.IGNORECASE,
    )
    urls = channel_pattern.findall(raw_urls)

    if not urls:
        urls = re.split(r"[\s,;]+", raw_urls)

    unique_urls = []
    for url in urls:
        cleaned_url = url.strip().strip(".,;|)]}")
        if cleaned_url and cleaned_url not in unique_urls:
            unique_urls.append(cleaned_url)
    return unique_urls[:MAX_COMPETITORS]


def competitor_input_warning(raw_urls: str, parsed_urls: List[str]) -> Optional[str]:
    if not raw_urls.strip():
        return None

    rough_count = len([item for item in re.split(r"[\s,;]+", raw_urls) if "youtube.com" in item or item.startswith("@")])
    if rough_count > MAX_COMPETITORS:
        return f"Detected more than {MAX_COMPETITORS} competitor links. Only first {MAX_COMPETITORS} will be analysed."
    if raw_urls.strip() and not parsed_urls:
        return "No competitor links detected. Paste channel URLs like https://www.youtube.com/@ChannelName."
    return None


def merge_ctr_data(videos: pd.DataFrame, ctr_upload) -> pd.DataFrame:
    if ctr_upload is None or videos.empty:
        return videos

    ctr_df = pd.read_csv(ctr_upload)
    ctr_df.columns = [column.strip().lower() for column in ctr_df.columns]
    if "ctr" not in ctr_df.columns:
        st.warning("CTR CSV ignored because it does not contain a 'ctr' column.")
        return videos

    merged = videos.copy()
    if "video_id" in ctr_df.columns:
        merged = merged.merge(ctr_df[["video_id", "ctr"]], on="video_id", how="left", suffixes=("", "_uploaded"))
    elif "title" in ctr_df.columns:
        merged = merged.merge(ctr_df[["title", "ctr"]], on="title", how="left", suffixes=("", "_uploaded"))
    else:
        st.warning("CTR CSV ignored. Add either 'video_id' or 'title' column with 'ctr'.")
        return videos

    merged["ctr"] = merged["ctr_uploaded"].combine_first(merged["ctr"])
    return merged.drop(columns=[column for column in ["ctr_uploaded"] if column in merged.columns])


def keyword_table(videos: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    records = []
    for _, row in videos.iterrows():
        for keyword in title_keywords(row["title"]):
            records.append(
                {
                    "keyword": keyword,
                    "views": row["views"],
                    "views_per_day": row["views_per_day"],
                    "title": row["title"],
                    "channel": row["channel"],
                }
            )

    if not records:
        return pd.DataFrame(columns=["keyword", "uses", "avg_views", "avg_views_per_day", "best_title"])

    keyword_df = pd.DataFrame(records)
    grouped = (
        keyword_df.groupby("keyword")
        .agg(
            uses=("keyword", "size"),
            channels=("channel", "nunique"),
            avg_views=("views", "mean"),
            median_views=("views", "median"),
            avg_views_per_day=("views_per_day", "mean"),
            best_title=("title", lambda values: values.iloc[0]),
        )
        .round(2)
        .reset_index()
    )
    return grouped.sort_values(["uses", "avg_views"], ascending=False).head(top_n)


def hook_table(videos: pd.DataFrame, top_n: int = 25) -> pd.DataFrame:
    records = []
    for _, row in videos.iterrows():
        for hook in title_hook_words(row["title"]):
            records.append(
                {
                    "hook_keyword": hook,
                    "views": row["views"],
                    "views_per_day": row["views_per_day"],
                    "title": row["title"],
                    "channel": row["channel"],
                }
            )

    if not records:
        return pd.DataFrame(columns=["hook_keyword", "uses", "avg_views", "avg_views_per_day", "best_title"])

    hook_df = pd.DataFrame(records)
    grouped = (
        hook_df.groupby("hook_keyword")
        .agg(
            uses=("hook_keyword", "size"),
            channels=("channel", "nunique"),
            avg_views=("views", "mean"),
            avg_views_per_day=("views_per_day", "mean"),
            best_title=("title", lambda values: values.iloc[0]),
        )
        .round(2)
        .reset_index()
    )
    return grouped.sort_values(["avg_views", "uses"], ascending=False).head(top_n)


def high_view_hook_videos(videos: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    if videos.empty:
        return pd.DataFrame(
            columns=["channel", "title", "video_type", "views", "hook_keywords", "keywords", "url"]
        )

    columns = ["channel", "title", "video_type", "views", "hook_keywords", "keywords", "url"]
    return (
        dedupe_videos(videos)
        .sort_values("views", ascending=False)
        .head(top_n)[columns]
        .reset_index(drop=True)
    )


def tag_table(videos: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    records = []
    for _, row in videos.iterrows():
        raw_tags = str(row.get("youtube_tags", ""))
        source_tags = [tag.strip().lower() for tag in raw_tags.split(",") if tag.strip()]
        if not source_tags:
            source_tags = title_keywords(row["title"])
        for tag in source_tags:
            records.append(
                {
                    "search_tag": tag,
                    "views": row["views"],
                    "views_per_day": row["views_per_day"],
                    "channel": row["channel"],
                }
            )

    if not records:
        return pd.DataFrame(columns=["search_tag", "uses", "avg_views_per_day"])

    tags_df = pd.DataFrame(records)
    return (
        tags_df.groupby("search_tag")
        .agg(
            uses=("search_tag", "size"),
            channels=("channel", "nunique"),
            avg_views=("views", "mean"),
            avg_views_per_day=("views_per_day", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values(["avg_views_per_day", "uses"], ascending=False)
        .head(top_n)
    )


def bucket_table(videos: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        videos.groupby(column)
        .agg(
            videos=("video_id", "count"),
            avg_views=("views", "mean"),
            median_views=("views", "median"),
            avg_views_per_day=("views_per_day", "mean"),
        )
        .round(2)
        .sort_values("avg_views_per_day", ascending=False)
        .reset_index()
    )


def feature_table(videos: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in ["has_number", "has_question", "has_year"]:
        summary = (
            videos.groupby(feature)
            .agg(
                videos=("video_id", "count"),
                avg_views=("views", "mean"),
                avg_views_per_day=("views_per_day", "mean"),
            )
            .round(2)
            .reset_index()
        )
        summary.insert(0, "feature", feature)
        summary = summary.rename(columns={feature: "value"})
        rows.append(summary)
    return pd.concat(rows, ignore_index=True)


def channel_keyword_set(videos: pd.DataFrame, top_n: int = 30) -> set:
    if videos.empty:
        return set()
    return set(keyword_table(videos, top_n=top_n)["keyword"].tolist())


def market_demand_keywords(all_videos: pd.DataFrame, top_n: int = 30) -> set:
    if all_videos.empty:
        return set()
    table = keyword_table(all_videos, top_n=top_n)
    return set(table[table["channels"] >= 2]["keyword"].tolist() or table["keyword"].tolist()[:10])


def explain_video_performance(row: pd.Series, channel_videos: pd.DataFrame, all_videos: pd.DataFrame) -> str:
    channel_median = channel_videos["views"].median()
    channel_top_25 = channel_videos["views"].quantile(0.75)
    market_keywords = market_demand_keywords(all_videos)
    row_keywords = set(title_keywords(row["title"]))
    row_hooks = title_hook_words(row["title"])
    reasons = []

    if row["views"] >= channel_top_25:
        reasons.append("channel ke top-view range me hai")
    elif row["views"] >= channel_median:
        reasons.append("channel median se better perform kar raha hai")

    shared_keywords = sorted(row_keywords & market_keywords)
    if shared_keywords:
        reasons.append("market-demand keywords use hue: " + ", ".join(shared_keywords[:4]))

    if row_hooks:
        reasons.append("strong hook words/signals: " + ", ".join(row_hooks[:4]))

    best_type = bucket_table(all_videos, "video_type").iloc[0]["video_type"]
    if row["video_type"] == best_type:
        reasons.append(f"{row['video_type']} format current dataset me strong perform kar raha hai")

    similar_keyword_videos = all_videos[
        all_videos["title"].apply(lambda title: bool(set(title_keywords(title)) & row_keywords))
    ]
    if len(dedupe_videos(similar_keyword_videos)) >= 5:
        reasons.append("same/similar topic multiple channels par repeat ho raha hai, demand signal milta hai")

    if not reasons:
        reasons.append("performance normal range me hai; clear demand signal weak hai")

    return "; ".join(reasons)


def latest_10_reason_table(channel_videos: pd.DataFrame, all_videos: pd.DataFrame) -> pd.DataFrame:
    if channel_videos.empty:
        return pd.DataFrame(
            columns=["channel", "title", "video_type", "upload_date", "views", "performance_level", "possible_reason", "url"]
        )

    latest = dedupe_videos(channel_videos).sort_values("published_at", ascending=False).head(10).copy()
    if "url" not in latest.columns:
        latest["url"] = ""
    channel_median = channel_videos["views"].median()
    channel_top_25 = channel_videos["views"].quantile(0.75)

    def performance_level(views: int) -> str:
        if views >= channel_top_25:
            return "High"
        if views >= channel_median:
            return "Above average"
        return "Normal/low"

    latest["performance_level"] = latest["views"].apply(performance_level)
    latest["possible_reason"] = latest.apply(
        lambda row: explain_video_performance(row, channel_videos, all_videos),
        axis=1,
    )

    return latest[
        ["channel", "title", "video_type", "upload_date", "views", "performance_level", "possible_reason", "url"]
    ]


def weekly_upload_frequency(videos: pd.DataFrame) -> pd.DataFrame:
    if videos.empty:
        return pd.DataFrame(columns=["channel", "week", "uploads", "shorts", "long_videos", "avg_views"])

    df = dedupe_videos(videos).copy()
    published = pd.to_datetime(df["published_at"], utc=True)
    iso = published.dt.isocalendar()
    df["week"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    df["is_shorts"] = df["video_type"].eq("Shorts")
    df["is_long"] = df["video_type"].eq("Long video")

    return (
        df.groupby(["channel", "week"])
        .agg(
            uploads=("video_id", "count"),
            shorts=("is_shorts", "sum"),
            long_videos=("is_long", "sum"),
            avg_views=("views", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values(["week", "uploads"], ascending=[False, False])
    )


def upload_frequency_summary(videos: pd.DataFrame) -> pd.DataFrame:
    weekly = weekly_upload_frequency(videos)
    if weekly.empty:
        return pd.DataFrame(columns=["channel", "weeks_active", "avg_uploads_per_week", "max_uploads_in_week", "avg_views"])

    return (
        weekly.groupby("channel")
        .agg(
            weeks_active=("week", "nunique"),
            avg_uploads_per_week=("uploads", "mean"),
            max_uploads_in_week=("uploads", "max"),
            avg_views=("avg_views", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("avg_uploads_per_week", ascending=False)
    )


def topic_relevance_table(all_videos: pd.DataFrame, video_description: str) -> pd.DataFrame:
    description_terms = set(description_keywords(video_description))
    rows = []

    for channel, channel_rows in dedupe_videos(all_videos).groupby("channel"):
        top_keywords = keyword_table(channel_rows, top_n=20)["keyword"].tolist()
        keyword_set = set(top_keywords)
        overlap = sorted(description_terms & keyword_set)
        score = round((len(overlap) / max(len(description_terms), 1)) * 100, 2) if description_terms else 0
        rows.append(
            {
                "channel": channel,
                "topic_relevance_score": score,
                "matching_keywords": ", ".join(overlap[:10]),
                "channel_top_keywords": ", ".join(top_keywords[:10]),
            }
        )

    return pd.DataFrame(rows).sort_values("topic_relevance_score", ascending=False)


def classify_trend_topic(title: str, tags: str = "", category: str = "") -> str:
    text = f"{title} {tags}".lower()
    topic_scores = {}

    for topic, keywords in TREND_TOPIC_KEYWORDS.items():
        topic_scores[topic] = sum(1 for keyword in keywords if keyword in text)

    best_topic = max(topic_scores, key=topic_scores.get)
    if topic_scores[best_topic] > 0:
        return best_topic

    if category == "Academic":
        return "Academic Other"
    if category == "Non-academic / Strategy":
        return "Strategy Other"
    return "Other"


def percentage_growth(current: float, previous: float) -> float:
    if pd.isna(previous) or previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)


def normalize_series_score(series: pd.Series) -> pd.Series:
    clean = series.replace([float("inf"), float("-inf")], pd.NA).fillna(0).astype(float)
    min_value = clean.min()
    max_value = clean.max()
    if min_value == max_value:
        return pd.Series([50.0] * len(clean), index=clean.index)
    return ((clean - min_value) / (max_value - min_value) * 100).round(2)


def trend_status_label(score: float) -> str:
    if score >= 80:
        return "Rapidly rising"
    if score >= 65:
        return "Growing"
    if score >= 45:
        return "Stable"
    if score >= 25:
        return "Declining"
    return "Weak / saturated"


def trend_market_signal(row: pd.Series) -> str:
    frequency = row["frequency_growth_pct"]
    velocity = row["views_velocity_growth_pct"]
    if frequency > 50 and velocity < -20:
        return "Possible saturation"
    if frequency > 20 and velocity > 20:
        return "Healthy growth"
    if frequency < -20 and velocity < -20:
        return "Losing momentum"
    return "Normal"


def detect_youtube_trends(
    videos: pd.DataFrame,
    current_window_days: int = 30,
    minimum_current_videos: int = 1,
    current_start_utc: Optional[datetime] = None,
    current_end_utc: Optional[datetime] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if videos.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    data = prepare_video_frame(add_content_categories(dedupe_videos(videos))).copy()
    required_columns = {"title", "published_at", "views"}
    missing_columns = sorted(required_columns - set(data.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    data["published_at"] = pd.to_datetime(data["published_at"], utc=True, errors="coerce")
    data = data.dropna(subset=["published_at"])
    if data.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    now_utc = pd.Timestamp.now(tz="UTC")
    data["video_age_days"] = ((now_utc - data["published_at"]).dt.total_seconds() / 86400).clip(lower=1)
    data["views_per_day"] = (data["views"] / data["video_age_days"]).round(2)
    median_views_day = max(float(data["views_per_day"].median()), 1.0)
    data["outlier_score"] = (data["views_per_day"] / median_views_day).round(2)
    data["trend_topic"] = data.apply(
        lambda row: classify_trend_topic(
            row["title"],
            row.get("youtube_tags", ""),
            row.get("content_category", ""),
        ),
        axis=1,
    )

    if current_start_utc is not None and current_end_utc is not None:
        current_start = pd.Timestamp(current_start_utc).tz_convert("UTC")
        current_end = pd.Timestamp(current_end_utc).tz_convert("UTC")
        window_days = max((current_end - current_start).days, 1)
    else:
        current_end = now_utc
        current_start = now_utc - pd.Timedelta(days=current_window_days)
        window_days = current_window_days

    previous_start = current_start - pd.Timedelta(days=window_days)
    current_df = data[(data["published_at"] >= current_start) & (data["published_at"] < current_end)].copy()
    previous_df = data[(data["published_at"] >= previous_start) & (data["published_at"] < current_start)].copy()

    current_stats = (
        current_df.groupby("trend_topic")
        .agg(
            current_video_count=("video_id", "count"),
            current_median_views_day=("views_per_day", "median"),
            current_avg_views_day=("views_per_day", "mean"),
            current_avg_outlier_score=("outlier_score", "mean"),
            current_outliers=("outlier_score", lambda values: (values >= 2).sum()),
            current_super_outliers=("outlier_score", lambda values: (values >= 4).sum()),
            current_total_views=("views", "sum"),
            channels_covering_topic=("channel", "nunique"),
        )
        .reset_index()
    )

    previous_stats = (
        previous_df.groupby("trend_topic")
        .agg(
            previous_video_count=("video_id", "count"),
            previous_median_views_day=("views_per_day", "median"),
            previous_avg_views_day=("views_per_day", "mean"),
            previous_avg_outlier_score=("outlier_score", "mean"),
            previous_outliers=("outlier_score", lambda values: (values >= 2).sum()),
            previous_total_views=("views", "sum"),
        )
        .reset_index()
    )

    if current_stats.empty and previous_stats.empty:
        return pd.DataFrame(), current_df, previous_df

    trends = current_stats.merge(previous_stats, on="trend_topic", how="outer")
    numeric_columns = trends.select_dtypes(include="number").columns
    trends[numeric_columns] = trends[numeric_columns].fillna(0)

    trends["frequency_growth_pct"] = trends.apply(
        lambda row: percentage_growth(row["current_video_count"], row["previous_video_count"]),
        axis=1,
    )
    trends["views_velocity_growth_pct"] = trends.apply(
        lambda row: percentage_growth(row["current_median_views_day"], row["previous_median_views_day"]),
        axis=1,
    )
    trends["outlier_growth_pct"] = trends.apply(
        lambda row: percentage_growth(row["current_outliers"], row["previous_outliers"]),
        axis=1,
    )

    trends["frequency_score"] = normalize_series_score(trends["frequency_growth_pct"].clip(-100, 500))
    trends["velocity_score"] = normalize_series_score(trends["views_velocity_growth_pct"].clip(-100, 500))
    trends["outlier_score_component"] = normalize_series_score(trends["outlier_growth_pct"].clip(-100, 500))
    trends["adoption_score"] = normalize_series_score(trends["channels_covering_topic"])

    trends["trend_score"] = (
        trends["frequency_score"] * 0.30
        + trends["velocity_score"] * 0.35
        + trends["outlier_score_component"] * 0.20
        + trends["adoption_score"] * 0.15
    ).round(1)
    trends["trend_status"] = trends["trend_score"].apply(trend_status_label)
    trends["market_signal"] = trends.apply(trend_market_signal, axis=1)
    trends = trends[trends["current_video_count"] >= minimum_current_videos]
    trends = add_trend_keyword_columns(trends, current_df)

    return trends.sort_values("trend_score", ascending=False), current_df, previous_df


def trend_keyword_table(current_df: pd.DataFrame, trend_topics: Optional[List[str]] = None) -> pd.DataFrame:
    if current_df.empty:
        return pd.DataFrame(
            columns=[
                "trend_topic", "keyword", "trending_videos", "total_views",
                "avg_views_per_day", "outlier_videos", "best_video", "best_video_url",
            ]
        )

    records = []
    topic_df = current_df.copy()
    if trend_topics is not None:
        topic_df = topic_df[topic_df["trend_topic"].isin(trend_topics)]

    for _, row in topic_df.iterrows():
        keywords = title_keywords(row["title"])
        if row.get("youtube_tags"):
            keywords.extend(words_from_text(str(row.get("youtube_tags", ""))))
        unique_keywords = []
        for keyword in keywords:
            if keyword not in unique_keywords:
                unique_keywords.append(keyword)

        for keyword in unique_keywords:
            records.append(
                {
                    "trend_topic": row["trend_topic"],
                    "keyword": keyword,
                    "video_id": row["video_id"],
                    "views": row["views"],
                    "views_per_day": row["views_per_day"],
                    "is_outlier": row["outlier_score"] >= 2,
                    "title": row["title"],
                    "url": row["url"],
                }
            )

    if not records:
        return pd.DataFrame(
            columns=[
                "trend_topic", "keyword", "trending_videos", "total_views",
                "avg_views_per_day", "outlier_videos", "best_video", "best_video_url",
            ]
        )

    keyword_df = pd.DataFrame(records)
    best_rows = keyword_df.loc[keyword_df.groupby(["trend_topic", "keyword"])["views"].idxmax()]
    best_rows = best_rows[["trend_topic", "keyword", "title", "url"]].rename(
        columns={"title": "best_video", "url": "best_video_url"}
    )
    grouped = (
        keyword_df.groupby(["trend_topic", "keyword"])
        .agg(
            trending_videos=("video_id", "nunique"),
            total_views=("views", "sum"),
            avg_views_per_day=("views_per_day", "mean"),
            outlier_videos=("is_outlier", "sum"),
        )
        .round(2)
        .reset_index()
        .merge(best_rows, on=["trend_topic", "keyword"], how="left")
    )
    return grouped.sort_values(["trending_videos", "total_views"], ascending=False)


def add_trend_keyword_columns(trends: pd.DataFrame, current_df: pd.DataFrame) -> pd.DataFrame:
    if trends.empty:
        return trends

    keyword_df = trend_keyword_table(current_df, trends["trend_topic"].tolist())
    trends = trends.copy()
    trends["trending_keyword_count"] = 0
    trends["top_7_trending_keywords"] = ""

    for topic in trends["trend_topic"]:
        topic_keywords = keyword_df[keyword_df["trend_topic"] == topic]
        keyword_count = len(topic_keywords)
        top_keywords = [
            f"{row.keyword} ({int(row.trending_videos)})"
            for row in topic_keywords.head(7).itertuples()
        ]
        while len(top_keywords) < 7:
            top_keywords.append("-")

        trends.loc[trends["trend_topic"] == topic, "trending_keyword_count"] = keyword_count
        trends.loc[trends["trend_topic"] == topic, "top_7_trending_keywords"] = ", ".join(top_keywords[:7])

    return trends


def classify_content_category(title: str, tags: str = "") -> str:
    words = set(words_from_text(f"{title} {tags}"))
    academic_score = len(words & ACADEMIC_KEYWORDS)
    strategy_score = len(words & STRATEGY_KEYWORDS)

    if academic_score > strategy_score and academic_score > 0:
        return "Academic"
    if strategy_score > 0:
        return "Non-academic / Strategy"
    return "Other / mixed"


def content_topic_keywords(title: str, tags: str = "", max_keywords: int = 3) -> str:
    keywords = []
    for keyword in words_from_text(f"{title} {tags}"):
        if keyword not in keywords:
            keywords.append(keyword)
        if len(keywords) == max_keywords:
            break
    return ", ".join(keywords)


def add_content_categories(videos: pd.DataFrame) -> pd.DataFrame:
    if videos.empty:
        return videos

    df = videos.copy()
    if "youtube_tags" not in df.columns:
        df["youtube_tags"] = ""
    df["content_category"] = df.apply(
        lambda row: classify_content_category(row["title"], row.get("youtube_tags", "")),
        axis=1,
    )
    df["topic_keywords"] = df.apply(
        lambda row: content_topic_keywords(row["title"], row.get("youtube_tags", "")),
        axis=1,
    )
    return df


def recent_window_videos(videos: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    if videos.empty:
        return videos

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    df = dedupe_videos(add_content_categories(videos)).copy()
    published = pd.to_datetime(df["published_at"], utc=True)
    return df[published >= cutoff].reset_index(drop=True)


def content_gap_summary_sheet(videos: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    recent = recent_window_videos(videos, days)
    if recent.empty:
        return pd.DataFrame(
            columns=["channel", "content_category", "videos", "total_views", "avg_views", "best_video", "best_video_views"]
        )

    best_rows = recent.sort_values("views", ascending=False).drop_duplicates(["channel", "content_category"])
    grouped = (
        recent.groupby(["channel", "content_category"])
        .agg(
            videos=("video_id", "count"),
            total_views=("views", "sum"),
            avg_views=("views", "mean"),
        )
        .round(2)
        .reset_index()
    )
    best_lookup = best_rows.set_index(["channel", "content_category"])[["title", "views"]].to_dict("index")
    grouped["best_video"] = grouped.apply(
        lambda row: best_lookup.get((row["channel"], row["content_category"]), {}).get("title", ""),
        axis=1,
    )
    grouped["best_video_views"] = grouped.apply(
        lambda row: best_lookup.get((row["channel"], row["content_category"]), {}).get("views", 0),
        axis=1,
    )
    return grouped.sort_values(["content_category", "total_views"], ascending=[True, False])


def content_gap_pivot_sheet(videos: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    summary = content_gap_summary_sheet(videos, days)
    if summary.empty:
        return pd.DataFrame(columns=["channel"])

    pivot = summary.pivot_table(
        index="channel",
        columns="content_category",
        values="videos",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    for category in ["Academic", "Non-academic / Strategy", "Other / mixed"]:
        if category not in pivot.columns:
            pivot[category] = 0

    totals = (
        recent_window_videos(videos, days)
        .groupby("channel")
        .agg(total_videos=("video_id", "count"), total_views=("views", "sum"), avg_views=("views", "mean"))
        .round(2)
        .reset_index()
    )
    return pivot.merge(totals, on="channel", how="left").sort_values("total_videos", ascending=False)


def content_gap_video_sheet(videos: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    recent = recent_window_videos(videos, days)
    if recent.empty:
        return pd.DataFrame(
            columns=["channel", "title", "content_category", "topic_keywords", "video_type", "upload_date", "views", "url"]
        )

    columns = [
        "channel", "title", "content_category", "topic_keywords", "video_type",
        "upload_date", "views", "views_per_day", "url",
    ]
    return recent.sort_values("views", ascending=False)[columns].reset_index(drop=True)


def content_topic_sheet(videos: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    recent = recent_window_videos(videos, days)
    records = []

    for _, row in recent.iterrows():
        for keyword in title_keywords(row["title"])[:6]:
            records.append(
                {
                    "channel": row["channel"],
                    "content_category": row["content_category"],
                    "topic_keyword": keyword,
                    "views": row["views"],
                    "title": row["title"],
                    "url": row["url"],
                }
            )

    if not records:
        return pd.DataFrame(
            columns=["channel", "content_category", "topic_keyword", "videos", "total_views", "avg_views", "best_video", "best_video_url"]
        )

    keyword_df = pd.DataFrame(records)
    grouped = (
        keyword_df.groupby(["channel", "content_category", "topic_keyword"])
        .agg(
            videos=("topic_keyword", "size"),
            total_views=("views", "sum"),
            avg_views=("views", "mean"),
            best_video=("title", lambda values: values.iloc[0]),
            best_video_url=("url", lambda values: values.iloc[0]),
        )
        .round(2)
        .reset_index()
    )
    return grouped.sort_values(["total_views", "videos"], ascending=False)


def content_gap_opportunities(own_channel_title: str, all_videos: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    topic_sheet = content_topic_sheet(all_videos, days)
    if topic_sheet.empty:
        return pd.DataFrame(
            columns=["content_category", "topic_keyword", "competitor_videos", "competitor_total_views", "competitor_channels", "best_competitor_video"]
        )

    own_topics = set(topic_sheet[topic_sheet["channel"] == own_channel_title]["topic_keyword"].tolist())
    competitor_topics = topic_sheet[topic_sheet["channel"] != own_channel_title]
    competitor_topics = competitor_topics[~competitor_topics["topic_keyword"].isin(own_topics)]

    if competitor_topics.empty:
        return pd.DataFrame(
            columns=["content_category", "topic_keyword", "competitor_videos", "competitor_total_views", "competitor_channels", "best_competitor_video"]
        )

    return (
        competitor_topics.groupby(["content_category", "topic_keyword"])
        .agg(
            competitor_videos=("videos", "sum"),
            competitor_total_views=("total_views", "sum"),
            competitor_channels=("channel", "nunique"),
            best_competitor_video=("best_video", lambda values: values.iloc[0]),
            best_competitor_url=("best_video_url", lambda values: values.iloc[0]),
        )
        .reset_index()
        .sort_values(["competitor_total_views", "competitor_videos"], ascending=False)
        .head(30)
    )


def normalize_score(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return round(min(max(value / max_value, 0), 1) * 100, 2)


def text_contains_intent(text: str, intent: str) -> bool:
    text_words = set(words_from_text(text))
    intent_words = set(words_from_text(intent))
    return bool(text_words & intent_words)


def parse_seed_intents(seed_text: str) -> List[str]:
    intents = []
    for part in re.split(r"[\n,;|]+", seed_text):
        clean = " ".join(part.strip().split())
        if clean and clean.lower() not in {intent.lower() for intent in intents}:
            intents.append(clean)
    return intents


def candidate_search_intents(
    own_channel_title: str,
    all_videos: pd.DataFrame,
    video_description: str,
    extra_seed_text: str,
    limit: int = 12,
) -> List[str]:
    all_videos = prepare_video_frame(all_videos)
    seeds = []

    for intent in parse_seed_intents(extra_seed_text):
        if intent not in seeds:
            seeds.append(intent)

    description_text = " ".join(video_description.strip().split())
    if description_text:
        description_phrase = " ".join(words_from_text(description_text)[:5])
        if description_phrase and description_phrase not in seeds:
            seeds.append(description_phrase)

    for keyword in description_keywords(video_description):
        if keyword not in seeds:
            seeds.append(keyword)

    opportunities = content_gap_opportunities(own_channel_title, all_videos)
    if not opportunities.empty:
        for keyword in opportunities["topic_keyword"].tolist():
            if keyword not in seeds:
                seeds.append(keyword)

    for keyword in keyword_table(all_videos, top_n=30)["keyword"].tolist():
        if keyword not in seeds:
            seeds.append(keyword)

    intents = []
    for seed in seeds:
        clean_seed = seed.strip()
        if not clean_seed or clean_seed in intents:
            continue
        intents.append(clean_seed)
        if len(intents) >= limit:
            break

    return intents


@st.cache_data(show_spinner=False, ttl=1800)
def search_market_video_ids(
    query: str,
    api_key: str,
    published_after: str,
    max_results: int,
    order: str,
    region_code: str,
    relevance_language: str,
) -> List[str]:
    data = request_youtube(
        "search",
        api_key,
        part="snippet",
        q=query,
        type="video",
        order=order,
        maxResults=max_results,
        publishedAfter=published_after,
        regionCode=region_code,
        relevanceLanguage=relevance_language,
        safeSearch="none",
    )
    return [
        item["id"]["videoId"]
        for item in data.get("items", [])
        if item.get("id", {}).get("videoId")
    ]


def prepare_video_frame(videos: pd.DataFrame) -> pd.DataFrame:
    if videos.empty:
        return videos

    df = videos.copy()
    if "published_at" in df.columns and "video_age_days" not in df.columns:
        published = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df["video_age_days"] = (
            (datetime.now(timezone.utc) - published).dt.total_seconds() / 86400
        ).fillna(1).clip(lower=1).round(1)
    if "source_channel" not in df.columns:
        df["source_channel"] = df.get("channel", "")
    if "source_channel_id" not in df.columns:
        df["source_channel_id"] = df.get("channel_id", "")
    if "channel" not in df.columns:
        df["channel"] = df.get("source_channel", "")
    if "url" not in df.columns and "video_id" in df.columns:
        df["url"] = df["video_id"].apply(lambda video_id: f"https://www.youtube.com/watch?v={video_id}")
    if "views_per_day" not in df.columns and {"views", "video_age_days"}.issubset(df.columns):
        df["views_per_day"] = (df["views"] / df["video_age_days"].clip(lower=1)).round(2)
    if "youtube_tags" not in df.columns:
        df["youtube_tags"] = ""
    if "keywords" not in df.columns and "title" in df.columns:
        df["keywords"] = df["title"].apply(lambda title: ", ".join(title_keywords(title)))
    if "hook_keywords" not in df.columns and "title" in df.columns:
        df["hook_keywords"] = df["title"].apply(lambda title: ", ".join(title_hook_words(title)))
    if "video_type" not in df.columns and "duration_seconds" in df.columns:
        df["video_type"] = df["duration_seconds"].apply(video_type)
    if "upload_date" not in df.columns and "published_at" in df.columns:
        df["upload_date"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce").dt.date.astype(str)

    return df


def search_market_videos(
    intents: List[str],
    api_key: str,
    days: int,
    max_results_per_intent: int,
    order: str,
    region_code: str,
    relevance_language: str,
) -> Tuple[pd.DataFrame, List[str]]:
    published_after = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    frames = []
    errors = []

    for intent in intents:
        try:
            video_ids = search_market_video_ids(
                intent,
                api_key,
                published_after,
                max_results_per_intent,
                order,
                region_code,
                relevance_language,
            )
        except Exception as error:
            errors.append(f"{intent}: {error}")
            continue

        if not video_ids:
            continue

        try:
            details = fetch_video_details(tuple(video_ids), api_key)
        except Exception as error:
            errors.append(f"{intent}: {error}")
            continue

        if details.empty:
            continue

        details["search_intent"] = intent
        frames.append(details)

    if not frames:
        return pd.DataFrame(), errors

    market = prepare_video_frame(dedupe_videos(pd.concat(frames, ignore_index=True)))
    if "source_channel" in market.columns:
        market["channel"] = market["source_channel"]
    else:
        market["channel"] = ""
    return add_content_categories(market), errors


def score_search_intents(
    own_channel_title: str,
    all_videos: pd.DataFrame,
    market_videos: pd.DataFrame,
    days: int,
) -> pd.DataFrame:
    if market_videos.empty:
        return pd.DataFrame(
            columns=[
                "search_intent", "opportunity_score", "competitor_performance", "topic_momentum",
                "outlier_frequency", "audience_interest", "your_content_gap", "recency",
            ]
        )

    all_videos = prepare_video_frame(all_videos)
    market_videos = prepare_video_frame(market_videos)
    scored_rows = []
    own_videos = all_videos[all_videos["channel"] == own_channel_title]
    competitor_videos = all_videos[all_videos["channel"] != own_channel_title]
    max_market_views_per_day = max(float(market_videos["views_per_day"].max()), 1)
    max_market_views = max(float(market_videos["views"].max()), 1)

    for intent, intent_rows in market_videos.groupby("search_intent"):
        intent_rows = dedupe_videos(intent_rows)
        own_covered = own_videos["title"].apply(lambda title: text_contains_intent(title, intent)).sum()
        competitor_matches = competitor_videos[
            competitor_videos["title"].apply(lambda title: text_contains_intent(title, intent))
        ]
        competitor_avg_views = float(competitor_matches["views"].mean()) if not competitor_matches.empty else 0.0
        competitor_performance = normalize_score(
            competitor_avg_views,
            max(float(all_videos["views"].quantile(0.90)), 1),
        )

        avg_views_per_day = float(intent_rows["views_per_day"].mean())
        topic_momentum = normalize_score(avg_views_per_day, max_market_views_per_day)

        median_views = max(float(intent_rows["views"].median()), 1)
        outliers = intent_rows[intent_rows["views"] >= median_views * 2]
        outlier_frequency = round((len(outliers) / max(len(intent_rows), 1)) * 100, 2)

        audience_interest = normalize_score(float(intent_rows["views"].mean()), max_market_views)
        your_content_gap = 100.0 if own_covered == 0 else max(0.0, 70.0 - (own_covered * 20.0))

        fresh_count = (intent_rows["video_age_days"] <= min(days, 14)).sum()
        recency = round((fresh_count / max(len(intent_rows), 1)) * 100, 2)

        opportunity_score = round(
            competitor_performance * 0.15
            + topic_momentum * 0.25
            + outlier_frequency * 0.15
            + audience_interest * 0.20
            + your_content_gap * 0.15
            + recency * 0.10,
            2,
        )

        best_video = intent_rows.sort_values("views", ascending=False).iloc[0]
        scored_rows.append(
            {
                "search_intent": intent,
                "opportunity_score": opportunity_score,
                "competitor_performance": competitor_performance,
                "topic_momentum": topic_momentum,
                "outlier_frequency": outlier_frequency,
                "audience_interest": audience_interest,
                "your_content_gap": your_content_gap,
                "recency": recency,
                "market_videos_found": len(intent_rows),
                "own_channel_covered_count": int(own_covered),
                "competitor_covered_count": len(competitor_matches),
                "best_market_video": best_video["title"],
                "best_market_channel": best_video.get("source_channel", best_video.get("channel", "")),
                "best_market_views": int(best_video["views"]),
                "best_market_url": best_video["url"],
            }
        )

    return pd.DataFrame(scored_rows).sort_values("opportunity_score", ascending=False)


def market_video_evidence_sheet(market_videos: pd.DataFrame) -> pd.DataFrame:
    market_videos = prepare_video_frame(market_videos)
    if market_videos.empty:
        return pd.DataFrame(
            columns=["search_intent", "title", "source_channel", "video_type", "upload_date", "views", "views_per_day", "url"]
        )

    columns = [
        "search_intent", "title", "source_channel", "video_type", "upload_date",
        "views", "views_per_day", "keywords", "hook_keywords", "url",
    ]
    return market_videos.sort_values(["search_intent", "views"], ascending=[True, False])[columns]


def parse_niche_keywords(raw_keywords: str) -> List[str]:
    keywords = []
    for part in re.split(r"[\n,;|]+", str(raw_keywords)):
        clean = " ".join(part.strip().lower().split())
        if clean and clean not in keywords:
            keywords.append(clean)
    return keywords


def infer_niche_keywords(videos: pd.DataFrame, limit: int = 18) -> List[str]:
    if videos.empty:
        return []

    generic_keywords = {
        "complete", "guide", "latest", "best", "strategy", "tips", "tricks",
        "video", "videos", "class", "classes", "live", "session", "update",
        "new", "important", "today", "free",
    }
    inferred = []

    try:
        keywords = keyword_table(prepare_video_frame(videos), top_n=60)["keyword"].tolist()
    except Exception:
        keywords = []

    for keyword in keywords:
        clean = keyword.lower().strip()
        if clean in generic_keywords or len(clean) < 3:
            continue
        if clean not in inferred:
            inferred.append(clean)
        if len(inferred) >= limit:
            break

    if len(inferred) < limit:
        tag_counts = Counter()
        for tags in videos.get("youtube_tags", pd.Series(dtype="string")).fillna(""):
            for tag in str(tags).split(","):
                clean = " ".join(tag.strip().lower().split())
                if clean and clean not in generic_keywords and len(clean) >= 3:
                    tag_counts[clean] += 1
        for keyword, _ in tag_counts.most_common(limit):
            if keyword not in inferred:
                inferred.append(keyword)
            if len(inferred) >= limit:
                break

    return inferred[:limit]


def text_matches_niche(text: str, niche_keywords: List[str]) -> bool:
    if not niche_keywords:
        return True

    clean_text = f" {str(text).lower()} "
    text_words = set(words_from_text(clean_text))
    for keyword in niche_keywords:
        keyword = keyword.lower().strip()
        if not keyword:
            continue
        keyword_words = set(words_from_text(keyword))
        if " " in keyword and keyword in clean_text:
            return True
        if keyword_words and keyword_words <= text_words:
            return True
    return False


def filter_videos_by_niche(videos: pd.DataFrame, niche_keywords: List[str]) -> pd.DataFrame:
    if videos.empty or not niche_keywords:
        return videos.copy()

    df = prepare_video_frame(videos).copy()
    mask = df.apply(
        lambda row: text_matches_niche(
            f"{row.get('title', '')} {row.get('keywords', '')} {row.get('youtube_tags', '')} {row.get('content_category', '')}",
            niche_keywords,
        ),
        axis=1,
    )
    return df[mask].reset_index(drop=True)


def filter_market_scores_by_niche(market_scores: pd.DataFrame, niche_keywords: List[str]) -> pd.DataFrame:
    if market_scores.empty or not niche_keywords:
        return market_scores.copy()

    return market_scores[
        market_scores["search_intent"].apply(lambda intent: text_matches_niche(intent, niche_keywords))
    ].reset_index(drop=True)


def topic_best_video(videos: pd.DataFrame, topic: str) -> Dict:
    if videos.empty:
        return {"title": "", "url": "", "views": 0, "views_per_day": 0.0}

    topic_words = set(words_from_text(topic))
    matches = videos[
        videos.apply(
            lambda row: bool(
                topic_words
                & set(words_from_text(f"{row.get('title', '')} {row.get('keywords', '')} {row.get('youtube_tags', '')}"))
            ),
            axis=1,
        )
    ].copy()
    if matches.empty:
        return {"title": "", "url": "", "views": 0, "views_per_day": 0.0}

    best = matches.sort_values(["views_per_day", "views"], ascending=False).iloc[0]
    return {
        "title": best.get("title", ""),
        "url": best.get("url", ""),
        "views": int(best.get("views", 0)),
        "views_per_day": float(best.get("views_per_day", 0)),
    }


def next_post_titles(topic: str, signal: str, related_keywords: List[str]) -> List[str]:
    topic_title = title_case_topic(topic)
    current_year = datetime.now().year
    related = [title_case_topic(keyword) for keyword in related_keywords if keyword and keyword != topic]
    support = related[0] if related else "Strategy"

    if signal == "Content gap":
        return [
            f"{topic_title}: Complete Guide Your Competitors Are Covering",
            f"Before You Miss {topic_title}, Watch This Full Breakdown",
            f"{topic_title} Strategy for {current_year}: What Works Now",
            f"{topic_title} Explained with Examples and Action Plan",
            f"Why {topic_title} Is a Big Opportunity Right Now",
        ]
    if signal == "Trend":
        return [
            f"{topic_title} Is Trending: What You Should Know Now",
            f"{topic_title} Trend Explained: Opportunity or Saturation?",
            f"Why Everyone Is Talking About {topic_title} in {current_year}",
            f"{topic_title}: Fresh Strategy Based on Current Demand",
            f"{topic_title} Momentum: How to Use It Before It Peaks",
        ]
    if signal == "Comments":
        return comment_title_options("Content request", topic, related_keywords)
    if signal == "YouTube search":
        return [
            f"{topic_title}: What People Are Searching on YouTube Right Now",
            f"{topic_title} Complete Search Guide for {current_year}",
            f"{topic_title} Explained: Best Answer for YouTube Search Demand",
            f"How to Use {topic_title} for Better Results",
            f"{topic_title} vs {support}: Which Should You Choose?",
        ]

    return [
        f"{topic_title} Explained: Complete Guide for {current_year}",
        f"{topic_title} Strategy That Actually Works",
        f"Before You Start {topic_title}, Watch This",
        f"{topic_title} Mistakes You Should Avoid",
        f"How to Master {topic_title}: Step-by-Step Plan",
    ]


def next_post_reason(row: pd.Series) -> str:
    reasons = []
    if row["trend_score"] >= 60:
        reasons.append("trend momentum strong hai")
    if row["gap_score"] >= 60:
        reasons.append("competitors cover kar rahe hain, aapka gap dikhta hai")
    if row["outlier_score"] >= 60:
        reasons.append("similar videos outlier performance de rahe hain")
    if row["comment_score"] >= 60:
        reasons.append("comments me direct audience demand hai")
    if row["search_score"] >= 60:
        reasons.append("YouTube search data me opportunity signal hai")
    if row["competitor_score"] >= 60:
        reasons.append("competitor/market videos par views strong hain")

    if not reasons:
        reasons.append("overall dataset me moderate but test-worthy signal hai")
    return "; ".join(reasons)


def build_next_post_recommendations(
    own_channel_title: str,
    all_videos: pd.DataFrame,
    comments: Optional[pd.DataFrame] = None,
    market_scores: Optional[pd.DataFrame] = None,
    top_n: int = 10,
) -> pd.DataFrame:
    columns = [
        "rank", "recommended_topic", "primary_signal", "what_should_we_post",
        "title_1", "title_2", "title_3", "title_4", "title_5", "long_tail_keywords",
        "final_score", "trend_score", "gap_score", "outlier_score", "comment_score",
        "search_score", "competitor_score", "why_post_next", "proof_video",
        "proof_views", "proof_url",
    ]
    if all_videos.empty:
        return pd.DataFrame(columns=columns)

    videos = prepare_video_frame(add_content_categories(dedupe_videos(all_videos))).copy()
    records = []

    def add_record(topic: str, signal: str, **scores) -> None:
        clean_topic = " ".join(str(topic).strip().split()).lower()
        if not clean_topic or clean_topic in STOPWORDS or len(clean_topic) < 3:
            return
        records.append(
            {
                "recommended_topic": clean_topic,
                "signal": signal,
                "trend_score": float(scores.get("trend_score", 0)),
                "gap_score": float(scores.get("gap_score", 0)),
                "outlier_score": float(scores.get("outlier_score", 0)),
                "comment_score": float(scores.get("comment_score", 0)),
                "search_score": float(scores.get("search_score", 0)),
                "competitor_score": float(scores.get("competitor_score", 0)),
            }
        )

    keyword_scores = keyword_table(videos, top_n=40)
    max_keyword_views_day = max(float(keyword_scores["avg_views_per_day"].max()), 1.0) if not keyword_scores.empty else 1.0
    for row in keyword_scores.itertuples():
        add_record(
            row.keyword,
            "Channel + competitors",
            competitor_score=normalize_score(float(row.avg_views_per_day), max_keyword_views_day),
            outlier_score=normalize_score(float(row.uses), max(float(keyword_scores["uses"].max()), 1.0)),
        )

    recent = recent_window_videos(videos, 30)
    if not recent.empty:
        median_views_day = max(float(recent["views_per_day"].median()), 1.0)
        outliers = recent[recent["views_per_day"] >= median_views_day * 1.75]
        for _, row in outliers.sort_values("views_per_day", ascending=False).head(30).iterrows():
            for keyword in title_keywords(row["title"])[:4]:
                add_record(
                    keyword,
                    "Recent outlier",
                    outlier_score=normalize_score(float(row["views_per_day"]), max(float(outliers["views_per_day"].max()), 1.0)),
                    competitor_score=80 if row.get("channel") != own_channel_title else 55,
                )

    gaps = content_gap_opportunities(own_channel_title, videos, days=30)
    if not gaps.empty:
        max_gap_views = max(float(gaps["competitor_total_views"].max()), 1.0)
        for row in gaps.itertuples():
            add_record(
                row.topic_keyword,
                "Content gap",
                gap_score=normalize_score(float(row.competitor_total_views), max_gap_views),
                competitor_score=normalize_score(float(row.competitor_total_views), max_gap_views),
            )

    try:
        trends, _, _ = detect_youtube_trends(videos, current_window_days=30, minimum_current_videos=1)
    except Exception:
        trends = pd.DataFrame()

    if not trends.empty:
        for row in trends.head(20).itertuples():
            add_record(
                row.trend_topic,
                "Trend",
                trend_score=float(row.trend_score),
                competitor_score=normalize_score(float(row.current_total_views), max(float(trends["current_total_views"].max()), 1.0)),
            )

    if comments is not None and not comments.empty:
        comment_ideas = comment_content_ideas(comments, videos, top_n=20)
        if not comment_ideas.empty:
            max_comment_score = max(float(comment_ideas["demand_score"].max()), 1.0)
            for row in comment_ideas.itertuples():
                add_record(
                    row.topic_keyword,
                    "Comments",
                    comment_score=normalize_score(float(row.demand_score), max_comment_score),
                )

    if market_scores is not None and not market_scores.empty:
        for row in market_scores.head(30).itertuples():
            add_record(
                row.search_intent,
                "YouTube search",
                search_score=float(row.opportunity_score),
                trend_score=float(row.topic_momentum),
                outlier_score=float(row.outlier_frequency),
                gap_score=float(row.your_content_gap),
                competitor_score=float(row.competitor_performance),
            )

    if not records:
        return pd.DataFrame(columns=columns)

    source = pd.DataFrame(records)
    score_cols = ["trend_score", "gap_score", "outlier_score", "comment_score", "search_score", "competitor_score"]
    grouped = (
        source.groupby("recommended_topic")
        .agg(
            primary_signal=("signal", lambda values: values.value_counts().index[0]),
            trend_score=("trend_score", "max"),
            gap_score=("gap_score", "max"),
            outlier_score=("outlier_score", "max"),
            comment_score=("comment_score", "max"),
            search_score=("search_score", "max"),
            competitor_score=("competitor_score", "max"),
        )
        .reset_index()
    )
    grouped["final_score"] = (
        grouped["trend_score"] * 0.18
        + grouped["gap_score"] * 0.17
        + grouped["outlier_score"] * 0.18
        + grouped["comment_score"] * 0.17
        + grouped["search_score"] * 0.17
        + grouped["competitor_score"] * 0.13
    ).round(1)

    for column in score_cols:
        grouped[column] = grouped[column].round(1)

    grouped = grouped.sort_values("final_score", ascending=False).head(top_n).copy()
    grouped.insert(0, "rank", range(1, len(grouped) + 1))
    grouped["what_should_we_post"] = grouped["recommended_topic"].apply(
        lambda topic: f"Post a focused video on {title_case_topic(topic)}"
    )
    grouped["why_post_next"] = grouped.apply(next_post_reason, axis=1)
    grouped["long_tail_keywords"] = grouped.apply(
        lambda row: ", ".join(
            comment_long_tail_keywords(
                "Content request",
                row["recommended_topic"],
                channel_context_keywords(row["recommended_topic"], videos, limit=8),
            )
        ),
        axis=1,
    )

    title_options = grouped.apply(
        lambda row: next_post_titles(
            row["recommended_topic"],
            row["primary_signal"],
            channel_context_keywords(row["recommended_topic"], videos, limit=8),
        ),
        axis=1,
    )
    for index in range(5):
        grouped[f"title_{index + 1}"] = title_options.apply(lambda titles: titles[index] if len(titles) > index else "")

    proof_rows = grouped["recommended_topic"].apply(lambda topic: topic_best_video(videos, topic))
    grouped["proof_video"] = proof_rows.apply(lambda item: item["title"])
    grouped["proof_views"] = proof_rows.apply(lambda item: item["views"])
    grouped["proof_url"] = proof_rows.apply(lambda item: item["url"])

    return grouped[columns].reset_index(drop=True)


def top_title_patterns(videos: pd.DataFrame) -> Dict:
    top_count = max(5, int(len(videos) * 0.25))
    top_videos = dedupe_videos(videos).sort_values("views", ascending=False).head(top_count)
    keyword_counts = Counter(keyword for title in top_videos["title"] for keyword in title_keywords(title))
    hook_counts = Counter(hook for title in top_videos["title"] for hook in title_hook_words(title))

    return {
        "top_videos": top_videos,
        "keywords": [keyword for keyword, _ in keyword_counts.most_common(15)],
        "hooks": [hook for hook, _ in hook_counts.most_common(10)],
        "title_char_range": (
            int(top_videos["title_length"].quantile(0.25)),
            int(top_videos["title_length"].quantile(0.75)),
        ),
        "best_title_bucket": top_videos["title_length_bucket"].mode().iloc[0],
        "best_video_bucket": top_videos["video_length_bucket"].mode().iloc[0],
        "best_word_count": int(round(top_videos["word_count"].median())),
    }


def description_keywords(description: str) -> List[str]:
    return words_from_text(description)[:20]


def generate_title_suggestions(
    own_videos: pd.DataFrame,
    all_videos: pd.DataFrame,
    video_description: str,
    count: int = 5,
) -> List[str]:
    own_patterns = top_title_patterns(own_videos)
    all_patterns = top_title_patterns(all_videos)
    desc_keywords = description_keywords(video_description)
    strong_keywords = keyword_table(all_videos, top_n=20)["keyword"].tolist()
    seed_keywords = []

    for keyword in desc_keywords + strong_keywords + own_patterns["keywords"] + all_patterns["keywords"]:
        if keyword not in seed_keywords:
            seed_keywords.append(keyword)

    if not seed_keywords:
        seed_keywords = ["strategy", "mistakes", "growth", "guide", "checklist"]

    hooks = all_patterns["hooks"] or ["mistakes", "guide", "truth", "checklist", "explained"]
    target_low, target_high = all_patterns["title_char_range"]
    current_year = datetime.now().year

    templates = [
        "{number} {keyword_title} {hook_title} You Should Know",
        "Before You Try {keyword}, Watch This",
        "{keyword_title} Explained: Simple Guide for {year}",
        "I Studied {keyword}: What Actually Works",
        "{keyword_title} Mistakes That Cost You Views",
        "How to Use {keyword} for Better Results",
        "The Truth About {keyword} Nobody Tells Beginners",
        "{keyword_title} Checklist: Do This Before You Start",
    ]

    titles = []
    for index, template in enumerate(templates):
        keyword = seed_keywords[index % len(seed_keywords)]
        hook = hooks[index % len(hooks)]
        title = template.format(
            keyword=keyword,
            keyword_title=keyword.title(),
            hook=hook,
            hook_title=hook.title(),
            number=[5, 7, 9, 11][index % 4],
            year=current_year,
        )
        if len(title) > max(target_high + 15, 80):
            title = f"{keyword.title()} {hook.title()}: What Works Now"
        if len(title) < max(target_low - 20, 30):
            title = f"{title} for Beginners"
        if title not in titles:
            titles.append(title)
        if len(titles) == count:
            break

    return titles[:count]


def build_markdown_report(
    own_channel: Dict,
    own_videos: pd.DataFrame,
    competitor_channels: List[Dict],
    competitor_videos: pd.DataFrame,
    all_videos: pd.DataFrame,
    video_description: str,
) -> str:
    own_patterns = top_title_patterns(own_videos)
    suggested_titles = generate_title_suggestions(own_videos, all_videos, video_description)
    best_keywords = keyword_table(all_videos, top_n=20)["keyword"].tolist()
    best_hooks = hook_table(all_videos, top_n=20)["hook_keyword"].tolist()
    best_tags = tag_table(all_videos, top_n=20)["search_tag"].tolist()

    lines = [
        "# YouTube Title Strategy Report",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Your Channel",
        f"- Channel: {own_channel['title']}",
        f"- Videos analysed: {len(own_videos)}",
        f"- Best title length: {own_patterns['best_title_bucket']} ({own_patterns['title_char_range'][0]}-{own_patterns['title_char_range'][1]} chars among top performers)",
        f"- Best word count: around {own_patterns['best_word_count']} words",
        f"- Best video length: {own_patterns['best_video_bucket']}",
        f"- Strong keywords: {', '.join(own_patterns['keywords'][:10])}",
        f"- Strong hooks: {', '.join(own_patterns['hooks'][:8])}",
        "",
    ]

    if competitor_channels:
        lines.append("## Competitors")
        for channel in competitor_channels:
            rows = competitor_videos[competitor_videos["channel_id"] == channel["id"]]
            patterns = top_title_patterns(rows)
            lines.extend(
                [
                    f"### {channel['title']}",
                    f"- Videos analysed: {len(rows)}",
                    f"- Strong keywords: {', '.join(patterns['keywords'][:8])}",
                    f"- Strong hooks: {', '.join(patterns['hooks'][:8])}",
                    f"- Best title length: {patterns['best_title_bucket']}",
                    "",
                ]
            )

    lines.extend(
        [
            "## Best 5 Suggested Titles",
            *[f"- {title}" for title in suggested_titles],
            "",
            "## Top 20 Most-Used Keywords",
            ", ".join(best_keywords),
            "",
            "## Top 20 Search Tags",
            ", ".join(best_tags),
            "",
            "## Top 20 High-View Hook Keywords",
            ", ".join(best_hooks),
            "",
            "## Top Unique Videos By Total Views",
            *[
                f"- {row.title} | {row.video_type} | {int(row.views):,} total views | {row.channel}"
                for row in dedupe_videos(all_videos).sort_values("views", ascending=False).head(20).itertuples()
            ],
            "",
            "## Upload Frequency Summary",
            *[
                f"- {row.channel}: {row.avg_uploads_per_week} uploads/week average, max {row.max_uploads_in_week} in one week"
                for row in upload_frequency_summary(all_videos).itertuples()
            ],
        ]
    )

    if video_description.strip():
        lines.extend(
            [
                "",
                "## New Video Topic Relevance",
                *[
                    f"- {row.channel}: {row.topic_relevance_score}% match | {row.matching_keywords or 'no direct keyword match'}"
                    for row in topic_relevance_table(all_videos, video_description).itertuples()
                ],
            ]
        )

    content_gap_summary = content_gap_pivot_sheet(all_videos)
    if not content_gap_summary.empty:
        lines.extend(
            [
                "",
                "## Last 30 Days Content Gap Summary",
            ]
        )
        for _, row in content_gap_summary.iterrows():
            lines.append(
                f"- {row['channel']}: Academic {row.get('Academic', 0)}, "
                f"Strategy/Non-academic {row.get('Non-academic / Strategy', 0)}, "
                f"Other {row.get('Other / mixed', 0)}, total videos {row.get('total_videos', 0)}"
            )

    return "\n".join(lines)


def format_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def render_channel_header(channel: Dict, videos: pd.DataFrame) -> None:
    left, right = st.columns([1, 4])
    with left:
        if channel.get("thumbnail"):
            st.image(channel["thumbnail"], width=96)
    with right:
        st.subheader(channel["title"])
        st.caption(channel["id"])
        stats = st.columns(4)
        stats[0].metric("Subscribers", format_number(channel["subscriber_count"]))
        stats[1].metric("Channel views", format_number(channel["view_count"]))
        stats[2].metric("Total videos", format_number(channel["video_count"]))
        stats[3].metric("Analysed", len(videos))


def render_analysis(label: str, videos: pd.DataFrame, key_prefix: str) -> None:
    st.markdown(f"### {label}")
    selected_type = st.segmented_control(
        "Video type",
        ["All videos", "Shorts", "Long videos"],
        default="All videos",
        key=f"{key_prefix}_video_type",
    )
    videos = filter_videos_by_type(videos, selected_type)

    if videos.empty:
        st.warning(f"No {selected_type.lower()} found in this channel for the selected date range.")
        return

    metrics = st.columns(5)
    metrics[0].metric("Average views", format_number(int(videos["views"].mean())))
    metrics[1].metric("Median views", format_number(int(videos["views"].median())))
    metrics[2].metric("Best total views", format_number(int(videos["views"].max())))
    metrics[3].metric("Avg title length", int(videos["title_length"].mean()))
    metrics[4].metric("Avg word count", int(videos["word_count"].mean()))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Title length performance")
        st.dataframe(bucket_table(videos, "title_length_bucket"))
    with col2:
        st.markdown("#### Number / question / year performance")
        st.dataframe(feature_table(videos), hide_index=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### Top 20 most-used keywords")
        st.dataframe(keyword_table(videos, top_n=20), hide_index=True)
    with col4:
        st.markdown("#### Top 20 high-view hook words")
        st.dataframe(hook_table(videos, top_n=20), hide_index=True)

    st.markdown("#### Top 20 high-view videos with hooks")
    st.dataframe(
        high_view_hook_videos(videos, top_n=20),
        hide_index=True,
        column_config={
            "views": st.column_config.NumberColumn("Total views", format="%d"),
            "url": st.column_config.LinkColumn("Video URL"),
        },
    )

    st.markdown("#### Search tags")
    st.dataframe(tag_table(videos, top_n=20), hide_index=True)

    st.markdown("#### Latest unique video data")
    display_columns = [
        "channel", "title", "video_type", "upload_date", "title_length", "word_count",
        "has_number", "has_question", "has_year", "views", "video_age_days",
        "views_per_day", "duration_minutes", "ctr", "keywords", "hook_keywords",
        "youtube_tags", "url",
    ]
    st.dataframe(
        videos[display_columns],
        hide_index=True,
        column_config={
            "views": st.column_config.NumberColumn("Total views", format="%d"),
            "views_per_day": st.column_config.NumberColumn("Views per day", format="%.2f"),
            "url": st.column_config.LinkColumn("Video URL"),
        },
    )


def render_overall_recommendations(
    own_videos: pd.DataFrame,
    competitor_videos: pd.DataFrame,
    all_videos: pd.DataFrame,
    video_description: str,
) -> None:
    competitor_count = competitor_videos["channel_id"].nunique() if not competitor_videos.empty else 0
    if competitor_count:
        st.caption(f"Title suggestions are based on your channel plus {competitor_count} competitor channel(s).")
    else:
        st.caption("Title suggestions are based on your channel only because no competitor channel was analysed.")

    st.markdown("### Overall comparison")
    comparison = (
        all_videos.groupby("channel")
        .agg(
            analysed=("video_id", "count"),
            avg_views=("views", "mean"),
            median_views=("views", "median"),
            avg_views_per_day=("views_per_day", "mean"),
            avg_title_length=("title_length", "mean"),
            avg_word_count=("word_count", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("avg_views_per_day", ascending=False)
    )
    st.dataframe(comparison, hide_index=True)

    own_patterns = top_title_patterns(own_videos)
    all_patterns = top_title_patterns(all_videos)
    competitor_keywords = keyword_table(competitor_videos, top_n=30)["keyword"].tolist() if not competitor_videos.empty else []
    own_keywords = keyword_table(own_videos, top_n=30)["keyword"].tolist()
    keyword_gaps = [keyword for keyword in competitor_keywords if keyword not in own_keywords][:10]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(
            f"Your best title zone: {own_patterns['title_char_range'][0]}-{own_patterns['title_char_range'][1]} chars, "
            f"around {own_patterns['best_word_count']} words."
        )
    with col2:
        st.warning(
            f"Market best title zone: {all_patterns['title_char_range'][0]}-{all_patterns['title_char_range'][1]} chars, "
            f"best bucket: {all_patterns['best_title_bucket']}."
        )
    with col3:
        st.success("Keyword gaps: " + (", ".join(keyword_gaps) if keyword_gaps else "No clear competitor gap found."))

    st.markdown("### Best 5 title suggestions")
    suggestions = generate_title_suggestions(own_videos, all_videos, video_description)
    for title in suggestions:
        st.write(f"- {title}")

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown("#### Top 20 most-used keywords")
        st.dataframe(keyword_table(all_videos, top_n=20), hide_index=True)
    with col5:
        st.markdown("#### Top 20 search tags")
        st.dataframe(tag_table(all_videos, top_n=20), hide_index=True)
    with col6:
        st.markdown("#### Top 20 high-view hook words")
        st.dataframe(hook_table(all_videos, top_n=20), hide_index=True)


def render_growth_insights(
    own_videos: pd.DataFrame,
    competitor_channels: List[Dict],
    competitor_videos: pd.DataFrame,
    all_videos: pd.DataFrame,
    video_description: str,
) -> None:
    st.markdown("### Why recent videos performed")
    st.caption(
        "These are possible reasons inferred from public data: total views, title keywords, hooks, format, and whether similar topics appear across channels."
    )

    with st.container(border=True):
        st.markdown("#### Your latest 10 videos")
        st.dataframe(
            latest_10_reason_table(own_videos, all_videos),
            hide_index=True,
            column_config={
                "views": st.column_config.NumberColumn("Total views", format="%d"),
                "url": st.column_config.LinkColumn("Video URL"),
            },
        )

    if not competitor_videos.empty:
        for channel in competitor_channels:
            rows = competitor_videos[competitor_videos["channel_id"] == channel["id"]]
            with st.container(border=True):
                st.markdown(f"#### {channel['title']} latest 10 videos")
                st.dataframe(
                    latest_10_reason_table(rows, all_videos),
                    hide_index=True,
                    column_config={
                        "views": st.column_config.NumberColumn("Total views", format="%d"),
                        "url": st.column_config.LinkColumn("Video URL"),
                    },
                )

    st.markdown("### Weekly upload frequency")
    st.caption("This shows how many videos each channel uploaded week by week in the latest analysed videos.")
    st.dataframe(
        weekly_upload_frequency(all_videos),
        hide_index=True,
        column_config={
            "avg_views": st.column_config.NumberColumn("Average total views", format="%.2f"),
        },
    )

    st.markdown("### Channel frequency summary")
    st.dataframe(
        upload_frequency_summary(all_videos),
        hide_index=True,
        column_config={
            "avg_uploads_per_week": st.column_config.NumberColumn("Avg uploads/week", format="%.2f"),
            "avg_views": st.column_config.NumberColumn("Average total views", format="%.2f"),
        },
    )

    st.markdown("### New video topic relevance")
    if video_description.strip():
        st.caption("Higher score means your next video description matches more keywords already working on that channel.")
        st.dataframe(topic_relevance_table(all_videos, video_description), hide_index=True)
    else:
        st.info("Write your next video description in the sidebar to see topic relevance by channel.")


MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def render_dashboard_page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="yt-kicker">Growth intelligence</div>
        <div class="yt-page-title">{title}</div>
        """,
        unsafe_allow_html=True,
    )
    if subtitle:
        st.caption(subtitle)


def ensure_dashboard_video_columns(videos: pd.DataFrame) -> pd.DataFrame:
    frame = videos.copy()
    for column, default in {
        "thumbnail": "",
        "title": "",
        "channel": "",
        "upload_date": "",
        "views": 0,
        "views_per_day": 0.0,
        "outlier_score": None,
        "video_id": "",
        "url": "",
    }.items():
        if column not in frame.columns:
            frame[column] = default

    frame["views"] = pd.to_numeric(frame["views"], errors="coerce").fillna(0)
    frame["views_per_day"] = pd.to_numeric(frame["views_per_day"], errors="coerce").fillna(0.0)
    if frame.empty:
        frame["outlier_score"] = 0.0
        return frame
    if frame["outlier_score"].isna().all():
        median_value = float(frame["views_per_day"].median())
        median_views_day = median_value if median_value > 0 else 1.0
        frame["outlier_score"] = (frame["views_per_day"] / median_views_day).round(2)
    else:
        frame["outlier_score"] = pd.to_numeric(frame["outlier_score"], errors="coerce").fillna(0.0)
    return frame


def period_growth_delta(videos: pd.DataFrame, days: int = 28) -> str:
    if videos.empty or "published_at" not in videos.columns:
        return "No recent data"
    frame = videos.copy()
    published = pd.to_datetime(frame["published_at"], utc=True, errors="coerce")
    if published.dropna().empty:
        return "No recent data"
    frame["published_at_dt"] = published
    frame["views"] = pd.to_numeric(frame.get("views", 0), errors="coerce").fillna(0)
    end_date = published.max()
    current_start = end_date - pd.Timedelta(days=days)
    previous_start = current_start - pd.Timedelta(days=days)
    current_views = frame[frame["published_at_dt"] >= current_start]["views"].sum()
    previous_views = frame[
        (frame["published_at_dt"] >= previous_start) & (frame["published_at_dt"] < current_start)
    ]["views"].sum()
    if previous_views <= 0:
        return "New activity"
    growth = ((current_views - previous_views) / previous_views) * 100
    sign = "+" if growth >= 0 else ""
    return f"{sign}{growth:.1f}% vs previous {days}D"


def render_premium_channel_header(channel: Dict, videos: pd.DataFrame) -> None:
    with st.container(border=True):
        header_cols = st.columns([1, 5, 2], vertical_alignment="center")
        with header_cols[0]:
            if channel.get("thumbnail"):
                st.image(channel["thumbnail"], width=82)
        with header_cols[1]:
            st.markdown(f"### {channel.get('title', 'Channel')}")
            st.caption(str(channel.get("description", ""))[:180])
        with header_cols[2]:
            st.metric("Recent growth", period_growth_delta(videos), border=True)

        render_metric_cards(
            [
                {"label": "Subscribers", "value": format_compact_number(channel.get("subscriber_count", 0))},
                {"label": "Total views", "value": format_compact_number(channel.get("view_count", 0))},
                {"label": "Video count", "value": format_compact_number(channel.get("video_count", 0))},
                {"label": "Analysed uploads", "value": format_compact_number(len(videos))},
            ]
        )


def render_overview_dashboard(
    own_channel: Dict,
    own_videos: pd.DataFrame,
    competitor_videos: pd.DataFrame,
    all_videos: pd.DataFrame,
) -> None:
    own_videos = ensure_dashboard_video_columns(own_videos)
    competitor_videos = ensure_dashboard_video_columns(competitor_videos)
    all_videos = ensure_dashboard_video_columns(all_videos)
    render_dashboard_page_header(
        "Overview",
        "Channel performance, outliers, competitor movement, and seasonal opportunities in one dashboard.",
    )
    render_premium_channel_header(own_channel, own_videos)

    timeframe = st.segmented_control(
        "Timeframe",
        ["7D", "28D", "90D", "1Y", "2Y"],
        default=st.session_state.get("overview_timeframe", "28D"),
        key="overview_timeframe",
    )
    scoped_own = filter_videos_by_timeframe(own_videos, timeframe)
    scoped_all = filter_videos_by_timeframe(all_videos, timeframe)
    scoped_competitors = filter_videos_by_timeframe(competitor_videos, timeframe)

    total_views = int(pd.to_numeric(scoped_own.get("views", 0), errors="coerce").fillna(0).sum()) if not scoped_own.empty else 0
    avg_views_per_day = float(pd.to_numeric(scoped_own.get("views_per_day", 0), errors="coerce").fillna(0).mean()) if not scoped_own.empty else 0
    outlier_count = int((pd.to_numeric(scoped_all.get("outlier_score", 0), errors="coerce").fillna(0) >= 2).sum()) if not scoped_all.empty else 0
    competitor_uploads = len(scoped_competitors)

    render_metric_cards(
        [
            {"label": "Timeframe views", "value": format_compact_number(total_views), "delta": period_growth_delta(scoped_own)},
            {"label": "Avg views/day", "value": f"{avg_views_per_day:,.1f}"},
            {"label": "Recent outliers", "value": format_compact_number(outlier_count)},
            {"label": "Competitor uploads", "value": format_compact_number(competitor_uploads)},
        ]
    )

    with st.container(border=True):
        st.markdown("#### Channel growth")
        render_growth_chart(scoped_own)

    section_cols = st.columns(2)
    with section_cols[0]:
        with st.container(border=True):
            st.markdown("#### Recent outliers")
            outlier_videos = scoped_all.sort_values(["outlier_score", "views_per_day"], ascending=False)
            render_video_card_grid(outlier_videos, limit=4, columns=2)

    with section_cols[1]:
        with st.container(border=True):
            st.markdown("#### Trending topics")
            st.dataframe(keyword_table(scoped_all, top_n=12), hide_index=True)

    lower_cols = st.columns(2)
    with lower_cols[0]:
        with st.container(border=True):
            st.markdown("#### Competitor activity")
            render_competitor_activity_chart(scoped_competitors)

    with lower_cols[1]:
        with st.container(border=True):
            st.markdown("#### Upcoming seasonal opportunities")
            seasonal = build_seasonal_opportunities(all_videos).head(8)
            if seasonal.empty:
                st.caption("No seasonal opportunity data available.")
            else:
                st.dataframe(
                    seasonal[
                        [
                            "month_name", "topic", "trend_stage", "demand_score",
                            "competitor_supply", "recommended_publishing_window",
                        ]
                    ],
                    hide_index=True,
                    column_config={"demand_score": st.column_config.NumberColumn("Demand score", format="%.1f")},
                )


def build_seasonal_opportunities(videos: pd.DataFrame) -> pd.DataFrame:
    if videos.empty or "published_at" not in videos.columns:
        return pd.DataFrame()
    records = []
    frame = videos.copy()
    frame["published_at_dt"] = pd.to_datetime(frame["published_at"], utc=True, errors="coerce")
    frame["views"] = pd.to_numeric(frame.get("views", 0), errors="coerce").fillna(0)
    frame["views_per_day"] = pd.to_numeric(frame.get("views_per_day", 0), errors="coerce").fillna(0)
    frame = frame.dropna(subset=["published_at_dt"])
    for _, row in frame.iterrows():
        topics = title_keywords(str(row.get("title", "")))[:4]
        for topic in topics:
            records.append(
                {
                    "month": int(row["published_at_dt"].month),
                    "month_name": MONTH_NAMES[int(row["published_at_dt"].month) - 1],
                    "topic": topic,
                    "channel": row.get("channel", ""),
                    "views": row.get("views", 0),
                    "views_per_day": row.get("views_per_day", 0),
                    "url": row.get("url", ""),
                    "title": row.get("title", ""),
                }
            )
    if not records:
        return pd.DataFrame()

    topic_df = pd.DataFrame(records)
    grouped = (
        topic_df.groupby(["month", "month_name", "topic"], as_index=False)
        .agg(
            videos=("topic", "size"),
            total_views=("views", "sum"),
            avg_views=("views", "mean"),
            avg_views_per_day=("views_per_day", "mean"),
            competitor_supply=("channel", "nunique"),
            best_video_title=("title", "first"),
            best_video_url=("url", "first"),
        )
    )
    max_views = max(float(grouped["total_views"].max()), 1.0)
    max_velocity = max(float(grouped["avg_views_per_day"].max()), 1.0)
    grouped["demand_score"] = (
        (grouped["total_views"] / max_views) * 65
        + (grouped["avg_views_per_day"] / max_velocity) * 35
    ).round(1)
    grouped["trend_stage"] = grouped.apply(
        lambda row: "Breakout" if row["demand_score"] >= 80 and row["videos"] <= 4
        else "Proven" if row["demand_score"] >= 65
        else "Competitive" if row["videos"] >= 6
        else "Early signal",
        axis=1,
    )
    grouped["recommended_publishing_window"] = grouped["month"].apply(
        lambda month: f"{MONTH_NAMES[(month - 2) % 12]} end to {MONTH_NAMES[month - 1]} mid"
    )
    return grouped.sort_values(["demand_score", "total_views"], ascending=False)


def render_seasonal_intelligence(all_videos: pd.DataFrame) -> None:
    render_dashboard_page_header(
        "Seasonal intelligence",
        "Month-wise topic demand, competitor supply, and recommended publishing windows from analysed uploads.",
    )
    opportunities = build_seasonal_opportunities(all_videos)
    if opportunities.empty:
        st.info("Analyse a wider date range to build seasonal intelligence.")
        return

    render_metric_cards(
        [
            {"label": "Seasonal topics", "value": format_compact_number(opportunities["topic"].nunique())},
            {"label": "Months detected", "value": format_compact_number(opportunities["month"].nunique())},
            {"label": "High-demand topics", "value": format_compact_number((opportunities["demand_score"] >= 70).sum())},
            {"label": "Avg competitor supply", "value": f"{opportunities['competitor_supply'].mean():.1f}"},
        ]
    )

    with st.container(border=True):
        st.markdown("#### 12-month topic heatmap")
        top_topics = opportunities.groupby("topic")["demand_score"].max().sort_values(ascending=False).head(18).index
        render_month_topic_heatmap(opportunities[opportunities["topic"].isin(top_topics)].copy())

    st.markdown("#### Upcoming opportunities")
    st.dataframe(
        opportunities[
            [
                "month_name", "topic", "trend_stage", "demand_score", "videos",
                "total_views", "avg_views_per_day", "competitor_supply",
                "recommended_publishing_window", "best_video_title", "best_video_url",
            ]
        ].head(60),
        hide_index=True,
        column_config={
            "demand_score": st.column_config.NumberColumn("Demand score", format="%.1f"),
            "total_views": st.column_config.NumberColumn("Total views", format="%d"),
            "avg_views_per_day": st.column_config.NumberColumn("Avg views/day", format="%.2f"),
            "best_video_url": st.column_config.LinkColumn("Best video URL"),
        },
    )


def render_content_gap_filler(own_channel: Dict, all_videos: pd.DataFrame) -> None:
    st.markdown("### Content gap filler")
    st.caption(
        "Last 30 days me aap aur competitors ne academic vs non-academic/strategy content kitna publish kiya, aur kis topic par views aaye."
    )

    days = 30
    recent = recent_window_videos(all_videos, days)
    if recent.empty:
        st.warning("Last 30 days me analysed channels ke videos nahi mile. More recent uploads wale channels add karke retry karein.")
        return

    comparison = content_gap_pivot_sheet(all_videos, days)
    category_summary = content_gap_summary_sheet(all_videos, days)
    video_sheet = content_gap_video_sheet(all_videos, days)
    topic_sheet = content_topic_sheet(all_videos, days)
    opportunities = content_gap_opportunities(own_channel["title"], all_videos, days)

    st.markdown("#### Channel comparison sheet")
    st.dataframe(
        comparison,
        hide_index=True,
        column_config={
            "total_views": st.column_config.NumberColumn("Total views", format="%d"),
            "avg_views": st.column_config.NumberColumn("Average views", format="%.2f"),
        },
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Category performance")
        st.dataframe(
            category_summary,
            hide_index=True,
            column_config={
                "total_views": st.column_config.NumberColumn("Total views", format="%d"),
                "avg_views": st.column_config.NumberColumn("Average views", format="%.2f"),
                "best_video_views": st.column_config.NumberColumn("Best video views", format="%d"),
            },
        )
    with col2:
        st.markdown("#### Content gap opportunities")
        st.dataframe(
            opportunities,
            hide_index=True,
            column_config={
                "competitor_total_views": st.column_config.NumberColumn("Competitor total views", format="%d"),
                "best_competitor_url": st.column_config.LinkColumn("Best competitor URL"),
            },
        )

    st.markdown("#### Topic keyword sheet")
    st.dataframe(
        topic_sheet.head(100),
        hide_index=True,
        column_config={
            "total_views": st.column_config.NumberColumn("Total views", format="%d"),
            "avg_views": st.column_config.NumberColumn("Average views", format="%.2f"),
            "best_video_url": st.column_config.LinkColumn("Best video URL"),
        },
    )

    st.markdown("#### Last 30 days video-level comparison")
    st.dataframe(
        video_sheet,
        hide_index=True,
        column_config={
            "views": st.column_config.NumberColumn("Total views", format="%d"),
            "views_per_day": st.column_config.NumberColumn("Views per day", format="%.2f"),
            "url": st.column_config.LinkColumn("Video URL"),
        },
    )

    st.markdown("#### Download content gap sheets")
    with st.container(horizontal=True):
        st.download_button(
            "Download comparison CSV",
            comparison.to_csv(index=False).encode("utf-8"),
            file_name="content_gap_channel_comparison.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download video sheet CSV",
            video_sheet.to_csv(index=False).encode("utf-8"),
            file_name="content_gap_video_sheet.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download topic gap CSV",
            opportunities.to_csv(index=False).encode("utf-8"),
            file_name="content_gap_opportunities.csv",
            mime="text/csv",
        )


def render_opportunity_finder(
    api_key: str,
    own_channel: Dict,
    all_videos: pd.DataFrame,
    video_description: str,
) -> None:
    st.markdown("### YouTube opportunity finder")
    st.caption(
        "This uses YouTube search API to find market videos beyond your selected channels, then scores search intents for new content ideas."
    )
    st.warning("Quota note: each searched intent uses YouTube search API quota. Start with 3-5 intents.")
    if not api_key:
        st.error("Opportunity Finder ke liye YouTube API key required hai.")
        return

    default_intents = candidate_search_intents(own_channel["title"], all_videos, video_description, "", limit=10)
    with st.container(border=True):
        extra_seed_text = st.text_area(
            "Extra seed keywords or niche",
            placeholder="Example: MBA entrance, CAT strategy, study plan, salary, career roadmap",
            height=90,
            key="opportunity_seed_text",
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            days = st.selectbox("Search recency window", [7, 30, 90], index=1, key="opportunity_days")
            max_intents = st.slider("Search intents to test", 3, 10, 5, key="opportunity_intents")
        with col2:
            max_results = st.slider("Videos per intent", 5, 25, 10, step=5, key="opportunity_results")
            order = st.selectbox("YouTube search order", ["relevance", "date", "viewCount"], index=0, key="opportunity_order")
        with col3:
            region_code = st.text_input("Region code", value="IN", max_chars=2, key="opportunity_region")
            relevance_language = st.text_input("Language code", value="hi", max_chars=5, key="opportunity_language")

        intents = candidate_search_intents(
            own_channel["title"],
            all_videos,
            video_description,
            extra_seed_text,
            limit=max_intents,
        )
        if intents:
            st.caption("Search intents that will be tested: " + ", ".join(intents))
        elif default_intents:
            st.caption("Suggested intents: " + ", ".join(default_intents[:max_intents]))
        run_market_search = st.button("Find market opportunities", type="primary", width="stretch")

    if not run_market_search:
        st.info("Click the button above to search YouTube and calculate opportunity scores.")
        return

    if not intents:
        st.error("No search intents found. Add seed keywords or write a next video description in the sidebar.")
        return

    with st.spinner("Searching YouTube market videos and calculating opportunity scores..."):
        market_videos, search_errors = search_market_videos(
            intents,
            api_key,
            days,
            max_results,
            order,
            region_code.strip().upper() or "IN",
            relevance_language.strip() or "hi",
        )
        opportunity_scores = score_search_intents(
            own_channel["title"],
            all_videos,
            market_videos,
            days,
        )

    if search_errors:
        with st.expander("Some search intents had API errors"):
            for error in search_errors:
                st.warning(error)

    if opportunity_scores.empty:
        st.warning("No market videos found for these intents. Try broader seed keywords or a longer recency window.")
        return

    st.markdown("#### Top keyword / search intent opportunities")
    st.dataframe(
        opportunity_scores,
        hide_index=True,
        column_config={
            "opportunity_score": st.column_config.NumberColumn("Opportunity score", format="%.2f"),
            "competitor_performance": st.column_config.NumberColumn("Competitor performance", format="%.2f"),
            "topic_momentum": st.column_config.NumberColumn("Topic momentum", format="%.2f"),
            "outlier_frequency": st.column_config.NumberColumn("Outlier frequency", format="%.2f"),
            "audience_interest": st.column_config.NumberColumn("Audience interest", format="%.2f"),
            "your_content_gap": st.column_config.NumberColumn("Your content gap", format="%.2f"),
            "recency": st.column_config.NumberColumn("Recency", format="%.2f"),
            "best_market_views": st.column_config.NumberColumn("Best market views", format="%d"),
            "best_market_url": st.column_config.LinkColumn("Best market URL"),
        },
    )

    st.markdown("#### Market video evidence")
    evidence = market_video_evidence_sheet(market_videos)
    st.dataframe(
        evidence,
        hide_index=True,
        column_config={
            "views": st.column_config.NumberColumn("Total views", format="%d"),
            "views_per_day": st.column_config.NumberColumn("Views per day", format="%.2f"),
            "url": st.column_config.LinkColumn("Video URL"),
        },
    )

    st.markdown("#### Download opportunity sheets")
    with st.container(horizontal=True):
        st.download_button(
            "Download opportunity scores CSV",
            opportunity_scores.to_csv(index=False).encode("utf-8"),
            file_name="youtube_opportunity_scores.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download market evidence CSV",
            evidence.to_csv(index=False).encode("utf-8"),
            file_name="youtube_market_video_evidence.csv",
            mime="text/csv",
        )


def render_trend_intelligence(videos: pd.DataFrame) -> None:
    st.markdown("### Trend intelligence")
    st.caption("Select a date range, then compare that range with the previous same-length period.")

    col1, col2 = st.columns(2)
    with col1:
        today = datetime.now(APP_TIMEZONE).date()
        default_start = today - timedelta(days=30)
        selected_range = st.date_input(
            "Trend date range",
            value=(default_start, today),
            max_value=today,
        )
    with col2:
        minimum_current_videos = st.slider("Minimum recent videos per topic", 1, 5, 1)

    if not isinstance(selected_range, tuple) or len(selected_range) != 2:
        st.info("Please select both start and end dates for trend analysis.")
        return

    start_date, end_date = selected_range
    if start_date > end_date:
        st.error("Start date end date se pehle honi chahiye.")
        return

    start_local = datetime.combine(start_date, datetime.min.time(), tzinfo=APP_TIMEZONE)
    end_local = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=APP_TIMEZONE)
    current_window_days = max((end_local - start_local).days, 1)

    try:
        trends, current_df, previous_df = detect_youtube_trends(
            videos,
            current_window_days=current_window_days,
            minimum_current_videos=minimum_current_videos,
            current_start_utc=start_local.astimezone(timezone.utc),
            current_end_utc=end_local.astimezone(timezone.utc),
        )
    except Exception as error:
        st.error(f"Trend analysis failed: {error}")
        return

    if trends.empty:
        st.warning("Not enough recent and previous-window data available for trend detection.")
        return

    st.caption(
        f"Current range: {start_date} to {end_date}. Previous comparison window: previous {current_window_days} day(s)."
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Topics detected", len(trends))
    metric_cols[1].metric("Rapidly rising", int((trends["trend_score"] >= 80).sum()))
    metric_cols[2].metric("Growing topics", int(trends["trend_score"].between(65, 79.99).sum()))
    metric_cols[3].metric("Possible saturation", int((trends["market_signal"] == "Possible saturation").sum()))

    st.markdown("#### Top trending topics")
    display_columns = [
        "trend_topic",
        "trend_score",
        "trend_status",
        "current_video_count",
        "previous_video_count",
        "frequency_growth_pct",
        "views_velocity_growth_pct",
        "current_outliers",
        "channels_covering_topic",
        "trending_keyword_count",
        "top_7_trending_keywords",
        "market_signal",
    ]
    display_df = trends[display_columns].rename(
        columns={
            "trend_topic": "Topic",
            "trend_score": "Trend score",
            "trend_status": "Trend status",
            "current_video_count": "Recent videos",
            "previous_video_count": "Previous videos",
            "frequency_growth_pct": "Publishing growth %",
            "views_velocity_growth_pct": "View velocity growth %",
            "current_outliers": "Recent outliers",
            "channels_covering_topic": "Channels covering",
            "trending_keyword_count": "Trending keyword count",
            "top_7_trending_keywords": "Top 7 trending keywords",
            "market_signal": "Market signal",
        }
    )
    st.dataframe(
        display_df,
        hide_index=True,
        column_config={
            "Trend score": st.column_config.NumberColumn(format="%.1f"),
            "Publishing growth %": st.column_config.NumberColumn(format="%.2f"),
            "View velocity growth %": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    chart_data = trends[["trend_topic", "trend_score"]].set_index("trend_topic")
    st.markdown("#### Trend score chart")
    st.bar_chart(chart_data)

    momentum_data = trends[
        ["trend_topic", "frequency_growth_pct", "views_velocity_growth_pct"]
    ].set_index("trend_topic")
    st.markdown("#### Topic momentum")
    st.bar_chart(momentum_data)

    st.markdown("#### Trending keyword performance")
    keyword_df = trend_keyword_table(current_df, trends["trend_topic"].tolist())
    st.dataframe(
        keyword_df,
        hide_index=True,
        column_config={
            "total_views": st.column_config.NumberColumn("Total views", format="%d"),
            "avg_views_per_day": st.column_config.NumberColumn("Avg views/day", format="%.2f"),
            "best_video_url": st.column_config.LinkColumn("Best video URL"),
        },
    )

    st.markdown("#### Investigate a topic")
    selected_topic = st.selectbox("Choose topic", trends["trend_topic"].tolist())
    selected = trends[trends["trend_topic"] == selected_topic].iloc[0]

    detail_cols = st.columns(3)
    detail_cols[0].metric("Trend score", f"{selected['trend_score']}/100")
    detail_cols[1].metric("Publishing growth", f"{selected['frequency_growth_pct']:.1f}%")
    detail_cols[2].metric("View velocity growth", f"{selected['views_velocity_growth_pct']:.1f}%")
    st.write("Trend status:", selected["trend_status"])
    st.write("Market signal:", selected["market_signal"])
    st.write("Top 7 trending keywords:", selected["top_7_trending_keywords"])

    topic_keyword_df = keyword_df[keyword_df["trend_topic"] == selected_topic].copy()
    if not topic_keyword_df.empty:
        st.markdown("#### Keywords working inside this topic")
        st.dataframe(
            topic_keyword_df.head(20),
            hide_index=True,
            column_config={
                "total_views": st.column_config.NumberColumn("Total views", format="%d"),
                "avg_views_per_day": st.column_config.NumberColumn("Avg views/day", format="%.2f"),
                "best_video_url": st.column_config.LinkColumn("Best video URL"),
            },
        )

    topic_videos = current_df[current_df["trend_topic"] == selected_topic].copy()
    if not topic_videos.empty:
        st.markdown("#### Recent videos driving this trend")
        topic_columns = [
            "channel",
            "title",
            "video_type",
            "views",
            "views_per_day",
            "outlier_score",
            "published_at",
            "url",
        ]
        st.dataframe(
            topic_videos.sort_values("outlier_score", ascending=False)[topic_columns],
            hide_index=True,
            column_config={
                "views": st.column_config.NumberColumn("Total views", format="%d"),
                "views_per_day": st.column_config.NumberColumn("Views per day", format="%.2f"),
                "outlier_score": st.column_config.NumberColumn("Outlier score", format="%.2f"),
                "url": st.column_config.LinkColumn("Video URL"),
            },
        )

    st.markdown("#### Strategic signals")
    for _, row in trends.head(5).iterrows():
        if row["trend_score"] >= 80:
            st.success(
                f"{row['trend_topic']}: rapidly rising. Publishing growth {row['frequency_growth_pct']:.0f}% "
                f"and view velocity growth {row['views_velocity_growth_pct']:.0f}%. "
                f"{int(row['current_outliers'])} recent outlier videos detected."
            )
        elif row["market_signal"] == "Possible saturation":
            st.warning(
                f"{row['trend_topic']}: publishing is increasing but performance is falling. This may indicate saturation."
            )
        elif row["trend_score"] >= 65:
            st.info(f"{row['trend_topic']}: growing topic with trend score {row['trend_score']}/100.")

    with st.container(horizontal=True):
        st.download_button(
            "Download trend intelligence CSV",
            trends.to_csv(index=False).encode("utf-8"),
            file_name="trend_intelligence.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download current trend videos CSV",
            current_df.to_csv(index=False).encode("utf-8"),
            file_name="trend_current_videos.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download trend keyword CSV",
            keyword_df.to_csv(index=False).encode("utf-8"),
            file_name="trend_keywords.csv",
            mime="text/csv",
        )


def render_comment_intelligence(api_key: str, all_videos: pd.DataFrame) -> None:
    st.markdown("### Comment intelligence")
    st.caption(
        "Select videos, fetch top-level YouTube comments, then identify audience questions, requests, complaints, confusion, praise, purchase intent, comparison, and exam anxiety."
    )

    if all_videos.empty:
        st.info("Analyse channels first so videos are available for comment intelligence.")
        return

    control_cols = st.columns(4)
    with control_cols[0]:
        video_list_mode = st.segmented_control(
            "Video list",
            ["High views", "Latest", "Random sample"],
            default="High views",
            key="comment_video_list_mode",
        )
    with control_cols[1]:
        max_comments = st.slider("Comments per video", 20, 300, 100, step=20)
    with control_cols[2]:
        order_label = st.segmented_control(
            "Comment order",
            ["Newest", "Relevant"],
            default="Newest",
            key="comment_order",
        )
    with control_cols[3]:
        time_frame = st.segmented_control(
            "Trend time frame",
            ["Day", "Week", "Month", "Hour of day"],
            default="Day",
            key="comment_time_frame",
        )

    candidate_videos = dedupe_videos(all_videos).copy()
    if video_list_mode == "Latest":
        candidate_videos = candidate_videos.sort_values("published_at", ascending=False).head(100)
    elif video_list_mode == "Random sample":
        candidate_videos = candidate_videos.sample(
            min(100, len(candidate_videos)),
            random_state=23,
        )
    else:
        candidate_videos = candidate_videos.sort_values("views", ascending=False).head(100)

    display_columns = [
        "channel", "title", "video_type", "upload_date", "views", "comments", "views_per_day", "url", "video_id",
    ]
    display_videos = candidate_videos[[column for column in display_columns if column in candidate_videos.columns]]

    st.markdown("#### Select videos for comment analysis")
    event = st.dataframe(
        display_videos,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="comment_video_selector",
        column_config={
            "views": st.column_config.NumberColumn("Total views", format="%d"),
            "comments": st.column_config.NumberColumn("Public comment count", format="%d"),
            "views_per_day": st.column_config.NumberColumn("Views per day", format="%.2f"),
            "url": st.column_config.LinkColumn("Video URL"),
            "video_id": None,
        },
    )
    selected_rows = []
    if event is not None and hasattr(event, "selection"):
        selected_rows = list(event.selection.rows)
    selected_videos = candidate_videos.iloc[selected_rows].copy() if selected_rows else pd.DataFrame()

    selected_count = len(selected_videos)
    st.caption(f"Selected videos: {selected_count}. For quota safety, select up to 20 videos at a time.")

    order = "time" if order_label == "Newest" else "relevance"
    if st.button(
        "Analyse selected comments",
        type="primary",
        disabled=selected_count == 0,
        width="stretch",
    ):
        if not api_key:
            st.error("YouTube API key add karein, tab comments fetch honge.")
        elif selected_count > 20:
            st.error("Please select maximum 20 videos at one time. YouTube API quota safe rahega.")
        else:
            comment_frames = []
            errors = []
            progress = st.progress(0)
            with st.spinner("Fetching and classifying comments..."):
                for index, row in enumerate(selected_videos.itertuples(), start=1):
                    try:
                        fetched = fetch_video_comments(
                            row.video_id,
                            api_key,
                            max_comments=max_comments,
                            order=order,
                        )
                        if fetched.empty:
                            errors.append(
                                {
                                    "video_title": row.title,
                                    "video_url": row.url,
                                    "status": "No public top-level comments returned.",
                                }
                            )
                        else:
                            comment_frames.append(fetched)
                    except Exception as error:
                        errors.append(
                            {
                                "video_title": row.title,
                                "video_url": row.url,
                                "status": str(error),
                            }
                        )
                    progress.progress(index / selected_count)

            raw_comments = pd.concat(comment_frames, ignore_index=True) if comment_frames else pd.DataFrame()
            analysed_comments = enrich_comment_analysis(raw_comments, selected_videos)
            st.session_state["comment_intelligence_result"] = {
                "comments": analysed_comments,
                "errors": pd.DataFrame(errors),
                "selected_video_ids": selected_videos["video_id"].tolist(),
            }

    result = st.session_state.get("comment_intelligence_result")
    if not result:
        st.info("Videos select karke `Analyse selected comments` click karein.")
        return

    comments = result["comments"].copy()
    errors = result["errors"].copy()

    if not errors.empty:
        with st.expander("Videos skipped or API warnings"):
            st.dataframe(
                errors,
                hide_index=True,
                column_config={"video_url": st.column_config.LinkColumn("Video URL")},
            )

    if comments.empty:
        st.warning("Selected videos se comments fetch nahi hue. Comments disabled ho sakte hain ya public comments available nahi hain.")
        return

    comments = comments.dropna(subset=["comment_date"]).copy()
    if comments.empty:
        st.warning("Fetched comments me valid publish date nahi mila, isliye time trend nahi ban pa raha.")
        return

    min_date = comments["comment_date"].min()
    max_date = comments["comment_date"].max()
    date_range = st.date_input(
        "Comment date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="comment_intelligence_date_range",
    )
    if not isinstance(date_range, tuple) or len(date_range) != 2:
        st.info("Please select both start and end dates for comment trend analysis.")
        return

    start_date, end_date = date_range
    filtered_comments = comments[
        (comments["comment_date"] >= start_date) & (comments["comment_date"] <= end_date)
    ].copy()
    if filtered_comments.empty:
        st.warning("Selected comment date range me comments nahi mile.")
        return

    summary = comment_type_summary(filtered_comments)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Comments analysed", len(filtered_comments))
    metric_cols[1].metric("Videos covered", filtered_comments["video_id"].nunique())
    metric_cols[2].metric("Top comment type", summary.iloc[0]["comment_type"])
    question_count = int(filtered_comments["matched_types"].str.contains("Question", na=False).sum())
    metric_cols[3].metric("Questions", question_count)

    st.markdown("#### Comment type summary")
    st.dataframe(
        summary,
        hide_index=True,
        column_config={
            "comments": st.column_config.NumberColumn("Comments", format="%d"),
            "unique_videos": st.column_config.NumberColumn("Videos", format="%d"),
            "avg_likes": st.column_config.NumberColumn("Average likes", format="%.2f"),
            "total_replies": st.column_config.NumberColumn("Total replies", format="%d"),
        },
    )

    trend = comment_time_trend(filtered_comments, time_frame)
    if not trend.empty:
        st.markdown("#### Comment trend by time frame")
        chart_data = trend.pivot_table(
            index="period",
            columns="comment_type",
            values="comments",
            aggfunc="sum",
            fill_value=0,
        )
        st.bar_chart(chart_data)
        st.dataframe(trend, hide_index=True)

    st.markdown("#### Upcoming video ideas from comments")
    st.caption("Top 10 ideas are ranked from comment demand plus related channel title/keyword patterns.")
    idea_df = comment_content_ideas(filtered_comments, all_videos, top_n=10)
    if idea_df.empty:
        st.info("Comments me clear content idea signals nahi mile.")
    else:
        st.dataframe(
            idea_df,
            hide_index=True,
            column_config={
                "idea_rank": st.column_config.NumberColumn("Rank", format="%d"),
                "title_1": st.column_config.TextColumn("Title 1"),
                "title_2": st.column_config.TextColumn("Title 2"),
                "title_3": st.column_config.TextColumn("Title 3"),
                "title_4": st.column_config.TextColumn("Title 4"),
                "title_5": st.column_config.TextColumn("Title 5"),
                "long_tail_keywords": st.column_config.TextColumn("Long-tail keywords"),
                "demand_score": st.column_config.NumberColumn("Demand score", format="%.1f"),
                "comments": st.column_config.NumberColumn("Comments", format="%d"),
                "videos": st.column_config.NumberColumn("Videos", format="%d"),
                "avg_likes": st.column_config.NumberColumn("Average likes", format="%.2f"),
                "total_replies": st.column_config.NumberColumn("Replies", format="%d"),
                "video_url": st.column_config.LinkColumn("Source video URL"),
            },
        )

    st.markdown("#### GLM AI comment strategy report")
    glm_base_url = load_env_value("GLM_BASE_URL") or DEFAULT_GLM_BASE_URL
    glm_model = load_env_value("GLM_MODEL") or DEFAULT_GLM_MODEL
    if not load_glm_api_key():
        st.info("GLM report ke liye sidebar me GLM API key paste karein, ya `.env` me `GLM_API_KEY=your_key` add karein.")
    st.caption(f"Model: {glm_model}. This report uses the already fetched comments and current channel data.")

    if st.button(
        "Generate GLM AI report",
        type="secondary",
        disabled=filtered_comments.empty,
        width="stretch",
    ):
        payload = build_glm_comment_payload(filtered_comments, summary, trend, idea_df, all_videos)
        with st.spinner("Generating GLM comment report..."):
            glm_result = generate_cached_glm_comment_report(
                payload,
                glm_api_cache_key(),
                glm_base_url,
                glm_model,
            )
        st.session_state["glm_comment_report_result"] = {
            "source_id": hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()[:12],
            "payload": payload,
            "result": glm_result,
        }

    payload_for_source = build_glm_comment_payload(filtered_comments, summary, trend, idea_df, all_videos)
    expected_glm_source = hashlib.sha256(
        json.dumps(payload_for_source, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:12]
    glm_session_result = st.session_state.get("glm_comment_report_result", {})
    if glm_session_result.get("source_id") == expected_glm_source:
        glm_result = glm_session_result.get("result", {})
        if glm_result.get("error"):
            st.error(glm_result["error"])
        else:
            glm_report = glm_result.get("report", {})
            if glm_report.get("executive_summary"):
                st.info(glm_report["executive_summary"])

            red_flags = pd.DataFrame(glm_report.get("audience_red_flags", []))
            if not red_flags.empty:
                st.markdown("##### Audience red flags")
                st.dataframe(red_flags, hide_index=True)

            glm_ideas = pd.DataFrame(glm_report.get("video_ideas", []))
            if not glm_ideas.empty:
                st.markdown("##### GLM recommended 10 video ideas")
                st.dataframe(
                    glm_ideas,
                    hide_index=True,
                    column_config={
                        "rank": st.column_config.NumberColumn("Rank", format="%d"),
                        "suggested_title": st.column_config.TextColumn("Suggested title"),
                        "long_tail_keywords": st.column_config.TextColumn("Long-tail keywords"),
                    },
                )

            recommendations = glm_report.get("content_angle_recommendations", [])
            if recommendations:
                st.markdown("##### Content angle recommendations")
                for item in recommendations:
                    st.write(f"- {item}")

            with st.container(horizontal=True):
                st.download_button(
                    "Download GLM report JSON",
                    json.dumps(glm_report, indent=2, ensure_ascii=False).encode("utf-8"),
                    file_name="glm_comment_strategy_report.json",
                    mime="application/json",
                )
                if not red_flags.empty:
                    st.download_button(
                        "Download red flags CSV",
                        red_flags.to_csv(index=False).encode("utf-8"),
                        file_name="glm_comment_red_flags.csv",
                        mime="text/csv",
                    )
                if not glm_ideas.empty:
                    st.download_button(
                        "Download GLM video ideas CSV",
                        glm_ideas.to_csv(index=False).encode("utf-8"),
                        file_name="glm_comment_video_ideas.csv",
                        mime="text/csv",
                    )

    st.markdown("#### Comment examples by type")
    selected_type = st.selectbox("Choose comment type", summary["comment_type"].tolist(), key="comment_type_examples")
    examples = top_comment_examples(filtered_comments, selected_type)
    if examples.empty:
        st.info("Is comment type ke examples selected date range me nahi mile.")
    else:
        st.dataframe(
            examples,
            hide_index=True,
            column_config={
                "comment_likes": st.column_config.NumberColumn("Comment likes", format="%d"),
                "reply_count": st.column_config.NumberColumn("Replies", format="%d"),
                "video_url": st.column_config.LinkColumn("Video URL"),
            },
        )

    st.markdown("#### Full classified comments")
    comment_columns = [
        "comment_type", "matched_types", "channel", "video_title", "comment_text",
        "comment_likes", "reply_count", "comment_date", "video_url",
    ]
    st.dataframe(
        filtered_comments[comment_columns].sort_values("comment_date", ascending=False),
        hide_index=True,
        column_config={
            "comment_likes": st.column_config.NumberColumn("Comment likes", format="%d"),
            "reply_count": st.column_config.NumberColumn("Replies", format="%d"),
            "video_url": st.column_config.LinkColumn("Video URL"),
        },
    )

    with st.container(horizontal=True):
        st.download_button(
            "Download classified comments CSV",
            filtered_comments.to_csv(index=False).encode("utf-8"),
            file_name="comment_intelligence_classified_comments.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download comment type summary CSV",
            summary.to_csv(index=False).encode("utf-8"),
            file_name="comment_intelligence_summary.csv",
            mime="text/csv",
        )
        if not trend.empty:
            st.download_button(
                "Download comment trend CSV",
                trend.to_csv(index=False).encode("utf-8"),
                file_name="comment_intelligence_time_trend.csv",
                mime="text/csv",
            )
        if not idea_df.empty:
            st.download_button(
                "Download content ideas CSV",
                idea_df.to_csv(index=False).encode("utf-8"),
                file_name="comment_intelligence_content_ideas.csv",
                mime="text/csv",
            )


def render_packaging_report(
    result: Dict,
    title: str,
    thumbnail_url: str,
    video_url: str,
    views: int,
    views_per_day: float,
    videos_for_rank: pd.DataFrame,
    download_prefix: str,
) -> None:
    title_analysis = result["title_analysis"]
    thumbnail_analysis = result["thumbnail_analysis"]
    packaging_score = result["packaging_score"]
    youtube_fit_report, similar_videos = build_youtube_data_fit_report(title, videos_for_rank, packaging_score)

    st.divider()
    st.markdown("#### Packaging intelligence score")
    score_cols = st.columns(6)
    score_cols[0].metric("Packaging score", f"{packaging_score}/100")
    score_cols[1].metric("Title clarity", f"{title_analysis['clarity_score']}/10")
    score_cols[2].metric("Title curiosity", f"{title_analysis['curiosity_score']}/10")
    score_cols[3].metric("Readability", f"{thumbnail_analysis['readability_score']}/10")
    score_cols[4].metric("Hierarchy", f"{thumbnail_analysis['visual_hierarchy_score']}/10")
    score_cols[5].metric("Redundancy", redundancy_label(thumbnail_analysis["redundancy_score"]))

    st.markdown("#### YouTube data ranking")
    rank_cols = st.columns(5)
    rank_cols[0].metric("Data fit score", f"{youtube_fit_report['youtube_data_fit_score']}/100")
    rank_cols[1].metric("Rank band", youtube_fit_report["rank_band"])
    rank_cols[2].metric("Keyword fit", f"{youtube_fit_report['keyword_score']}/100")
    rank_cols[3].metric("Hook fit", f"{youtube_fit_report['hook_score']}/100")
    rank_cols[4].metric("Length fit", f"{youtube_fit_report['length_bucket_score']}/100")
    st.caption(youtube_fit_report["benchmark_note"])
    st.caption(
        f"Benchmark used: {youtube_fit_report['benchmark_videos']} videos from {youtube_fit_report['benchmark_channels']} channels."
    )
    st.write("Matched keywords:", youtube_fit_report["matched_keywords"])
    st.write("Matched hooks:", youtube_fit_report["matched_hooks"])

    if not similar_videos.empty:
        st.markdown("##### Similar high-performing videos from analysed data")
        st.dataframe(
            similar_videos,
            hide_index=True,
            column_config={
                "views": st.column_config.NumberColumn("Views", format="%d"),
                "views_per_day": st.column_config.NumberColumn("Views/day", format="%.2f"),
                "url": st.column_config.LinkColumn("Video URL"),
            },
        )

    if thumbnail_analysis.get("analysis_error"):
        st.warning(thumbnail_analysis["analysis_error"])

    title_labels = {
        "title_length": "Title length",
        "word_count": "Word count",
        "has_number": "Has number?",
        "has_question": "Has question?",
        "has_year": "Has year?",
        "hook_type": "Hook type",
        "hook_words": "Hook words",
        "curiosity_score": "Curiosity",
        "clarity_score": "Clarity",
        "specificity_score": "Specificity",
        "urgency_score": "Urgency",
        "emotion_score": "Emotion",
        "orientation": "Search vs browse",
    }
    thumbnail_labels = {
        "visible_text": "Visible text",
        "thumbnail_text_word_count": "Thumbnail text word count",
        "face_present": "Face present?",
        "approximate_face_count": "Approximate face count",
        "dominant_emotion": "Dominant emotion",
        "visual_clutter_score": "Visual clutter",
        "readability_score": "Readability",
        "visual_hierarchy_score": "Visual hierarchy",
        "thumbnail_curiosity_score": "Thumbnail curiosity",
        "simplicity_score": "Simplicity",
        "thumbnail_style": "Thumbnail style",
    }
    relationship_labels = {
        "alignment_score": "Title-thumbnail alignment",
        "complementarity_score": "Complementarity",
        "redundancy_score": "Redundancy",
        "curiosity_gap_score": "Curiosity gap",
        "message_clarity_score": "Message clarity",
    }

    analysis_cols = st.columns(3)
    with analysis_cols[0]:
        st.markdown("#### Title analysis")
        st.dataframe(analysis_dict_to_frame(title_analysis, title_labels), hide_index=True)
    with analysis_cols[1]:
        st.markdown("#### Thumbnail analysis")
        st.dataframe(analysis_dict_to_frame(thumbnail_analysis, thumbnail_labels), hide_index=True)
    with analysis_cols[2]:
        st.markdown("#### Title-thumbnail relationship")
        st.dataframe(analysis_dict_to_frame(thumbnail_analysis, relationship_labels), hide_index=True)

    st.markdown("#### AI recommendation")
    rec_cols = st.columns(3)
    with rec_cols[0]:
        st.markdown("##### Strengths")
        strengths = thumbnail_analysis.get("strengths", [])
        if strengths:
            for item in strengths[:3]:
                st.write(f"- {item}")
        else:
            st.write("No AI strengths available yet.")
    with rec_cols[1]:
        st.markdown("##### Weaknesses")
        weaknesses = thumbnail_analysis.get("weaknesses", [])
        if weaknesses:
            for item in weaknesses[:3]:
                st.write(f"- {item}")
        else:
            st.write("No AI weaknesses available yet.")
    with rec_cols[2]:
        st.markdown("##### Recommendations")
        recommendations = thumbnail_analysis.get("recommendations", [])
        if recommendations:
            for item in recommendations[:3]:
                st.write(f"- {item}")
        else:
            st.write("No AI recommendations available yet.")

    suggestion_cols = st.columns(2)
    with suggestion_cols[0]:
        st.markdown("#### Improved title")
        st.success(thumbnail_analysis.get("improved_title") or "Not available")
    with suggestion_cols[1]:
        st.markdown("#### Thumbnail text / angle")
        st.success(thumbnail_analysis.get("thumbnail_text_angle") or "Not available")

    export_payload = {
        "title": title,
        "thumbnail_url": thumbnail_url,
        "video_url": video_url,
        "views": views,
        "views_per_day": views_per_day,
        "packaging_intelligence_score": packaging_score,
        "youtube_data_fit_report": youtube_fit_report,
        "title_analysis": title_analysis,
        "thumbnail_analysis": thumbnail_analysis,
    }
    st.download_button(
        "Download packaging analysis JSON",
        json.dumps(export_payload, indent=2, ensure_ascii=False).encode("utf-8"),
        file_name=f"{download_prefix}_packaging_analysis.json",
        mime="application/json",
    )


def render_uploaded_thumbnail_report(result: Dict, title: str, download_prefix: str) -> None:
    validation = result.get("validation", {})
    analysis = result.get("analysis", {})

    if validation:
        with st.expander("Image validation", expanded=not result.get("ok", False)):
            validation_rows = [
                {"Check": "File name", "Value": validation.get("filename", "")},
                {"Check": "File type", "Value": validation.get("mime_type", "")},
                {"Check": "Format", "Value": validation.get("format", "")},
                {"Check": "File size", "Value": f"{validation.get('file_size_mb', 0)} MB"},
                {"Check": "Dimensions", "Value": f"{validation.get('width', 0)} x {validation.get('height', 0)} px"},
                {"Check": "Aspect ratio", "Value": validation.get("aspect_ratio", 0)},
            ]
            st.dataframe(pd.DataFrame(validation_rows), hide_index=True)
            for warning in validation.get("warnings", []):
                st.warning(warning)

    if not result.get("ok"):
        st.error(result.get("error") or "Thumbnail analysis failed.")
        return

    packaging_score = result.get("packaging_score", calculate_uploaded_thumbnail_packaging_score(analysis))
    st.divider()
    st.markdown("#### Packaging intelligence score")
    score_cols = st.columns(5)
    score_cols[0].metric("Packaging score", f"{packaging_score}/100")
    score_cols[1].metric("Alignment", f"{analysis.get('title_thumbnail_alignment_score', 0)}/10")
    score_cols[2].metric("Complementarity", f"{analysis.get('complementarity_score', 0)}/10")
    score_cols[3].metric("Readability", f"{analysis.get('readability_score', 0)}/10")
    score_cols[4].metric("Redundancy", redundancy_label(int(round(analysis.get("redundancy_score", 0)))))

    title_analysis = deterministic_title_analysis(title)
    title_labels = {
        "title_length": "Title length",
        "word_count": "Word count",
        "has_number": "Has number?",
        "has_question": "Has question?",
        "has_year": "Has year?",
        "hook_type": "Hook type",
        "hook_words": "Hook words",
        "curiosity_score": "Title curiosity",
        "clarity_score": "Title clarity",
        "specificity_score": "Specificity",
        "urgency_score": "Title urgency",
        "emotion_score": "Emotion",
        "orientation": "Search vs browse",
    }
    thumbnail_labels = {
        "thumbnail_text": "Thumbnail text",
        "face_present": "Face present?",
        "face_count": "Face count",
        "dominant_emotion": "Dominant emotion",
        "main_subject": "Main subject",
        "thumbnail_style": "Thumbnail style",
        "readability_score": "Readability",
        "visual_hierarchy_score": "Visual hierarchy",
        "clutter_score": "Clutter",
        "curiosity_score": "Thumbnail curiosity",
        "urgency_score": "Thumbnail urgency",
        "mobile_readability_score": "Mobile readability",
    }
    relationship_labels = {
        "title_thumbnail_alignment_score": "Title-thumbnail alignment",
        "complementarity_score": "Complementarity",
        "redundancy_score": "Redundancy",
        "curiosity_gap_score": "Curiosity gap",
    }

    analysis_cols = st.columns(3)
    with analysis_cols[0]:
        st.markdown("#### Title analysis")
        st.dataframe(analysis_dict_to_frame(title_analysis, title_labels), hide_index=True)
    with analysis_cols[1]:
        st.markdown("#### Thumbnail analysis")
        st.dataframe(analysis_dict_to_frame(analysis, thumbnail_labels), hide_index=True)
    with analysis_cols[2]:
        st.markdown("#### Title-thumbnail relationship")
        st.dataframe(analysis_dict_to_frame(analysis, relationship_labels), hide_index=True)

    detail_scores = [
        ("Visual hierarchy", analysis.get("visual_hierarchy_score", 0)),
        ("Curiosity", analysis.get("curiosity_score", 0)),
        ("Mobile readability", analysis.get("mobile_readability_score", 0)),
        ("Urgency", analysis.get("urgency_score", 0)),
        ("Clutter", analysis.get("clutter_score", 0)),
        ("Curiosity gap", analysis.get("curiosity_gap_score", 0)),
    ]
    score_card_cols = st.columns(6)
    for index, (label, value) in enumerate(detail_scores):
        score_card_cols[index].metric(label, f"{value}/10")

    st.markdown("#### AI recommendations")
    rec_cols = st.columns(3)
    with rec_cols[0]:
        st.markdown("##### Strengths")
        for item in analysis.get("strengths", []) or ["No strengths returned."]:
            st.write(f"- {item}")
    with rec_cols[1]:
        st.markdown("##### Problems")
        for item in analysis.get("problems", []) or ["No problems returned."]:
            st.write(f"- {item}")
    with rec_cols[2]:
        st.markdown("##### Recommendations")
        for item in analysis.get("recommendations", []) or ["No recommendations returned."]:
            st.write(f"- {item}")

    export_payload = {
        "title": title,
        "packaging_intelligence_score": packaging_score,
        "validation": validation,
        "title_analysis": title_analysis,
        "thumbnail_analysis": analysis,
    }
    st.download_button(
        "Download uploaded thumbnail analysis JSON",
        json.dumps(export_payload, indent=2, ensure_ascii=False).encode("utf-8"),
        file_name=f"{download_prefix}_uploaded_thumbnail_analysis.json",
        mime="application/json",
    )


def render_monthly_competitor_report(competitor_videos: pd.DataFrame, analysis_start_date: str, analysis_end_date: str) -> None:
    st.markdown("### Monthly competitor content report")
    st.caption("Month-wise competitor publishing, views, upload dates, keywords, tags, and trend charts from the selected analysis date range.")

    if competitor_videos.empty:
        st.info("Selected date range me competitor videos nahi mile. Sidebar me competitors add karke wider range ke saath `Analyse channels` click karein.")
        return

    videos = prepare_video_frame(dedupe_videos(competitor_videos)).copy()
    if videos.empty:
        st.warning("Competitor video data empty hai.")
        return

    st.info(f"Current report range: {analysis_start_date} to {analysis_end_date}. Change this from sidebar and click `Analyse channels` again.")

    channel_options = sorted(videos["channel"].dropna().astype(str).unique().tolist())
    selected_channel_titles = st.multiselect(
        "Competitor channels",
        options=channel_options,
        default=channel_options,
        help="Select channels from the already fetched competitor dataset.",
    )
    top_terms_per_month = st.slider("Top terms/month", 5, 20, 10, key="monthly_report_top_terms")
    if not selected_channel_titles:
        st.warning("At least one competitor channel select karein.")
        return

    videos = videos[videos["channel"].astype(str).isin(selected_channel_titles)].copy()

    summary = build_monthly_competitor_summary(videos)
    keyword_report = build_monthly_term_report(videos, "keyword", top_n_per_month=top_terms_per_month)
    tag_report = build_monthly_term_report(videos, "tag", top_n_per_month=top_terms_per_month)
    chart_granularity = st.segmented_control(
        "Trend chart granularity",
        ["Daily upload date", "Month wise"],
        default="Daily upload date",
        key="monthly_competitor_chart_granularity",
    )
    trend_data = build_competitor_time_trend(videos, chart_granularity)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Videos fetched", videos["video_id"].nunique())
    metric_cols[1].metric("Competitors", videos["channel"].nunique())
    metric_cols[2].metric("Total views", format_number(int(videos["views"].sum())))
    metric_cols[3].metric("Months covered", summary["month"].nunique() if not summary.empty else 0)

    if not trend_data.empty:
        st.markdown("#### Interactive upload and views trend")
        tooltip = [
            alt.Tooltip("period_label:N", title="Period"),
            alt.Tooltip("channel:N", title="Channel"),
            alt.Tooltip("videos_uploaded:Q", title="Videos uploaded"),
            alt.Tooltip("total_views:Q", title="Total views", format=","),
            alt.Tooltip("avg_views:Q", title="Avg views", format=",.2f"),
            alt.Tooltip("avg_views_per_day:Q", title="Avg views/day", format=",.2f"),
        ]
        upload_chart = (
            alt.Chart(trend_data)
            .mark_line(point=True)
            .encode(
                x=alt.X("period:T", title="Upload date" if chart_granularity == "Daily upload date" else "Month"),
                y=alt.Y("videos_uploaded:Q", title="Videos uploaded"),
                color=alt.Color("channel:N", title="Competitor"),
                tooltip=tooltip,
            )
            .interactive()
            .properties(height=320)
        )
        views_chart = (
            alt.Chart(trend_data)
            .mark_line(point=True)
            .encode(
                x=alt.X("period:T", title="Upload date" if chart_granularity == "Daily upload date" else "Month"),
                y=alt.Y("total_views:Q", title="Total views"),
                color=alt.Color("channel:N", title="Competitor"),
                tooltip=tooltip,
            )
            .interactive()
            .properties(height=320)
        )
        chart_cols = st.columns(2)
        with chart_cols[0]:
            st.altair_chart(upload_chart)
        with chart_cols[1]:
            st.altair_chart(views_chart)

        st.markdown("##### Chart data")
        st.dataframe(
            trend_data,
            hide_index=True,
            column_config={
                "period": st.column_config.DatetimeColumn("Period", format="YYYY-MM-DD"),
                "videos_uploaded": st.column_config.NumberColumn("Videos uploaded", format="%d"),
                "total_views": st.column_config.NumberColumn("Total views", format="%d"),
                "avg_views": st.column_config.NumberColumn("Avg views", format="%.2f"),
                "avg_views_per_day": st.column_config.NumberColumn("Avg views/day", format="%.2f"),
            },
        )

    st.markdown("#### Month-wise publishing and views")
    st.dataframe(
        summary,
        hide_index=True,
        column_config={
            "total_views": st.column_config.NumberColumn("Total views", format="%d"),
            "avg_views": st.column_config.NumberColumn("Avg views", format="%.2f"),
            "avg_views_per_day": st.column_config.NumberColumn("Avg views/day", format="%.2f"),
            "top_video_views": st.column_config.NumberColumn("Top video views", format="%d"),
            "top_video_url": st.column_config.LinkColumn("Top video URL"),
        },
    )

    st.markdown("#### Month-wise trending keywords")
    st.dataframe(
        keyword_report,
        hide_index=True,
        column_config={
            "total_views": st.column_config.NumberColumn("Total views", format="%d"),
            "avg_views_per_day": st.column_config.NumberColumn("Avg views/day", format="%.2f"),
            "best_url": st.column_config.LinkColumn("Best video URL"),
        },
    )

    st.markdown("#### Month-wise trending tags")
    st.dataframe(
        tag_report,
        hide_index=True,
        column_config={
            "total_views": st.column_config.NumberColumn("Total views", format="%d"),
            "avg_views_per_day": st.column_config.NumberColumn("Avg views/day", format="%.2f"),
            "best_url": st.column_config.LinkColumn("Best video URL"),
        },
    )

    st.markdown("#### All videos with upload dates")
    video_sheet = uploaded_videos_export_sheet(videos)
    st.dataframe(
        video_sheet,
        hide_index=True,
        column_config={
            "upload_date": st.column_config.DateColumn("Upload date"),
            "views": st.column_config.NumberColumn("Views", format="%d"),
            "likes": st.column_config.NumberColumn("Likes", format="%d"),
            "comments": st.column_config.NumberColumn("Comments", format="%d"),
            "views_per_day": st.column_config.NumberColumn("Views/day", format="%.2f"),
            "video_age_days": st.column_config.NumberColumn("Video age days", format="%.1f"),
            "duration_minutes": st.column_config.NumberColumn("Duration minutes", format="%.2f"),
            "url": st.column_config.LinkColumn("Video URL"),
            "thumbnail": st.column_config.ImageColumn("Thumbnail"),
        },
    )

    with st.container(horizontal=True):
        st.download_button(
            "Download monthly summary CSV",
            summary.to_csv(index=False).encode("utf-8"),
            file_name="monthly_competitor_summary.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download monthly keywords CSV",
            keyword_report.to_csv(index=False).encode("utf-8"),
            file_name="monthly_competitor_keywords.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download monthly tags CSV",
            tag_report.to_csv(index=False).encode("utf-8"),
            file_name="monthly_competitor_tags.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download selected-range video sheet CSV",
            video_sheet.to_csv(index=False).encode("utf-8"),
            file_name="selected_date_range_competitor_uploaded_videos.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download chart data CSV",
            trend_data.to_csv(index=False).encode("utf-8"),
            file_name="monthly_competitor_trend_chart_data.csv",
            mime="text/csv",
        )


def render_title_thumbnail_analyzer(all_videos: pd.DataFrame) -> None:
    st.markdown("### Title + Thumbnail Analyzer")
    st.caption("Analyse an existing video package or upload your own title + thumbnail. This is packaging intelligence, not CTR prediction.")

    if all_videos.empty:
        st.info("Analyse channels first for existing-video benchmarking, or upload your own title + thumbnail below.")
        videos = pd.DataFrame()
    else:
        videos = prepare_video_frame(dedupe_videos(all_videos)).copy()

    if not videos.empty:
        for column, default in {
            "thumbnail": "",
            "title": "",
            "channel": "",
            "video_type": "",
            "upload_date": "",
            "views": 0,
            "views_per_day": 0.0,
            "video_id": "",
            "url": "",
        }.items():
            if column not in videos.columns:
                videos[column] = default

        videos["views"] = pd.to_numeric(videos["views"], errors="coerce").fillna(0).astype(int)
        videos["views_per_day"] = pd.to_numeric(videos["views_per_day"], errors="coerce").fillna(0.0).round(2)
        videos = videos.sort_values(["views", "views_per_day"], ascending=False).reset_index(drop=True)
        videos["selector_label"] = videos.apply(
            lambda row: f"{row['channel']} | {format_number(int(row['views']))} views | {row['title']}",
            axis=1,
        )

    mode_options = ["Upload title + thumbnail"] if videos.empty else ["Existing video", "Upload title + thumbnail"]
    mode = st.segmented_control(
        "Analysis mode",
        mode_options,
        default=mode_options[0],
    )

    if not load_openai_api_key():
        st.info("Thumbnail semantic analysis ke liye sidebar me OpenAI API key paste karein, ya project `.env` file me `OPENAI_API_KEY=your_key` add karein. Title analysis deterministic Python se chalega.")

    if mode == "Upload title + thumbnail":
        st.markdown("#### Upload your package")
        input_cols = st.columns([2, 1])
        with input_cols[0]:
            custom_title = st.text_input(
                "Your video title",
                placeholder="Example: 7 CAT Mistakes Killing Your Percentile",
                key="custom_package_title",
            )
        with input_cols[1]:
            uploaded_thumbnail = st.file_uploader(
                "Upload thumbnail",
                type=["jpg", "jpeg", "png"],
                key="custom_package_thumbnail",
            )

        if uploaded_thumbnail is not None:
            image_bytes = uploaded_thumbnail.getvalue()
            mime_type = uploaded_thumbnail.type or "image/jpeg"
            image_hash = hashlib.sha256(image_bytes).hexdigest()[:12]
            st.image(image_bytes, caption="Uploaded thumbnail")
            image_validation = validate_thumbnail_image(image_bytes, uploaded_thumbnail.name, mime_type)
            if image_validation["valid"]:
                st.success("Thumbnail file validated.")
            else:
                for error in image_validation["errors"]:
                    st.error(error)
            for warning in image_validation["warnings"]:
                st.warning(warning)
        else:
            image_bytes = b""
            mime_type = "image/jpeg"
            image_hash = "no_image"
            image_validation = {}
            st.info("Upload a thumbnail image to run full title + thumbnail analysis.")

        if st.button("Analyze Thumbnail", type="primary", width="stretch"):
            if not custom_title.strip():
                st.error("Please enter your video title.")
            elif not image_bytes:
                st.error("Please upload a thumbnail image.")
            elif image_validation and not image_validation["valid"]:
                st.error("Please fix the thumbnail validation errors before analysis.")
            else:
                with st.spinner("Analysing your uploaded title and thumbnail..."):
                    model = load_env_value("OPENAI_VISION_MODEL") or DEFAULT_OPENAI_VISION_MODEL
                    analysis_result = analyze_uploaded_thumbnail_with_sdk(
                        custom_title,
                        image_bytes,
                        uploaded_thumbnail.name,
                        mime_type,
                        openai_api_cache_key(),
                        model,
                    )
                    st.session_state["custom_title_thumbnail_analysis_result"] = {
                        "source_id": f"{image_hash}_{hashlib.sha256(custom_title.encode('utf-8')).hexdigest()[:8]}",
                        "title": custom_title,
                        "analysis_result": analysis_result,
                    }

        result = st.session_state.get("custom_title_thumbnail_analysis_result", {})
        expected_source_id = (
            f"{image_hash}_{hashlib.sha256(custom_title.encode('utf-8')).hexdigest()[:8]}"
            if custom_title and uploaded_thumbnail is not None
            else ""
        )
        if result.get("source_id") != expected_source_id:
            st.info("Click the analyzer button to generate this uploaded package report.")
            return

        render_uploaded_thumbnail_report(
            result.get("analysis_result", {}),
            custom_title,
            f"uploaded_title_thumbnail_{image_hash}",
        )
        return

    st.markdown("#### Select existing video")
    selected_label = st.selectbox(
        "Video",
        videos["selector_label"].tolist(),
        index=0,
        help="This list uses videos already loaded in the app. It does not make a new YouTube API call.",
    )
    selected_row = videos[videos["selector_label"] == selected_label].iloc[0]

    preview_columns = [
        "thumbnail", "channel", "title", "video_type", "upload_date",
        "views", "views_per_day", "url",
    ]
    st.dataframe(
        videos[preview_columns].head(100),
        hide_index=True,
        column_config={
            "thumbnail": st.column_config.ImageColumn("Thumbnail"),
            "views": st.column_config.NumberColumn("Total views", format="%d"),
            "views_per_day": st.column_config.NumberColumn("Views/day", format="%.2f"),
            "url": st.column_config.LinkColumn("Video URL"),
        },
    )

    title = str(selected_row.get("title") or "")
    thumbnail_value = selected_row.get("thumbnail", "")
    thumbnail_url = "" if pd.isna(thumbnail_value) else str(thumbnail_value).strip()
    video_id = str(selected_row.get("video_id") or "")
    url_value = selected_row.get("url", "")
    video_url = "" if pd.isna(url_value) else str(url_value).strip()
    views = int(selected_row.get("views") or 0)
    views_per_day = float(selected_row.get("views_per_day") or 0.0)
    outlier_value = selected_row.get("outlier_score", "Not available")
    if pd.isna(outlier_value):
        outlier_value = "Not available"

    preview_left, preview_right = st.columns([1, 2])
    with preview_left:
        if thumbnail_url and thumbnail_url.lower() != "nan":
            st.image(thumbnail_url, caption="Selected thumbnail")
        else:
            st.warning("Thumbnail missing for this video.")
    with preview_right:
        st.markdown("#### Current package")
        st.write(title)
        metric_cols = st.columns(4)
        metric_cols[0].metric("Views", format_number(views))
        metric_cols[1].metric("Views/day", f"{views_per_day:,.2f}")
        metric_cols[2].metric("Format", str(selected_row.get("video_type") or "Unknown"))
        metric_cols[3].metric("Outlier score", outlier_value)
        if video_url and video_url.lower() != "nan":
            st.link_button("Open video", video_url)

    title_analysis = deterministic_title_analysis(title)
    if st.button("Analyze title + thumbnail package", type="primary", width="stretch"):
        with st.spinner("Analysing title, thumbnail, and packaging relationship..."):
            thumbnail_analysis = analyze_thumbnail_with_ai(
                title,
                thumbnail_url,
                video_id,
                views,
                views_per_day,
                openai_api_cache_key(),
            )
            st.session_state["title_thumbnail_analysis_result"] = {
                "video_id": video_id,
                "title": title,
                "title_analysis": title_analysis,
                "thumbnail_analysis": thumbnail_analysis,
                "packaging_score": packaging_intelligence_score(title_analysis, thumbnail_analysis),
            }

    result = st.session_state.get("title_thumbnail_analysis_result", {})
    if result.get("video_id") != video_id:
        st.info("Click the analyzer button to generate this video's packaging report.")
        return

    render_packaging_report(
        result,
        title,
        thumbnail_url,
        video_url,
        views,
        views_per_day,
        videos,
        f"title_thumbnail_analysis_{video_id or 'video'}",
    )


def render_what_should_we_post_next(
    api_key: str,
    own_channel: Dict,
    all_videos: pd.DataFrame,
    video_description: str,
) -> None:
    st.markdown("### What should we post next?")
    st.caption(
        "Combines your channel, competitors, recent outliers, trend intelligence, content gaps, comment intelligence, and optional live YouTube search evidence."
    )

    if all_videos.empty:
        st.info("Analyse channels first to generate post recommendations.")
        return

    default_niche_keywords = infer_niche_keywords(all_videos)
    with st.container(border=True):
        st.markdown("#### Niche/category filter")
        strict_niche_filter = st.toggle(
            "Show only this channel type/category",
            value=True,
            help="Filters recommendations and live YouTube search evidence so unrelated categories do not enter the score.",
        )
        niche_keywords_text = st.text_area(
            "Niche/category keywords",
            value=", ".join(default_niche_keywords),
            height=90,
            help="Edit these keywords if the auto-detected niche is too broad or too narrow.",
        )
        niche_keywords = parse_niche_keywords(niche_keywords_text)

    recommendation_videos = filter_videos_by_niche(all_videos, niche_keywords) if strict_niche_filter else all_videos.copy()
    if strict_niche_filter and recommendation_videos.empty:
        st.warning("Niche/category filter ke baad videos nahi mile. Keywords thode broad karein.")
        return

    comment_result = st.session_state.get("comment_intelligence_result", {})
    comment_comments = comment_result.get("comments", pd.DataFrame())
    if isinstance(comment_comments, pd.DataFrame) and not comment_comments.empty:
        comment_comments = comment_comments.dropna(subset=["comment_date"]).copy()
        if strict_niche_filter:
            comment_comments = comment_comments[
                comment_comments.apply(
                    lambda row: text_matches_niche(
                        f"{row.get('video_title', '')} {row.get('comment_text', '')} {row.get('comment_type', '')}",
                        niche_keywords,
                    ),
                    axis=1,
                )
            ].copy()

    stored_market_scores = st.session_state.get("next_post_market_scores", pd.DataFrame())
    stored_market_videos = st.session_state.get("next_post_market_videos", pd.DataFrame())
    stored_errors = st.session_state.get("next_post_market_errors", [])
    filtered_market_scores = (
        filter_market_scores_by_niche(stored_market_scores, niche_keywords)
        if strict_niche_filter and isinstance(stored_market_scores, pd.DataFrame)
        else stored_market_scores
    )
    filtered_market_videos = (
        filter_videos_by_niche(stored_market_videos, niche_keywords)
        if strict_niche_filter and isinstance(stored_market_videos, pd.DataFrame)
        else stored_market_videos
    )

    base_recommendations = build_next_post_recommendations(
        own_channel["title"],
        recommendation_videos,
        comments=comment_comments if isinstance(comment_comments, pd.DataFrame) else None,
        market_scores=filtered_market_scores if isinstance(filtered_market_scores, pd.DataFrame) else None,
        top_n=10,
    )

    if base_recommendations.empty:
        st.warning("Recommendation banane ke liye enough signals nahi mile.")
        return

    metric_cols = st.columns(4)
    metric_cols[0].metric("Ideas ranked", len(base_recommendations))
    metric_cols[1].metric("Videos analysed", dedupe_videos(recommendation_videos)["video_id"].nunique())
    metric_cols[2].metric("Channels analysed", recommendation_videos["channel"].nunique())
    metric_cols[3].metric("Comment signals", len(comment_comments) if isinstance(comment_comments, pd.DataFrame) else 0)

    st.markdown("#### Final recommendation board")
    st.dataframe(
        base_recommendations,
        hide_index=True,
        column_config={
            "rank": st.column_config.NumberColumn("Rank", format="%d"),
            "final_score": st.column_config.NumberColumn("Final score", format="%.1f"),
            "trend_score": st.column_config.NumberColumn("Trend", format="%.1f"),
            "gap_score": st.column_config.NumberColumn("Gap", format="%.1f"),
            "outlier_score": st.column_config.NumberColumn("Outlier", format="%.1f"),
            "comment_score": st.column_config.NumberColumn("Comments", format="%.1f"),
            "search_score": st.column_config.NumberColumn("Search", format="%.1f"),
            "competitor_score": st.column_config.NumberColumn("Competitor", format="%.1f"),
            "proof_views": st.column_config.NumberColumn("Proof views", format="%d"),
            "proof_url": st.column_config.LinkColumn("Proof video URL"),
        },
    )

    top_pick = base_recommendations.iloc[0]
    st.markdown("#### Best next post")
    st.success(f"{top_pick['what_should_we_post']} - score {top_pick['final_score']}/100")
    st.write("Recommended title:", top_pick["title_1"])
    st.write("Long-tail keywords:", top_pick["long_tail_keywords"])
    st.write("Why:", top_pick["why_post_next"])

    st.markdown("#### Live YouTube search validation")
    st.caption("This button uses YouTube Search API for recent market videos. Use it when you want ongoing YouTube demand included.")
    search_cols = st.columns(4)
    with search_cols[0]:
        search_days = st.selectbox("Search window", [7, 14, 30, 90], index=1, format_func=lambda days: f"Last {days} days")
    with search_cols[1]:
        max_results = st.slider("Results per idea", 3, 10, 5)
    with search_cols[2]:
        search_order = st.segmented_control("Search order", ["date", "relevance", "viewCount"], default="date")
    with search_cols[3]:
        region_code = st.text_input("Region", value="IN", max_chars=2)

    extra_seeds = st.text_area(
        "Extra search topics",
        value=video_description.strip(),
        placeholder="Optional: add extra topics, one per line",
        height=90,
    )
    search_intents = base_recommendations["recommended_topic"].head(8).tolist()
    for seed in parse_seed_intents(extra_seeds):
        if seed not in search_intents and (not strict_niche_filter or text_matches_niche(seed, niche_keywords)):
            search_intents.append(seed)
    search_intents = search_intents[:10]
    st.caption("Search intents: " + ", ".join(search_intents))

    if st.button("Refresh YouTube search trends for these ideas", type="primary", width="stretch"):
        if not api_key:
            st.error("YouTube API key add karein, tab live search validation chalega.")
        else:
            with st.spinner("Searching recent YouTube videos and scoring opportunities..."):
                market_videos, errors = search_market_videos(
                    search_intents,
                    api_key,
                    days=search_days,
                    max_results_per_intent=max_results,
                    order=search_order,
                    region_code=region_code.upper(),
                    relevance_language="en",
                )
                if strict_niche_filter:
                    market_videos = filter_videos_by_niche(market_videos, niche_keywords)
                market_scores = score_search_intents(
                    own_channel["title"],
                    recommendation_videos,
                    market_videos,
                    days=search_days,
                )
                st.session_state["next_post_market_videos"] = market_videos
                st.session_state["next_post_market_scores"] = market_scores
                st.session_state["next_post_market_errors"] = errors
            st.rerun()

    if isinstance(filtered_market_scores, pd.DataFrame) and not filtered_market_scores.empty:
        st.markdown("#### YouTube search opportunity scores")
        st.dataframe(
            filtered_market_scores,
            hide_index=True,
            column_config={
                "opportunity_score": st.column_config.NumberColumn("Opportunity score", format="%.2f"),
                "best_market_views": st.column_config.NumberColumn("Best market views", format="%d"),
                "best_market_url": st.column_config.LinkColumn("Best market URL"),
            },
        )

    if isinstance(filtered_market_videos, pd.DataFrame) and not filtered_market_videos.empty:
        st.markdown("#### Recent YouTube search evidence")
        st.dataframe(
            market_video_evidence_sheet(filtered_market_videos).head(100),
            hide_index=True,
            column_config={
                "views": st.column_config.NumberColumn("Total views", format="%d"),
                "views_per_day": st.column_config.NumberColumn("Views/day", format="%.2f"),
                "url": st.column_config.LinkColumn("Video URL"),
            },
        )

    if stored_errors:
        with st.expander("YouTube search warnings"):
            for error in stored_errors:
                st.write(error)

    st.markdown("#### Download")
    st.download_button(
        "Download next-post recommendations CSV",
        base_recommendations.to_csv(index=False).encode("utf-8"),
        file_name="what_should_we_post_next.csv",
        mime="text/csv",
    )


def render_keyword_reports_page(all_videos: pd.DataFrame) -> None:
    st.markdown("### Keyword reports")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Top 20 most-used keywords")
        st.dataframe(keyword_table(all_videos, top_n=20), hide_index=True)
    with col2:
        st.markdown("#### Top 20 high-view hook words")
        st.dataframe(hook_table(all_videos, top_n=20), hide_index=True)

    st.markdown("#### Top 20 search tags")
    st.dataframe(tag_table(all_videos, top_n=20), hide_index=True)

    st.markdown("#### Top 20 high-view videos with hooks")
    st.dataframe(
        high_view_hook_videos(all_videos, top_n=20),
        hide_index=True,
        column_config={
            "views": st.column_config.NumberColumn("Total views", format="%d"),
            "url": st.column_config.LinkColumn("Video URL"),
        },
    )

    st.markdown("#### Top performing videos across all channels")
    top_columns = [
        "channel", "title", "video_type", "upload_date", "views", "video_age_days",
        "views_per_day", "title_length", "word_count", "has_number",
        "has_question", "has_year", "keywords", "hook_keywords", "url",
    ]
    available_columns = [column for column in top_columns if column in all_videos.columns]
    st.dataframe(
        all_videos.sort_values("views", ascending=False).head(50)[available_columns],
        hide_index=True,
        column_config={
            "views": st.column_config.NumberColumn("Total views", format="%d"),
            "url": st.column_config.LinkColumn("Video URL"),
        },
    )


def render_downloads_page(
    own_channel: Dict,
    own_videos: pd.DataFrame,
    competitor_channels: List[Dict],
    competitor_videos: pd.DataFrame,
    all_videos: pd.DataFrame,
    video_description: str,
) -> None:
    st.markdown("### Downloads")
    report = build_markdown_report(
        own_channel,
        own_videos,
        competitor_channels,
        competitor_videos,
        all_videos,
        video_description,
    )
    with st.container(horizontal=True):
        st.download_button(
            "Download markdown report",
            report,
            file_name="youtube_strategy_report.md",
            mime="text/markdown",
        )
        st.download_button(
            "Download selected date-range videos CSV",
            uploaded_videos_export_sheet(all_videos).to_csv(index=False).encode("utf-8"),
            file_name="selected_date_range_all_uploaded_videos.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download keyword CSV",
            keyword_table(all_videos, top_n=100).to_csv(index=False).encode("utf-8"),
            file_name="keyword_report.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download hook CSV",
            hook_table(all_videos, top_n=100).to_csv(index=False).encode("utf-8"),
            file_name="hook_keyword_report.csv",
            mime="text/csv",
        )
    with st.container(horizontal=True):
        st.download_button(
            "Download content gap comparison CSV",
            content_gap_pivot_sheet(all_videos).to_csv(index=False).encode("utf-8"),
            file_name="content_gap_channel_comparison.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download content gap video sheet CSV",
            content_gap_video_sheet(all_videos).to_csv(index=False).encode("utf-8"),
            file_name="content_gap_video_sheet.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download content gap opportunities CSV",
            content_gap_opportunities(own_channel["title"], all_videos).to_csv(index=False).encode("utf-8"),
            file_name="content_gap_opportunities.csv",
            mime="text/csv",
        )
    st.markdown("#### Report preview")
    st.markdown(report)


def render_competitors_page(competitor_channels: List[Dict], competitor_videos: pd.DataFrame) -> None:
    render_dashboard_page_header("Competitors", "Compare competitor performance, upload patterns, and video-level metrics.")
    if competitor_videos.empty:
        st.info("Add at least one competitor channel URL to see competitor reports.")
        return
    for channel in competitor_channels:
        rows = competitor_videos[competitor_videos["channel_id"] == channel["id"]]
        render_premium_channel_header(channel, rows)
        render_video_card_grid(rows.sort_values("views", ascending=False), limit=3, columns=3)
        render_analysis(channel["title"], rows, f"competitor_{channel['id']}")


def render_outliers_page(
    own_videos: pd.DataFrame,
    competitor_channels: List[Dict],
    competitor_videos: pd.DataFrame,
    all_videos: pd.DataFrame,
    video_description: str,
) -> None:
    own_videos = ensure_dashboard_video_columns(own_videos)
    competitor_videos = ensure_dashboard_video_columns(competitor_videos)
    all_videos = ensure_dashboard_video_columns(all_videos)
    render_dashboard_page_header("Outliers", "Find videos that overperformed and inspect the likely public-data signals.")
    with st.container(border=True):
        st.markdown("#### High-outlier video cards")
        ranked = all_videos.sort_values(["outlier_score", "views_per_day", "views"], ascending=False)
        render_video_card_grid(ranked, limit=6, columns=3)
    render_growth_insights(own_videos, competitor_channels, competitor_videos, all_videos, video_description)


def render_alerts_page(all_videos: pd.DataFrame) -> None:
    render_dashboard_page_header("Alerts", "Lightweight watchlist for high outlier and fast-moving upload signals.")
    if all_videos.empty:
        st.info("Analyse channels first to see alert candidates.")
        return
    all_videos = ensure_dashboard_video_columns(all_videos)
    fast = all_videos.sort_values(["outlier_score", "views_per_day"], ascending=False).head(25)
    render_metric_cards(
        [
            {"label": "High outlier alerts", "value": format_compact_number((fast["outlier_score"] >= 2).sum())},
            {"label": "Watchlist videos", "value": format_compact_number(len(fast))},
            {"label": "Top views/day", "value": f"{float(fast['views_per_day'].max()):,.1f}"},
            {"label": "Channels monitored", "value": format_compact_number(fast["channel"].nunique())},
        ]
    )
    st.dataframe(
        fast,
        hide_index=True,
        column_config={
            "thumbnail": st.column_config.ImageColumn("Thumbnail"),
            "views": st.column_config.NumberColumn("Views", format="%d"),
            "views_per_day": st.column_config.NumberColumn("Views/day", format="%.2f"),
            "outlier_score": st.column_config.NumberColumn("Outlier score", format="%.2f"),
            "url": st.column_config.LinkColumn("Video URL"),
        },
    )


def parse_youtube_video_id(video_url: str) -> str:
    raw = str(video_url or "").strip()
    if not raw:
        return ""
    if re.fullmatch(r"[\w-]{11}", raw):
        return raw

    parsed = urlparse(raw if re.match(r"^https?://", raw) else f"https://{raw}")
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if "youtu.be" in host and path_parts:
        return path_parts[0][:11]
    query = parse_qs(parsed.query)
    if query.get("v"):
        return query["v"][0][:11]
    if path_parts:
        for marker in ["shorts", "embed", "live", "v"]:
            if marker in path_parts:
                index = path_parts.index(marker)
                if len(path_parts) > index + 1:
                    return path_parts[index + 1][:11]
    return ""


@st.cache_data(show_spinner=False, ttl=1800)
def fetch_single_video_analysis(video_url: str, api_key: str) -> pd.DataFrame:
    video_id = parse_youtube_video_id(video_url)
    if not video_id:
        raise ValueError("Please paste a valid YouTube video link.")
    details = fetch_video_details((video_id,), api_key)
    if details.empty:
        raise ValueError("Video details not found. Check the link or video privacy.")
    return details


def build_estimated_monthly_video_views(video_row: pd.Series) -> pd.DataFrame:
    published_at = pd.to_datetime(video_row.get("published_at"), utc=True, errors="coerce")
    if pd.isna(published_at):
        return pd.DataFrame()
    today = datetime.now(timezone.utc)
    total_views = int(video_row.get("views") or 0)
    total_days = max((today - published_at.to_pydatetime()).total_seconds() / 86400, 1)
    avg_views_per_day = total_views / total_days

    start_month = pd.Timestamp(year=published_at.year, month=published_at.month, day=1, tz="UTC")
    end_month = pd.Timestamp(year=today.year, month=today.month, day=1, tz="UTC")
    month_starts = pd.date_range(start_month, end_month, freq="MS", tz="UTC")

    rows = []
    cumulative = 0.0
    for month_start in month_starts:
        month_end = month_start + pd.offsets.MonthBegin(1)
        active_start = max(month_start, published_at)
        active_end = min(month_end, pd.Timestamp(today))
        active_days = max((active_end - active_start).total_seconds() / 86400, 0)
        estimated_views = avg_views_per_day * active_days
        cumulative += estimated_views
        rows.append(
            {
                "month": month_start.date(),
                "month_label": month_start.strftime("%b %Y"),
                "active_days": round(active_days, 1),
                "estimated_month_views": int(round(estimated_views)),
                "estimated_cumulative_views": int(round(min(cumulative, total_views))),
                "avg_views_per_day": round(avg_views_per_day, 2),
            }
        )

    if rows:
        rows[-1]["estimated_cumulative_views"] = total_views
    return pd.DataFrame(rows)


def render_video_monthly_view_chart(monthly_views: pd.DataFrame) -> None:
    if monthly_views.empty:
        st.info("Monthly chart data could not be created for this video.")
        return

    base = alt.Chart(monthly_views).encode(
        x=alt.X("month:T", title="Month"),
        tooltip=[
            alt.Tooltip("month_label:N", title="Month"),
            alt.Tooltip("active_days:Q", title="Active days"),
            alt.Tooltip("estimated_month_views:Q", title="Estimated month views", format=","),
            alt.Tooltip("estimated_cumulative_views:Q", title="Estimated cumulative views", format=","),
        ],
    )
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#2563EB").encode(
        y=alt.Y("estimated_month_views:Q", title="Estimated monthly views"),
    )
    line = base.mark_line(point=True, color="#E11D48").encode(
        y=alt.Y("estimated_cumulative_views:Q", title="Estimated cumulative views"),
    )
    st.altair_chart((bars + line).resolve_scale(y="independent").properties(height=380).interactive())


def render_youtube_video_analyzer(api_key: str, all_videos: pd.DataFrame) -> None:
    render_dashboard_page_header(
        "Video analyzer",
        "Paste one YouTube video link to inspect title, public metrics, and estimated month-by-month views.",
    )
    st.caption(
        "Note: public YouTube Data API shows current total views only. The month-by-month chart below is an estimate from upload date to today, not actual YouTube Analytics history."
    )

    with st.container(border=True):
        video_url = st.text_input(
            "YouTube video link",
            placeholder="https://www.youtube.com/watch?v=VIDEO_ID",
            key="single_video_analyzer_url",
        )
        analyse_video = st.button("Analyze video", type="primary", width="stretch")

    if analyse_video:
        if not api_key:
            st.error("Add your YouTube Data API key in Data setup first.")
            return
        try:
            with st.spinner("Fetching video details..."):
                video_df = fetch_single_video_analysis(video_url, api_key)
            st.session_state["single_video_analysis_result"] = {
                "video_url": video_url,
                "video": video_df.iloc[0].to_dict(),
            }
        except Exception as error:
            st.error(str(error))
            return

    result = st.session_state.get("single_video_analysis_result", {})
    if not result:
        st.info("Paste a video link and click Analyze video.")
        return

    row = pd.Series(result["video"])
    thumbnail_url = str(row.get("thumbnail") or "")
    title = str(row.get("title") or "")
    monthly_views = build_estimated_monthly_video_views(row)

    top_cols = st.columns([1.2, 2.8], vertical_alignment="center")
    with top_cols[0]:
        if thumbnail_url:
            st.image(thumbnail_url)
    with top_cols[1]:
        st.markdown(f"### {title}")
        st.caption(str(row.get("source_channel") or row.get("channel") or ""))
        metric_cols = st.columns(4)
        metric_cols[0].metric("Total views", format_number(int(row.get("views") or 0)), border=True)
        metric_cols[1].metric("Views/day", f"{float(row.get('views_per_day') or 0):,.2f}", border=True)
        metric_cols[2].metric("Video age", f"{float(row.get('video_age_days') or 0):,.1f} days", border=True)
        metric_cols[3].metric("Comments", format_number(int(row.get("comments") or 0)), border=True)
        if row.get("url"):
            st.link_button("Open video", str(row.get("url")), icon=":material/open_in_new:")

    with st.container(border=True):
        st.markdown("#### Estimated month-by-month views")
        render_video_monthly_view_chart(monthly_views)

    detail_cols = st.columns(2)
    with detail_cols[0]:
        st.markdown("#### Title signals")
        title_analysis = deterministic_title_analysis(title)
        title_labels = {
            "title_length": "Title length",
            "word_count": "Word count",
            "has_number": "Has number?",
            "has_question": "Has question?",
            "has_year": "Has year?",
            "hook_type": "Hook type",
            "hook_words": "Hook words",
            "curiosity_score": "Curiosity",
            "clarity_score": "Clarity",
            "orientation": "Search vs browse",
        }
        st.dataframe(analysis_dict_to_frame(title_analysis, title_labels), hide_index=True)
    with detail_cols[1]:
        st.markdown("#### Monthly estimate data")
        st.dataframe(
            monthly_views,
            hide_index=True,
            column_config={
                "month": st.column_config.DateColumn("Month"),
                "estimated_month_views": st.column_config.NumberColumn("Estimated month views", format="%d"),
                "estimated_cumulative_views": st.column_config.NumberColumn("Estimated cumulative views", format="%d"),
                "avg_views_per_day": st.column_config.NumberColumn("Avg views/day", format="%.2f"),
            },
        )

    if not all_videos.empty:
        st.markdown("#### Similar analysed videos")
        keywords = set(title_keywords(title)[:6])
        if keywords:
            similar = all_videos[
                all_videos["title"].astype(str).apply(
                    lambda item: bool(keywords & set(title_keywords(item)))
                )
            ].copy()
            if not similar.empty:
                render_video_card_grid(similar.sort_values("views", ascending=False), limit=3, columns=3)

    st.download_button(
        "Download video analyzer CSV",
        monthly_views.to_csv(index=False).encode("utf-8"),
        file_name="youtube_video_monthly_estimated_views.csv",
        mime="text/csv",
    )


def render_settings_page(
    own_channel: Dict,
    own_videos: pd.DataFrame,
    competitor_channels: List[Dict],
    competitor_videos: pd.DataFrame,
    all_videos: pd.DataFrame,
    video_description: str,
    analysis_start_date: str,
    analysis_end_date: str,
    saved_max_videos: int,
) -> None:
    render_dashboard_page_header("Settings", "API status, analysis scope, saved reports, and exports.")
    render_metric_cards(
        [
            {"label": "Date range", "value": f"{analysis_start_date} to {analysis_end_date}"},
            {"label": "Max videos/channel", "value": format_compact_number(saved_max_videos)},
            {"label": "Competitors", "value": format_compact_number(len(competitor_channels))},
            {"label": "Analysed videos", "value": format_compact_number(len(all_videos))},
        ]
    )
    st.markdown("#### API status")
    status_rows = [
        {"Service": "YouTube Data API", "Status": "Configured" if load_api_key() else "Use sidebar input"},
        {"Service": "OpenAI thumbnail analysis", "Status": "Configured" if load_openai_api_key() else "Not configured"},
        {"Service": "GLM comment report", "Status": "Configured" if load_glm_api_key() else "Not configured"},
    ]
    st.dataframe(pd.DataFrame(status_rows), hide_index=True)
    render_keyword_reports_page(all_videos)
    render_downloads_page(
        own_channel,
        own_videos,
        competitor_channels,
        competitor_videos,
        all_videos,
        video_description,
    )


def main() -> None:
    st.set_page_config(page_title="YouTube Growth Intelligence", page_icon=":material/analytics:", layout="wide")
    apply_dashboard_theme()
    has_saved_analysis = "analysis_result" in st.session_state

    with st.sidebar:
        nav_page = render_sidebar_navigation()
        st.divider()
        with st.expander("Data setup", expanded=not has_saved_analysis):
            default_key = load_api_key()
            api_key = st.text_input("YouTube Data API key", value=default_key, type="password")
            default_openai_key = load_env_value("OPENAI_API_KEY")
            st.text_input(
                "OpenAI API key for thumbnail analysis",
                value=default_openai_key,
                type="password",
                key="openai_api_key_input",
                help="Used only in Title + Thumbnail Analyzer for vision thumbnail analysis.",
            )
            default_glm_key = load_env_value("GLM_API_KEY") or load_env_value("ZAI_API_KEY")
            st.text_input(
                "GLM API key for comment report",
                value=default_glm_key,
                type="password",
                key="glm_api_key_input",
                help="Used only in Comment Intelligence to generate AI video ideas, red flags, and reports.",
            )
            own_url = st.text_input("Your channel URL", placeholder="https://www.youtube.com/@YourChannel")
            competitor_urls = st.text_area(
                "Competitor channel URLs - paste up to 5",
                placeholder=(
                    "https://www.youtube.com/@Competitor1\n"
                    "https://www.youtube.com/@Competitor2\n"
                    "@Competitor3"
                ),
                height=150,
            )
            detected_competitors = parse_competitor_urls(competitor_urls)
            if detected_competitors:
                st.caption(f"Detected {len(detected_competitors)} competitor link(s).")
                with st.expander("Show detected competitors"):
                    for competitor in detected_competitors:
                        st.write(competitor)
            warning = competitor_input_warning(competitor_urls, detected_competitors)
            if warning:
                st.warning(warning)

            video_description = st.text_area(
                "Your next video description",
                placeholder="Write your next video topic/description here...",
                height=130,
            )
            ctr_upload = st.file_uploader(
                "Optional CTR CSV for your own channel",
                type=["csv"],
                help="Public API does not provide CTR. Upload CSV with columns: video_id,ctr or title,ctr.",
            )
            today = datetime.now(APP_TIMEZONE).date()
            default_start = today.replace(month=1, day=1)
            analysis_date_range = st.date_input(
                "Video analysis date range",
                value=(default_start, today),
                help="The app fetches videos uploaded inside this range, not only the latest 100 videos.",
            )
            max_videos_per_channel = st.slider(
                "Max videos/channel",
                min_value=50,
                max_value=2000,
                value=500,
                step=50,
                help="Increase this if a channel uploaded many videos in the selected range. Higher values use more YouTube API quota.",
            )
            analyse = st.button("Analyse channels", type="primary", width="stretch")

        st.caption("Competitor CTR is not public. Upload CTR only for your own exported data.")

    if analyse:
        if not api_key:
            st.error("Add a YouTube Data API key before running the analysis.")
            return

        if not own_url:
            st.error("Add your channel URL first.")
            return

        if not isinstance(analysis_date_range, tuple) or len(analysis_date_range) != 2:
            st.error("Please select both start and end dates for analysis.")
            return

        analysis_start_date, analysis_end_date = analysis_date_range
        if analysis_start_date > analysis_end_date:
            st.error("Start date end date se pehle honi chahiye.")
            return

        competitor_url_list = parse_competitor_urls(competitor_urls)

        try:
            with st.spinner(f"Fetching your videos from {analysis_start_date} to {analysis_end_date}..."):
                own_channel, own_videos = load_channel_videos_for_date_range(
                    own_url,
                    api_key,
                    analysis_start_date.isoformat(),
                    analysis_end_date.isoformat(),
                    max_videos_per_channel,
                )
                own_videos = merge_ctr_data(own_videos, ctr_upload)
                own_videos = dedupe_videos(own_videos)

            competitor_channels = []
            competitor_frames = []
            for index, competitor_url in enumerate(competitor_url_list, start=1):
                with st.spinner(f"Fetching competitor {index} videos from {analysis_start_date} to {analysis_end_date}..."):
                    channel, videos = load_channel_videos_for_date_range(
                        competitor_url,
                        api_key,
                        analysis_start_date.isoformat(),
                        analysis_end_date.isoformat(),
                        max_videos_per_channel,
                    )
                    competitor_channels.append(channel)
                    competitor_frames.append(dedupe_videos(videos))

            competitor_videos = (
                pd.concat(competitor_frames, ignore_index=True)
                if competitor_frames
                else pd.DataFrame(columns=own_videos.columns)
            )
            competitor_channels = dedupe_channels(competitor_channels)
            competitor_videos = dedupe_videos(competitor_videos)
            own_videos_unfiltered = add_content_categories(own_videos)
            competitor_videos_unfiltered = add_content_categories(competitor_videos)
            all_videos_unfiltered = add_content_categories(
                dedupe_videos(pd.concat([own_videos_unfiltered, competitor_videos_unfiltered], ignore_index=True))
            )

            st.session_state["analysis_result"] = {
                "own_channel": own_channel,
                "own_videos_unfiltered": own_videos_unfiltered,
                "competitor_channels": competitor_channels,
                "competitor_videos_unfiltered": competitor_videos_unfiltered,
                "all_videos_unfiltered": all_videos_unfiltered,
                "analysis_start_date": analysis_start_date.isoformat(),
                "analysis_end_date": analysis_end_date.isoformat(),
                "max_videos_per_channel": max_videos_per_channel,
            }

        except Exception as error:
            st.error(str(error))
            return

    elif not has_saved_analysis:
        if nav_page == "Thumbnail Analyzer":
            render_title_thumbnail_analyzer(pd.DataFrame())
            return
        if nav_page == "Video Analyzer":
            render_youtube_video_analyzer(api_key, pd.DataFrame())
            return
        render_dashboard_page_header("Start analysis", "Paste channel links in Data setup, then run the dashboard.")
        st.info("Paste your channel link, add up to 5 competitors, write your next video description, then click Analyse channels.")
        return

    analysis_result = st.session_state["analysis_result"]
    own_channel = analysis_result["own_channel"]
    competitor_channels = analysis_result["competitor_channels"]
    own_videos_unfiltered = analysis_result["own_videos_unfiltered"]
    competitor_videos_unfiltered = analysis_result["competitor_videos_unfiltered"]
    all_videos_unfiltered = analysis_result["all_videos_unfiltered"]
    analysis_start_date = analysis_result.get("analysis_start_date", "")
    analysis_end_date = analysis_result.get("analysis_end_date", "")
    saved_max_videos = analysis_result.get("max_videos_per_channel", MAX_VIDEOS)

    own_videos = own_videos_unfiltered.copy()
    competitor_videos = competitor_videos_unfiltered.copy()
    all_videos = all_videos_unfiltered.copy()

    channel_names = [own_channel.get("title", "")] + [channel.get("title", "") for channel in competitor_channels]
    with st.sidebar:
        selected_channel_filter = render_global_channel_search(channel_names)

    if selected_channel_filter:
        own_videos = own_videos[own_videos["channel"].astype(str) == selected_channel_filter].copy()
        competitor_videos = competitor_videos[competitor_videos["channel"].astype(str) == selected_channel_filter].copy()
        all_videos = all_videos[all_videos["channel"].astype(str) == selected_channel_filter].copy()

    if analysis_start_date and analysis_end_date:
        st.caption(
            f"Showing videos uploaded from {analysis_start_date} to {analysis_end_date}. "
            f"Fetch limit: up to {saved_max_videos} videos per channel."
        )
    if all_videos.empty:
        st.warning("Selected date range me videos nahi mile. Date range ko wider karke Analyse channels dobara click karein.")
        return

    if nav_page == "Overview":
        render_overview_dashboard(own_channel, own_videos, competitor_videos, all_videos)
    elif nav_page == "Your Channel":
        render_premium_channel_header(own_channel, own_videos)
        render_analysis(own_channel["title"], own_videos, "own")
    elif nav_page == "Competitors":
        render_competitors_page(competitor_channels, competitor_videos)
    elif nav_page == "Video Analyzer":
        render_youtube_video_analyzer(api_key, all_videos)
    elif nav_page == "Outliers":
        render_outliers_page(own_videos, competitor_channels, competitor_videos, all_videos, video_description)
    elif nav_page == "Trends":
        render_trend_intelligence(all_videos_unfiltered)
    elif nav_page == "Seasonal Intelligence":
        render_seasonal_intelligence(all_videos)
    elif nav_page == "Search Demand":
        render_opportunity_finder(api_key, own_channel, all_videos, video_description)
    elif nav_page == "Audience Intelligence":
        render_comment_intelligence(api_key, all_videos)
    elif nav_page == "Content Gap":
        render_content_gap_filler(own_channel, all_videos)
    elif nav_page == "Thumbnail Analyzer":
        render_title_thumbnail_analyzer(all_videos_unfiltered)
    elif nav_page == "Title Analyzer":
        render_overall_recommendations(own_videos, competitor_videos, all_videos, video_description)
    elif nav_page == "Content Ideas":
        render_what_should_we_post_next(api_key, own_channel, all_videos_unfiltered, video_description)
    elif nav_page == "Historical Data":
        render_monthly_competitor_report(competitor_videos_unfiltered, analysis_start_date, analysis_end_date)
    elif nav_page == "Alerts":
        render_alerts_page(all_videos)
    elif nav_page == "Settings":
        render_settings_page(
            own_channel,
            own_videos,
            competitor_channels,
            competitor_videos,
            all_videos,
            video_description,
            analysis_start_date,
            analysis_end_date,
            saved_max_videos,
        )


if __name__ == "__main__":
    main()
