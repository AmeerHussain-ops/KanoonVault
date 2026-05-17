"""CI smoke test: offline import checks; optional API key validation."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

offline = "--offline" in sys.argv or os.getenv("CI_OFFLINE") == "1"


def _offline_checks():
    import database as db
    from config import OPENROUTER_MODEL, OCR_VISION_MODEL, TIMELINE_MODEL
    from services.timeline_service import extract_timeline_events
    from services.ocr_service import get_ocr_engine

    db.init_db()
    events = extract_timeline_events(
        "Circuit Bench hearing scheduled for 01.12.2025 per court notification.",
        "sample.pdf",
    )
    if not events:
        print("Timeline regex smoke failed: expected at least one event", file=sys.stderr)
        sys.exit(1)

    print("Offline smoke OK")
    print(f"  chat model: {OPENROUTER_MODEL}")
    print(f"  ocr vision: {OCR_VISION_MODEL}")
    print(f"  timeline:   {TIMELINE_MODEL}")
    print(f"  ocr engine: {get_ocr_engine()}")


def _api_key_checks():
    from config import OPENROUTER_API_KEY, TIMELINE_API_KEY, OCR_VISION_API_KEY

    missing = []
    if not OPENROUTER_API_KEY:
        missing.append("OPENROUTER_API_KEY")
    if not TIMELINE_API_KEY and not OPENROUTER_API_KEY:
        missing.append("TIMELINE_API_KEY (or set OPENROUTER_API_KEY)")

    if missing:
        print("Missing required env vars:", ", ".join(missing), file=sys.stderr)
        sys.exit(1)

    if not OCR_VISION_API_KEY:
        print("Note: OCR_VISION_API_KEY not set (dual OCR vision disabled)")
    print("API key smoke OK")


if __name__ == "__main__":
    _offline_checks()
    if not offline:
        _api_key_checks()
