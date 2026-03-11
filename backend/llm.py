"""
LLM Helper — Google Gemini API integration.

Replaces the Ollama backend with Gemini 1.5 Flash, which runs on Railway
(no local GPU required). Falls back to rule-based output when the key is
missing or the API call fails.

Usage:
  from backend.llm import llm_call, gemini_available
  # ollama_available is kept as an alias for backward compatibility
"""
import os
from typing import Optional
from loguru import logger

try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

_SYSTEM = (
    "You are an expert Indian credit analyst with 20 years of corporate lending experience. "
    "Be concise and factual. Use RBI/Basel/Indian-banking terminology. "
    "Reply in plain English only. No markdown, no headers, no bullet points unless explicitly asked."
)

_client = None

def _get_client():
    global _client
    if _client is not None:
        return _client
    if not _GENAI_AVAILABLE or not GEMINI_API_KEY:
        return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        _client = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=_SYSTEM,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.9,
                "max_output_tokens": 500,
            },
        )
        logger.info(f"[LLM] Gemini client initialised — model={GEMINI_MODEL}")
        return _client
    except Exception as e:
        logger.warning(f"[LLM] Gemini init failed: {e}")
        return None


def gemini_available() -> bool:
    """Returns True if Gemini API key is set and lib is installed."""
    return bool(_GENAI_AVAILABLE and GEMINI_API_KEY)


# Backward-compatibility alias used throughout the codebase
def ollama_available() -> bool:
    return gemini_available()


def get_device() -> str:
    return "gemini"


def set_device(device: str) -> None:
    # No-op — Gemini is always cloud; kept for API compatibility
    logger.info(f"[LLM] set_device('{device}') ignored — using Gemini API")


def get_config() -> dict:
    return {
        "model":  GEMINI_MODEL,
        "device": "cloud",
        "label":  f"Gemini — {GEMINI_MODEL} (Google AI)",
        "gemini_available": gemini_available(),
    }


def llm_call(prompt: str, max_tokens: int = 200, model: str = None) -> Optional[str]:
    """
    Send a prompt to Gemini 1.5 Flash.
    Returns the text response, or None on failure.
    All callers already handle None gracefully with rule-based fallbacks.
    """
    client = _get_client()
    if client is None:
        logger.debug("[LLM] Gemini unavailable — using rule-based fallback")
        return None
    try:
        resp = client.generate_content(prompt)
        text = resp.text.strip() if resp.text else ""
        logger.debug(f"[LLM] Gemini → {len(text)} chars")
        return text or None
    except Exception as e:
        logger.warning(f"[LLM] Gemini call failed: {e}")
        return None
