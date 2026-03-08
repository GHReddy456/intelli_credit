"""
Ollama Setup Script for credON (CPU-only)
==========================================
Run this once to install Ollama and download phi3:mini.

Usage:
    python ollama_setup.py

What it does:
    1. Checks if Ollama CLI is installed; if not, prints download link.
    2. Checks if Ollama server is running; if not, starts it.
    3. Pulls phi3:mini (3.8B, ~2.3 GB) — works entirely on CPU, no GPU needed.
    4. Sends a test prompt and prints the response.
    5. Prints the env vars you need to set to enable LLM in credON.

CPU performance reference (phi3:mini):
    4-core laptop (Intel i5/Ryzen 5) : ~6-10 tokens/s  (~20-30s for 200 tokens)
    8-core desktop (i7/Ryzen 7)     : ~12-18 tokens/s  (~11-17s for 200 tokens)
    16-core workstation             : ~20-30 tokens/s  (~7-10s for 200 tokens)

Lighter alternatives (less quality but faster on CPU):
    gemma3:1b   — 815 MB — ~20 tokens/s on medium laptop
    qwen2:0.5b  — 394 MB — ~35 tokens/s, smallest available
"""
import subprocess
import sys
import time
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL      = "phi3:mini"


def run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=capture, text=True)


def check_ollama_installed() -> bool:
    r = run(["ollama", "--version"])
    return r.returncode == 0


def check_ollama_running() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def start_ollama_server():
    """Start 'ollama serve' as a background process."""
    print("  Starting Ollama server in background...")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait up to 10s for it to become ready
    for i in range(10):
        time.sleep(1)
        if check_ollama_running():
            print("  Ollama server started.")
            return True
        print(f"  Waiting... ({i+1}/10)")
    return False


def list_pulled_models() -> list[str]:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def pull_model(model: str):
    """Pull model with live progress output."""
    print(f"\n  Pulling {model} — this downloads ~2.3 GB on first run.")
    print("  Progress will appear below (Ctrl+C to cancel):\n")
    result = run(["ollama", "pull", model], capture=False)
    return result.returncode == 0


def test_inference(model: str) -> bool:
    """Send a short credit-analysis prompt and verify the response."""
    print(f"\n  Testing inference with {model}...")
    prompt = (
        "In one sentence, what is DSCR and why does a bank care about it "
        "when lending to an Indian SME?"
    )
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model":  model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 80, "temperature": 0.1},
            },
            timeout=120,
        )
        if resp.status_code == 200:
            text = resp.json().get("response", "").strip()
            print(f"\n  PROMPT : {prompt}")
            print(f"  RESPONSE: {text}\n")
            return bool(text)
    except Exception as e:
        print(f"  Inference test failed: {e}")
    return False


def main():
    print("=" * 60)
    print("  credON — Ollama CPU-LLM Setup")
    print("=" * 60)

    # ── 1. Check Ollama CLI ────────────────────────────────────────────
    print("\n[1/4] Checking Ollama CLI installation...")
    if check_ollama_installed():
        r = run(["ollama", "--version"])
        print(f"  Ollama installed: {r.stdout.strip()}")
    else:
        print("\n  Ollama is NOT installed.")
        print("\n  Install it now:")
        print("    Windows : Download from https://ollama.com/download/windows")
        print("              Run the installer, then re-run this script.")
        print("\n    Linux   : curl -fsSL https://ollama.com/install.sh | sh")
        print("    Mac     : brew install ollama  OR download from https://ollama.com")
        sys.exit(1)

    # ── 2. Start server if needed ─────────────────────────────────────
    print("\n[2/4] Checking Ollama server...")
    if check_ollama_running():
        print("  Ollama server is already running.")
    else:
        print("  Server not running — attempting to start...")
        if not start_ollama_server():
            print("\n  Could not start Ollama automatically.")
            print("  Run in a separate terminal:  ollama serve")
            print("  Then re-run this script.")
            sys.exit(1)

    # ── 3. Pull model ─────────────────────────────────────────────────
    print(f"\n[3/4] Checking if {MODEL} is available...")
    pulled = list_pulled_models()
    if any(MODEL in m for m in pulled):
        print(f"  {MODEL} is already downloaded. Skipping pull.")
    else:
        print(f"  Available models: {pulled or 'none'}")
        print(f"  {MODEL} not found — pulling now...")
        if not pull_model(MODEL):
            print(f"\n  Pull failed. Try manually:  ollama pull {MODEL}")
            sys.exit(1)
        print(f"  {MODEL} downloaded successfully.")

    # ── 4. Test inference ─────────────────────────────────────────────
    print("\n[4/4] Running inference test...")
    if test_inference(MODEL):
        print("  Inference test PASSED.")
    else:
        print("  Inference test failed — model may still be loading. Wait 30s and retry.")
        sys.exit(1)

    # ── Done ──────────────────────────────────────────────────────────
    print("=" * 60)
    print("  Setup complete! Activate LLM in credON:")
    print("=" * 60)
    print("""
  Option A — enable for this terminal session:
    Windows PowerShell : $env:USE_LLM="true"
    Linux/Mac bash     : export USE_LLM=true
    Then run           : python run.py

  Option B — permanent (add to .env or system environment):
    USE_LLM=true
    OLLAMA_MODEL=phi3:mini        # default, already set
    OLLAMA_BASE_URL=http://localhost:11434   # default

  Lighter/faster CPU models (lower quality):
    ollama pull gemma3:1b    # 815 MB, set OLLAMA_MODEL=gemma3:1b
    ollama pull qwen2:0.5b   # 394 MB, set OLLAMA_MODEL=qwen2:0.5b
""")


if __name__ == "__main__":
    main()
