import base64
import io
import json
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, UnidentifiedImageError

try:
    from openai import OpenAI, OpenAIError
except Exception:
    OpenAI = None

    class OpenAIError(Exception):
        pass


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SUPPORTED_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MIN_WIDTH = 320
MIN_HEIGHT = 180
IDEAL_ASPECT_RATIO = 16 / 9
ASPECT_RATIO_WARNING_TOLERANCE = 0.25

THUMBNAIL_STYLES = {
    "Face + Text",
    "Text Heavy",
    "Object Focused",
    "Screenshot/UI",
    "Comparison",
    "Reaction",
    "Minimal",
    "Other",
}

REQUIRED_ANALYSIS_KEYS = [
    "thumbnail_text",
    "face_present",
    "face_count",
    "dominant_emotion",
    "main_subject",
    "thumbnail_style",
    "readability_score",
    "visual_hierarchy_score",
    "clutter_score",
    "curiosity_score",
    "urgency_score",
    "mobile_readability_score",
    "title_thumbnail_alignment_score",
    "complementarity_score",
    "redundancy_score",
    "curiosity_gap_score",
    "strengths",
    "problems",
    "recommendations",
]

THUMBNAIL_ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "thumbnail_text": {"type": "string"},
        "face_present": {"type": "boolean"},
        "face_count": {"type": "integer", "minimum": 0},
        "dominant_emotion": {"type": "string"},
        "main_subject": {"type": "string"},
        "thumbnail_style": {
            "type": "string",
            "enum": sorted(THUMBNAIL_STYLES),
        },
        "readability_score": {"type": "number", "minimum": 0, "maximum": 10},
        "visual_hierarchy_score": {"type": "number", "minimum": 0, "maximum": 10},
        "clutter_score": {"type": "number", "minimum": 0, "maximum": 10},
        "curiosity_score": {"type": "number", "minimum": 0, "maximum": 10},
        "urgency_score": {"type": "number", "minimum": 0, "maximum": 10},
        "mobile_readability_score": {"type": "number", "minimum": 0, "maximum": 10},
        "title_thumbnail_alignment_score": {"type": "number", "minimum": 0, "maximum": 10},
        "complementarity_score": {"type": "number", "minimum": 0, "maximum": 10},
        "redundancy_score": {"type": "number", "minimum": 0, "maximum": 10},
        "curiosity_gap_score": {"type": "number", "minimum": 0, "maximum": 10},
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "problems": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
    },
    "required": REQUIRED_ANALYSIS_KEYS,
}


def default_thumbnail_analysis() -> Dict[str, Any]:
    return {
        "thumbnail_text": "",
        "face_present": False,
        "face_count": 0,
        "dominant_emotion": "Unknown",
        "main_subject": "Unknown",
        "thumbnail_style": "Other",
        "readability_score": 0,
        "visual_hierarchy_score": 0,
        "clutter_score": 0,
        "curiosity_score": 0,
        "urgency_score": 0,
        "mobile_readability_score": 0,
        "title_thumbnail_alignment_score": 0,
        "complementarity_score": 0,
        "redundancy_score": 10,
        "curiosity_gap_score": 0,
        "strengths": [],
        "problems": [],
        "recommendations": [],
    }


def clamp_score(value: Any, default: float = 0.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    return round(max(0.0, min(10.0, score)), 1)


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "present", "1"}
    return bool(value)


def normalize_list(value: Any, limit: int = 3) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]


def normalize_analysis(raw: Dict[str, Any]) -> Dict[str, Any]:
    result = default_thumbnail_analysis()
    if isinstance(raw, dict):
        result.update(raw)

    for key in [
        "readability_score",
        "visual_hierarchy_score",
        "clutter_score",
        "curiosity_score",
        "urgency_score",
        "mobile_readability_score",
        "title_thumbnail_alignment_score",
        "complementarity_score",
        "redundancy_score",
        "curiosity_gap_score",
    ]:
        result[key] = clamp_score(result.get(key))

    result["face_present"] = normalize_bool(result.get("face_present"))
    try:
        result["face_count"] = max(0, int(result.get("face_count") or 0))
    except (TypeError, ValueError):
        result["face_count"] = 0

    for key in ["thumbnail_text", "dominant_emotion", "main_subject"]:
        result[key] = str(result.get(key) or "").strip()

    if result.get("thumbnail_style") not in THUMBNAIL_STYLES:
        result["thumbnail_style"] = "Other"

    result["strengths"] = normalize_list(result.get("strengths"), 3)
    result["problems"] = normalize_list(result.get("problems"), 3)
    result["recommendations"] = normalize_list(result.get("recommendations"), 3)
    return result


def validate_thumbnail_image(image_bytes: bytes, filename: str = "", mime_type: str = "") -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    filename = filename or ""
    extension = Path(filename).suffix.lower()
    detected_mime_type = ""
    image_format = ""
    width = 0
    height = 0
    aspect_ratio = 0.0
    file_size = len(image_bytes or b"")

    if not image_bytes:
        errors.append("Image file is empty.")
    if file_size > MAX_IMAGE_BYTES:
        errors.append("Image file is too large. Maximum allowed size is 10 MB.")
    if extension and extension not in SUPPORTED_EXTENSIONS:
        errors.append("Unsupported file type. Upload JPG, JPEG, or PNG only.")
    if mime_type and mime_type.lower() not in {"image/jpeg", "image/jpg", "image/png"}:
        errors.append("Unsupported image MIME type. Upload JPG, JPEG, or PNG only.")

    if image_bytes:
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                image_format = (image.format or "").upper()
                width, height = image.size
                detected_mime_type = SUPPORTED_IMAGE_FORMATS.get(image_format, "")
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            errors.append("Invalid image file. Please upload a readable JPG, JPEG, or PNG image.")

    if image_format and image_format not in SUPPORTED_IMAGE_FORMATS:
        errors.append("Unsupported image format. Upload JPG, JPEG, or PNG only.")
    if width and height:
        aspect_ratio = width / height
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            errors.append("Image dimensions are too small. Minimum size is 320x180 pixels.")
        if abs(aspect_ratio - IDEAL_ASPECT_RATIO) > ASPECT_RATIO_WARNING_TOLERANCE:
            warnings.append("Thumbnail is not close to the YouTube 16:9 aspect ratio.")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "filename": filename,
        "mime_type": detected_mime_type or (mime_type or "").lower(),
        "format": image_format,
        "width": width,
        "height": height,
        "aspect_ratio": round(aspect_ratio, 3) if aspect_ratio else 0,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
    }


def image_to_data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type or 'image/jpeg'};base64,{encoded}"


def extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", "")
    if output_text:
        return output_text

    chunks: List[str] = []
    for item in getattr(response, "output", []) or []:
        content_items = item.get("content", []) if isinstance(item, dict) else getattr(item, "content", [])
        for content in content_items or []:
            text = content.get("text", "") if isinstance(content, dict) else getattr(content, "text", "")
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def parse_json_text(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}


def calculate_packaging_score(analysis: Dict[str, Any]) -> int:
    normalized = normalize_analysis(analysis)
    weighted_score = (
        normalized["title_thumbnail_alignment_score"] * 10 * 0.20
        + normalized["complementarity_score"] * 10 * 0.20
        + normalized["readability_score"] * 10 * 0.15
        + normalized["visual_hierarchy_score"] * 10 * 0.15
        + normalized["curiosity_score"] * 10 * 0.15
        + normalized["mobile_readability_score"] * 10 * 0.10
        + (10 - normalized["redundancy_score"]) * 10 * 0.05
    )
    return max(0, min(100, int(round(weighted_score))))


def build_prompt(title: str) -> str:
    return f"""
Analyze this proposed YouTube video package using the title and uploaded thumbnail together.

Proposed title:
{title}

Return only structured JSON. Do not predict CTR, views, virality, revenue, or exact performance.
Do not identify any person by name. If faces are visible, describe only presence, count, and broad emotion.

Score every score field from 0 to 10:
- 0 means very weak or absent.
- 10 means very strong.
- For redundancy_score, 10 means too much unnecessary repetition between title and thumbnail.

Evaluate whether the thumbnail adds useful information beyond the title, whether the title and thumbnail repeat the same idea, and how clear the combined message is on mobile.
Keep strengths, problems, and recommendations specific to this exact package.
"""


def analyze_thumbnail_package(
    title: str,
    image_bytes: bytes,
    filename: str,
    mime_type: str,
    api_key: str,
    model: str = "gpt-5",
) -> Dict[str, Any]:
    validation = validate_thumbnail_image(image_bytes, filename, mime_type)
    empty_result = {
        "ok": False,
        "analysis": default_thumbnail_analysis(),
        "packaging_score": 0,
        "validation": validation,
    }

    if not validation["valid"]:
        return {
            **empty_result,
            "error_type": "unsupported_image",
            "error": " ".join(validation["errors"]),
        }
    if not title.strip():
        return {
            **empty_result,
            "error_type": "missing_title",
            "error": "Please enter a proposed YouTube video title.",
        }
    if not api_key:
        return {
            **empty_result,
            "error_type": "missing_api_key",
            "error": "OPENAI_API_KEY missing. Add it in the sidebar or project .env file.",
        }
    if OpenAI is None:
        return {
            **empty_result,
            "error_type": "missing_dependency",
            "error": "OpenAI Python SDK is not installed. Run: pip install -r requirements.txt",
        }

    detected_mime_type = validation.get("mime_type") or mime_type or "image/jpeg"
    data_url = image_to_data_url(image_bytes, detected_mime_type)
    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=model or "gpt-5",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": build_prompt(title)},
                        {"type": "input_image", "image_url": data_url, "detail": "low"},
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "thumbnail_packaging_analysis",
                    "schema": THUMBNAIL_ANALYSIS_SCHEMA,
                    "strict": True,
                }
            },
        )
    except OpenAIError as error:
        return {
            **empty_result,
            "error_type": "openai_api_error",
            "error": f"OpenAI API error: {error}",
        }
    except Exception as error:
        return {
            **empty_result,
            "error_type": "openai_api_error",
            "error": f"Thumbnail analysis failed: {error}",
        }

    parsed = parse_json_text(extract_response_text(response))
    if not parsed:
        return {
            **empty_result,
            "error_type": "malformed_ai_response",
            "error": "AI returned malformed JSON. Please retry once.",
        }

    analysis = normalize_analysis(parsed)
    return {
        "ok": True,
        "analysis": analysis,
        "packaging_score": calculate_packaging_score(analysis),
        "validation": validation,
        "response_id": getattr(response, "id", ""),
        "model": model or "gpt-5",
    }
