"""
LLM Helper — Ollama wrapper with manual CPU / GPU selection.

Device is chosen by the user via the frontend toggle (POST /api/llm/config).
No auto-detection — the user knows their hardware best.

Device configs (hardcoded for target hardware):
  CPU  → phi3:mini     (2.3 GB, ~15-20 tok/s on i7-13th gen)
  GPU  → llama3.1:8b   (4.7 GB Q4, ~70 tok/s on RTX 4060 8 GB VRAM)

Usage:
  from backend.llm import llm_call, ollama_available, get_device, set_device
"""
import os
from functools import lru_cache
from typing import Optional
from loguru import logger

try:
    import requests as _requests
except ImportError:
    _requests = None

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ── Manually-set device (changed at runtime via set_device()) ──────────────────
_DEVICE: str = "cpu"   # default; frontend can change to "gpu"

# ── Fixed configs per device ───────────────────────────────────────────────────
_CONFIGS = {
    "cpu": {
        "model":      "phi3:mini",
        "num_gpu":    0,            # all layers on CPU
        "num_thread": os.cpu_count() or 8,
        "num_ctx":    2048,
        "timeout":    240,
        "label":      "CPU — phi3:mini (i7-13th gen, ~15-20 tok/s)",
    },
    "gpu": {
        "model":      "llama3.1:8b",
        "num_gpu":    -1,           # all layers on GPU
        "num_ctx":    4096,
        "timeout":    90,
        "label":      "GPU — llama3.1:8b (RTX 4060 8 GB, ~70 tok/s)",
    },
}

# System prompt injected into every credit-analysis call
_SYSTEM = (
    "You are an expert Indian credit analyst with 20 years of corporate lending experience. "
    "Be concise and factual. Use RBI/Basel/Indian-banking terminology. "
    "Reply in plain English only. No markdown, no headers, no bullet points unless explicitly asked."
)


# ── Device management ──────────────────────────────────────────────────────────

def set_device(device: str) -> None:
    """Switch between 'cpu' and 'gpu'. Clears Ollama availability cache."""
    global _DEVICE
    if device not in _CONFIGS:
        raise ValueError(f"device must be one of {list(_CONFIGS)}, got {device!r}")
    _DEVICE = device
    ollama_available.cache_clear()
    logger.info(f"[LLM] Device switched to {device.upper()} — model={_CONFIGS[device]['model']}")


def get_device() -> str:
    return _DEVICE


def get_config() -> dict:
    return _CONFIGS[_DEVICE].copy()


# ── Ollama availability ────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def ollama_available() -> bool:
    """Pings Ollama once; result cached until set_device() clears it."""
    if _requests is None:
        return False
    try:
        r = _requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if r.status_code == 200:
            tags = [m.get("name", "") for m in r.json().get("models", [])]
            cfg  = get_config()
            logger.info(
                f"[LLM] Ollama running — device={_DEVICE.upper()}, "
                f"model={cfg['model']}, pulled={tags or 'none'}"
            )
            return True
    except Exception:
        pass
    logger.info("[LLM] Ollama not reachable — LLM features disabled (rule-based fallbacks active)")
    return False


# ── Core call ──────────────────────────────────────────────────────────────────

def llm_call(prompt: str, max_tokens: int = 200, model: str = None) -> Optional[str]:
    """
    Send a prompt to Ollama. Returns None on failure — all callers handle None gracefully.

    CPU mode: caps max_tokens at 150 to keep latency reasonable.
    GPU mode: uses the full requested token count.
    """
    if not ollama_available():
        return None

    cfg     = get_config()
    m       = model or cfg["model"]
    timeout = cfg["timeout"]

    # CPU: cap tokens to keep response time under ~30s
    if _DEVICE == "cpu":
        max_tokens = min(max_tokens, 150)

    full_prompt = f"{_SYSTEM}\n\n{prompt}"

    options: dict = {
        "num_predict": max_tokens,
        "temperature": 0.1,
        "top_p":       0.9,
        "num_gpu":     cfg["num_gpu"],
        "num_ctx":     cfg["num_ctx"],
    }
    if _DEVICE == "cpu":
        options["num_thread"] = cfg["num_thread"]

    try:
        resp = _requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": m, "prompt": full_prompt, "stream": False, "options": options},
            timeout=timeout,
        )
        if resp.status_code == 200:
            text = resp.json().get("response", "").strip()
            logger.debug(f"[LLM] {m} ({_DEVICE.upper()}) → {len(text)} chars")
            return text or None
        logger.warning(f"[LLM] Ollama HTTP {resp.status_code}")
    except _requests.exceptions.Timeout:
        logger.warning(f"[LLM] Timeout after {timeout}s — model may still be loading")
    except Exception as e:
        logger.warning(f"[LLM] Call failed: {e}")
    return None
