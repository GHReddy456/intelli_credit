"""
run.py — one-command startup for Intelli-Credit backend.

Usage:
    python run.py              # start API on port 8000
    python run.py --demo       # generate demo data, then start
    python run.py --train      # force-retrain ML model, then start
    python run.py --help
"""
import sys
import os
import argparse

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(__file__))


def train_model():
    print("[boot] Training / loading ML model…")
    from models.credit_model import CreditModel
    from backend.config import FEATURE_NAMES
    CreditModel()
    print(f"[boot] Model ready. Features: {len(FEATURE_NAMES)}")


def generate_demo():
    print("[boot] Generating demo documents…")
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "gen", pathlib.Path(__file__).parent / "demo_data" / "generate_demo.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)


def start_server(host="0.0.0.0", port=8000, reload=False):
    import uvicorn
    print(f"[boot] Starting Intelli-Credit API on http://{host}:{port}")
    print(f"[boot] API docs -> http://localhost:{port}/docs")
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


def main():
    parser = argparse.ArgumentParser(description="Intelli-Credit startup")
    parser.add_argument("--demo",   action="store_true", help="Generate demo documents first")
    parser.add_argument("--train",  action="store_true", help="Force retrain ML model")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn hot-reload (dev mode)")
    parser.add_argument("--port",   type=int, default=8000)
    args = parser.parse_args()

    print("=" * 60)
    print("   INTELLI-CREDIT — AI Corporate Credit Appraisal Engine")
    print("=" * 60)

    if args.demo:
        generate_demo()

    if args.train:
        # Remove cached model so it retrains
        from backend.config import MODEL_DIR
        import shutil
        mpath = os.path.join(MODEL_DIR, "credit_model.pkl")
        if os.path.exists(mpath):
            os.remove(mpath)
            print("[boot] Removed cached model — will retrain")

    train_model()
    start_server(port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
