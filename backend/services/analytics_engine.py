import base64
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse
from zoneinfo import ZoneInfo
import pandas as pd
import requests

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
MAX_VIDEOS = 100
MAX_COMPETITORS = 5

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
    val = os.getenv(env_key, "").strip()
    if val:
        return val.strip('"').strip("'")
    env_paths = [os.path.join(APP_DIR, ".env"), os.path.abspath(".env")]
    for path in env_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    clean = line.strip()
                    if clean and not clean.startswith("#"):
                        if clean.lower().startswith("export "):
                            clean = clean[7:].strip()
                        k, sep, v = clean.partition("=")
                        if sep and k.strip() == env_key:
                            return v.strip().strip('"').strip("'")
    return ""

def sanitize_error_text(text: str, secrets: Optional[List[str]] = None) -> str:
    clean = str(text or "")
    for secret in secrets or []:
        if secret:
            clean = clean.replace(secret, "***")
    clean = re.sub(r"([?&]key=)[^&\s)'\"]+", r"\1***", clean)
    clean = re.sub(r"([?&]access_token=)[^&\s)'\"]+", r"\1***", clean)
    return clean

def words_from_text(text: str) -> List[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]{2,}", str(text).lower())
    return [w for w in words if w not in STOPWORDS and not w.isdigit()]

def title_keywords(title: str) -> List[str]:
    return words_from_text(title)

def title_hook_words(title: str) -> List[str]:
    words = words_from_text(title)
    hooks = [w for w in words if w in HOOK_WORDS]
    if "?" in str(title):
        hooks.append("question")
    if re.search(r"\b\d+\b", str(title)):
        hooks.append("number")
    if re.search(r"\b20\d{2}\b", str(title)):
        hooks.append("year")
    return hooks

def parse_duration(duration: str) -> int:
    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?",
        duration,
    )
    if not match:
        return 0
    parts = {k: int(v or 0) for k, v in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]

def parse_published_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

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

def bool_label(val: bool) -> str:
    return "Yes" if val else "No"

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
    clean = str(title).lower()
    if "?" in title:
        return "Question"
    if re.search(r"\b\d+\b", title):
        return "Number/list"
    if any(w in clean for w in ["mistake", "avoid", "stop", "wrong"]):
        return "Problem/avoidance"
    if any(w in clean for w in ["secret", "truth", "hidden", "nobody"]):
        return "Curiosity"
    if any(w in clean for w in ["complete", "guide", "explained", "tutorial"]):
        return "Educational"
    if any(w in clean for w in ["before", "now", "today", "last minute"]):
        return "Urgency"
    return "Direct"

def deterministic_title_analysis(title: str) -> Dict[str, Any]:
    title = str(title or "").strip()
    words = re.findall(r"\w+", title)
    title_length = len(title)
    word_count = len(words)
    has_number = bool(re.search(r"\b\d+\b", title))
    has_question = "?" in title
    has_year = bool(re.search(r"\b20\d{2}\b", title))
    lower_title = title.lower()
    keywords = title_keywords(title)
    hook_words = title_hook_words(title)

    clarity = 10
    if title_length < 25 or title_length > 85:
        clarity -= 2
    if word_count < 4 or word_count > 13:
        clarity -= 1
    if len(keywords) < 2:
        clarity -= 2
    if any(s in title for s in ["!!!", "???", "🔥"]):
        clarity -= 1

    curiosity = 4 + len(hook_words) * 1.4
    if has_question:
        curiosity += 1.5
    if any(w in lower_title for w in ["secret", "truth", "before", "mistake", "avoid", "hidden", "stop"]):
        curiosity += 2

    specificity = 3 + min(len(keywords), 5)
    if has_number:
        specificity += 1.5
    if has_year:
        specificity += 1
    if any(w in lower_title for w in ["cat", "iim", "mock", "percentile", "varc", "lrdi", "quant", "ai", "coding"]):
        specificity += 1

    urgency = 2
    if any(w in lower_title for w in ["now", "today", "before", "last", "stop", "avoid", "deadline", "2026", "2027"]):
        urgency += 4
    if any(w in lower_title for w in ["mistake", "mistakes", "killing", "fail", "low score"]):
        urgency += 2

    emotion = 3
    if any(w in lower_title for w in ["mistake", "secret", "truth", "fear", "stress", "confused", "stop", "avoid", "killing"]):
        emotion += 4
    if any(w in lower_title for w in ["easy", "simple", "complete", "best"]):
        emotion += 1

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
        "orientation": title_orientation(title),
    }

def classify_content_category(title: str, tags: str = "") -> str:
    words = set(words_from_text(f"{title} {tags}"))
    academic_score = len(words & ACADEMIC_KEYWORDS)
    strategy_score = len(words & STRATEGY_KEYWORDS)
    if academic_score > strategy_score and academic_score > 0:
        return "Academic"
    if strategy_score > 0:
        return "Non-academic / Strategy"
    return "Other / mixed"

def classify_trend_topic(title: str, tags: str = "", category: str = "") -> str:
    text = f"{title} {tags}".lower()
    topic_scores = {}
    for topic, keywords in TREND_TOPIC_KEYWORDS.items():
        topic_scores[topic] = sum(1 for k in keywords if k in text)
    best_topic = max(topic_scores, key=topic_scores.get)
    if topic_scores[best_topic] > 0:
        return best_topic
    if category == "Academic":
        return "Academic Other"
    if category == "Non-academic / Strategy":
        return "Strategy Other"
    return "Other"

def starts_with_pattern(title: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title)
    return " ".join(words[:3]).lower() if words else ""

def dedupe_videos_list(videos: List[Dict]) -> List[Dict]:
    seen = set()
    result = []
    for v in videos:
        vid = v.get("video_id")
        if vid and vid not in seen:
            seen.add(vid)
            result.append(v)
    return result

def dedupe_channels_list(channels: List[Dict]) -> List[Dict]:
    seen = set()
    result = []
    for c in channels:
        cid = c.get("id")
        if cid and cid not in seen:
            seen.add(cid)
            result.append(c)
    return result
