from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.analytics_engine import load_env_value
from backend.services.youtube_client import request_youtube

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class VerifyKeysRequest(BaseModel):
    youtube_key: Optional[str] = None
    openai_key: Optional[str] = None
    glm_key: Optional[str] = None

@router.get("/status")
def get_env_status() -> Dict[str, Any]:
    yt_key = load_env_value("YOUTUBE_API_KEY")
    openai_key = load_env_value("OPENAI_API_KEY")
    glm_key = load_env_value("GLM_API_KEY") or load_env_value("ZAI_API_KEY")

    return {
        "youtube_configured": bool(yt_key),
        "youtube_key_preview": f"{yt_key[:4]}...{yt_key[-4:]}" if len(yt_key) > 8 else ("Configured" if yt_key else "Missing"),
        "openai_configured": bool(openai_key),
        "openai_key_preview": f"{openai_key[:4]}...{openai_key[-4:]}" if len(openai_key) > 8 else ("Configured" if openai_key else "Missing"),
        "glm_configured": bool(glm_key),
        "glm_key_preview": f"{glm_key[:4]}...{glm_key[-4:]}" if len(glm_key) > 8 else ("Configured" if glm_key else "Missing"),
    }

@router.post("/verify-keys")
def verify_keys(payload: VerifyKeysRequest) -> Dict[str, Any]:
    results = {}

    # Test YouTube API
    yt_key = payload.youtube_key or load_env_value("YOUTUBE_API_KEY")
    if yt_key:
        try:
            test = request_youtube("search", yt_key, part="snippet", q="test", maxResults=1)
            results["youtube"] = {"valid": True, "message": "YouTube API Key is valid and working."}
        except Exception as e:
            results["youtube"] = {"valid": False, "message": str(e)}
    else:
        results["youtube"] = {"valid": False, "message": "No YouTube API Key provided."}

    # Test OpenAI API
    openai_key = payload.openai_key or load_env_value("OPENAI_API_KEY")
    results["openai"] = {
        "valid": bool(openai_key),
        "message": "OpenAI Key configured." if openai_key else "No OpenAI API Key provided.",
    }

    # Test GLM API
    glm_key = payload.glm_key or load_env_value("GLM_API_KEY") or load_env_value("ZAI_API_KEY")
    results["glm"] = {
        "valid": bool(glm_key),
        "message": "GLM / Z.AI Key configured." if glm_key else "No GLM API Key provided.",
    }

    return results
