
from google import genai
from functools import lru_cache
from study_app.config import get_settings


@lru_cache
def get_gemini_client() -> genai.GenerativeModel:
    """
    Returns a cached Gemini 1.5 Flash model instance.
    Flash is free-tier, fast, and handles text + vision + audio.
    """
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)
    return client
