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

# ── Chat (OpenRouter) — z-ai/glm-4.5-air:free
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.5-air:free")
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")

# ── Vision OCR (OpenRouter) — google/gemma-4-31b-it:free (dual OCR with PaddleOCR)
_openrouter_default_url = "https://openrouter.ai/api/v1/chat/completions"
OCR_VISION_API_KEY = os.getenv("OCR_VISION_API_KEY", "") or os.getenv("TIMELINE_API_KEY", "")
OCR_VISION_MODEL = os.getenv("OCR_VISION_MODEL", "google/gemma-4-31b-it:free")
OCR_VISION_URL = os.getenv("OCR_VISION_URL", os.getenv("TIMELINE_URL", _openrouter_default_url))

# ── Timeline extraction (text-only, from OCR output)
TIMELINE_API_KEY = os.getenv("TIMELINE_API_KEY", "")
TIMELINE_MODEL = os.getenv("TIMELINE_MODEL", "google/gemma-4-31b-it:free")
TIMELINE_URL = os.getenv("TIMELINE_URL", _openrouter_default_url)

# Maximum OCR context characters sent to LLM (to fit in context window)
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))

# Upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# Server port (used in start.bat)
PORT = int(os.getenv("PORT", "8000"))
