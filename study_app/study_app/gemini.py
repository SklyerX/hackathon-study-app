from google import genai
from functools import lru_cache
from .config import get_settings


@lru_cache
def get_gemini_client() -> genai.Client:
    """
    Returns a cached Gemini 2.0 / 1.5 Client.
    Using the new 'google-genai' SDK structure.
    """
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)
    return client
