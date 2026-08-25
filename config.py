"""
KanoonVault Configuration
Sensitive keys are read from environment variables to avoid accidental commits.
Create a `.env` file locally or set env vars in your environment.
"""
import os
from pathlib import Path


def _load_dotenv():
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# ── API Key Resolution (Dynamic) ──────────────────────────────────────────
def get_api_key(key_type: str = "OPENROUTER") -> str:
    """Dynamically get the API key from credentials manager, .env file, or environment."""
    try:
        from credentials import load_api_key
        key = load_api_key(key_type)
        if key and key.strip():
            return key.strip()
    except Exception:
        pass

    env_map = {
        "OPENROUTER": "OPENROUTER_API_KEY",
        "OCR_VISION": "OCR_VISION_API_KEY",
        "TIMELINE": "TIMELINE_API_KEY",
    }
    env_var = env_map.get(key_type, f"{key_type}_API_KEY")
    val = os.getenv(env_var, "").strip()
    if val:
        return val

    # Fallback to OPENROUTER_API_KEY if specific key not set
    return os.getenv("OPENROUTER_API_KEY", "").strip()


_openrouter_default_url = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "z-ai/glm-5.2:free")
OPENROUTER_FALLBACK_MODEL = os.getenv("OPENROUTER_FALLBACK_MODEL", "google/gemma-4-26b-a4b-it:free")
OPENROUTER_URL = os.getenv("OPENROUTER_URL", _openrouter_default_url)

# ── Vision OCR — GLM-OCR via Roboflow Workflow
_roboflow_ocr_url = "https://serverless.roboflow.com/ameer-hussain/workflows/glm-ocr-ocr"
OCR_VISION_API_KEY = os.getenv("OCR_VISION_API_KEY", "") or os.getenv("TIMELINE_API_KEY", "")
OCR_VISION_MODEL = os.getenv("OCR_VISION_MODEL", "GLM-OCR")
OCR_VISION_URL = os.getenv("OCR_VISION_URL", _roboflow_ocr_url)

# ── Timeline extraction (text-only, from OCR output)
TIMELINE_API_KEY = os.getenv("TIMELINE_API_KEY", "")
TIMELINE_MODEL = os.getenv("TIMELINE_MODEL", "GLM-OCR")
TIMELINE_URL = os.getenv("TIMELINE_URL", OPENROUTER_URL)

# Maximum OCR context characters sent to LLM (to fit in context window)
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))

# Upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# Server port (used in start.bat)
PORT = int(os.getenv("PORT", "8000"))
