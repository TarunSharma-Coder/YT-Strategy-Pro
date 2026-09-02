import json
from typing import Any, Dict, List, Tuple

try:
    from openai import OpenAI, OpenAIError
except Exception:
    OpenAI = None

    class OpenAIError(Exception):
        pass


DEFAULT_GLM_BASE_URL = "https://api.z.ai/api/paas/v4/"
DEFAULT_GLM_MODEL = "glm-5.1"


def friendly_glm_error_message(error: Exception) -> str:
    status_code = getattr(error, "status_code", "")
    details = str(error)
    lower_details = details.lower()

    if (
        "insufficient balance" in lower_details
        or "no resource package" in lower_details
        or "please recharge" in lower_details
    ):
        return (
            "GLM account balance/resource package issue: your GLM/Z.AI account does not have enough balance "
            "or the selected model is not included in your active package. Recharge the GLM account, buy/activate "
            "a resource package, or change `GLM_MODEL` to a model available in your package. The normal rule-based "
            "Comment Intelligence tables above will still work without GLM."
        )

    if status_code in {401, 403} or "unauthorized" in lower_details or "forbidden" in lower_details:
        return "GLM API key/auth error: check that the GLM key is correct and active."

    if status_code == 429 or "rate limit" in lower_details:
        return "GLM rate limit reached. Wait a few minutes and try again, or use a lower-cost model/package."

    return f"GLM API error: {details}"


def safe_json_from_text(text: str) -> Dict[str, Any]:
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


def as_list(value: Any, limit: int) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value][:limit]
    if isinstance(value, list):
        return value[:limit]
    return []


def normalize_glm_report(raw: Dict[str, Any]) -> Dict[str, Any]:
    report = {
        "executive_summary": "",
        "audience_red_flags": [],
        "video_ideas": [],
        "content_angle_recommendations": [],
    }
    if isinstance(raw, dict):
        report.update(raw)

    report["executive_summary"] = str(report.get("executive_summary") or "").strip()
    report["audience_red_flags"] = as_list(report.get("audience_red_flags"), 10)
    report["video_ideas"] = as_list(report.get("video_ideas"), 10)
    report["content_angle_recommendations"] = as_list(report.get("content_angle_recommendations"), 8)

    normalized_ideas = []
    for index, item in enumerate(report["video_ideas"], start=1):
        if isinstance(item, str):
            item = {"suggested_title": item}
        if not isinstance(item, dict):
            continue
        keywords = as_list(item.get("long_tail_keywords"), 5)
        normalized_ideas.append(
            {
                "rank": int(item.get("rank") or index),
                "idea": str(item.get("idea") or "").strip(),
                "suggested_title": str(item.get("suggested_title") or "").strip(),
                "why_this_can_work": str(item.get("why_this_can_work") or item.get("why") or "").strip(),
                "comment_signal": str(item.get("comment_signal") or "").strip(),
                "long_tail_keywords": ", ".join(str(keyword).strip() for keyword in keywords if str(keyword).strip()),
            }
        )
    report["video_ideas"] = normalized_ideas[:10]

    normalized_red_flags = []
    for item in report["audience_red_flags"]:
        if isinstance(item, str):
            item = {"red_flag": item}
        if not isinstance(item, dict):
            continue
        normalized_red_flags.append(
            {
                "red_flag": str(item.get("red_flag") or "").strip(),
                "severity": str(item.get("severity") or "Medium").strip(),
                "evidence": str(item.get("evidence") or "").strip(),
                "action": str(item.get("action") or item.get("what_to_fix") or "").strip(),
            }
        )
    report["audience_red_flags"] = normalized_red_flags[:10]
    report["content_angle_recommendations"] = [
        str(item).strip() for item in report["content_angle_recommendations"] if str(item).strip()
    ][:8]
    return report


def extract_message_text(response: Any) -> str:
    try:
        return response.choices[0].message.content or ""
    except Exception:
        return ""


def build_glm_prompt(payload: Dict[str, Any]) -> str:
    return f"""
You are a YouTube growth strategist. Analyze the classified YouTube comments and current idea table.

Return valid JSON only with this exact shape:
{{
  "executive_summary": "short summary of audience demand and risks",
  "audience_red_flags": [
    {{
      "red_flag": "specific risk or warning from comments",
      "severity": "High/Medium/Low",
      "evidence": "short evidence from comment patterns",
      "action": "specific fix for next content"
    }}
  ],
  "video_ideas": [
    {{
      "rank": 1,
      "idea": "content idea",
      "suggested_title": "full YouTube title",
      "why_this_can_work": "why based on comments and channel data",
      "comment_signal": "Question/Content request/Complaint/Confusion/Praise/etc",
      "long_tail_keywords": ["keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5"]
    }}
  ],
  "content_angle_recommendations": ["specific angle recommendation"]
}}

Rules:
- Give exactly 10 video_ideas when possible.
- Give up to 10 audience_red_flags.
- Do not predict exact views, CTR, revenue, or virality.
- Use only the supplied comments, comment types, video titles, and idea evidence.
- Make titles specific, clickable, and relevant to the channel niche.
- Keep the output in English/Hinglish style if the comments indicate Hindi/Hinglish audience.

Data:
{json.dumps(payload, ensure_ascii=False)}
"""


def generate_glm_comment_report(
    payload: Dict[str, Any],
    api_key: str,
    base_url: str = DEFAULT_GLM_BASE_URL,
    model: str = DEFAULT_GLM_MODEL,
) -> Tuple[Dict[str, Any], str]:
    if not api_key:
        return {}, "GLM_API_KEY missing. Add it in the sidebar or .env file."
    if OpenAI is None:
        return {}, "OpenAI SDK is not installed. Run: pip install -r requirements.txt"

    client = OpenAI(api_key=api_key, base_url=base_url or DEFAULT_GLM_BASE_URL)
    try:
        response = client.chat.completions.create(
            model=model or DEFAULT_GLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Return valid JSON only. You are a careful YouTube audience research analyst.",
                },
                {"role": "user", "content": build_glm_prompt(payload)},
            ],
            temperature=0.4,
            max_tokens=4096,
        )
    except OpenAIError as error:
        return {}, friendly_glm_error_message(error)
    except Exception as error:
        return {}, f"GLM report failed: {error}"

    parsed = safe_json_from_text(extract_message_text(response))
    if not parsed:
        return {}, "GLM returned malformed JSON. Please retry once."
    return normalize_glm_report(parsed), ""
