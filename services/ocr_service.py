"""
KanoonVault OCR Service
Handles: PDF (PyMuPDF), Images (JPG/PNG), Plain text

PDFs (PyMuPDF / fitz):
  - Text-layer pages: page.get_text()
  - Scanned pages: render to PNG via get_pixmap(), then dual OCR below

Images and scanned PDF pages:
  - PaddleOCR (primary, Python 3.10.x) + Tesseract fallback
  - Gemma 4 Vision (when OCR_VISION_API_KEY is set), run in parallel
  - Final text = consensus merge (lines/words both engines agree on)
"""
import io
import os
import re
import sys
import base64
import httpx
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import OCR_VISION_API_KEY, OCR_VISION_MODEL, OCR_VISION_URL

_LINE_MATCH_THRESHOLD = 0.50

# ── PyMuPDF – required for PDFs ───────────────────────────────────────────
PYMUPDF_AVAILABLE = False
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    pass

# ── PaddleOCR – optional (not yet available for Python 3.12+) ─────────────
PADDLE_AVAILABLE = False
try:
    if sys.version_info < (3, 12):
        from paddleocr import PaddleOCR
        PADDLE_AVAILABLE = True
except ImportError:
    pass

# ── Tesseract OCR – fallback for images ───────────────────────────────────
TESSERACT_AVAILABLE = False
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    pass

_ocr_engine = None


def _get_ocr():
    global _ocr_engine
    if _ocr_engine is None and PADDLE_AVAILABLE:
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _ocr_engine


def _preprocess_image_for_ocr(img):
    """
    Enhance image quality for better OCR accuracy.
    Critical for WhatsApp images, scans, and low-contrast documents.
    """
    from PIL import Image, ImageEnhance, ImageFilter

    if img.mode != 'RGB':
        img = img.convert('RGB')

    w, h = img.size
    if w < 1500:
        scale = max(2, 1500 // w)
        img = img.resize((w * scale, h * scale), Image.LANCZOS)

    img = img.convert('L')

    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    img = img.filter(ImageFilter.SHARPEN)
    return img


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lower())


def _normalize_token(word: str) -> str:
    return re.sub(r"[^\w]", "", word.lower())


def _parse_paddle_result(result) -> str:
    lines = []
    if not result:
        return ""
    for block in result:
        if not block:
            continue
        for line in block:
            if line and len(line) >= 2 and line[1]:
                text, conf = line[1][0], line[1][1]
                if conf > 0.4:
                    lines.append(text.strip())
    return "\n".join(lines)


def _ocr_paddle(image_bytes: bytes) -> str:
    from PIL import Image
    import numpy as np

    ocr = _get_ocr()
    img = Image.open(io.BytesIO(image_bytes))
    img = _preprocess_image_for_ocr(img)
    arr = np.array(img.convert("RGB"))
    return _parse_paddle_result(ocr.ocr(arr, cls=True))


def _ocr_tesseract(image_bytes: bytes) -> str:
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    img = _preprocess_image_for_ocr(img)
    return pytesseract.image_to_string(img, config=r"--oem 3 --psm 6")


def _ocr_local(image_bytes: bytes) -> str:
    """Local OCR: PaddleOCR first, then Tesseract."""
    paddle_text = ""
    if PADDLE_AVAILABLE:
        paddle_text = _ocr_paddle(image_bytes)
        if paddle_text and len(paddle_text.strip()) > 10:
            return paddle_text

    if TESSERACT_AVAILABLE:
        text = _ocr_tesseract(image_bytes)
        if text and len(text.strip()) > 0:
            return text

    if paddle_text:
        return paddle_text

    return "[Image OCR not available — use Python 3.10.x and install paddleocr]"


def _pick_consensus_line(paddle_line: str, gemma_line: str) -> str:
    """Keep words that appear in both lines (paddle order); else use richer line."""
    paddle_words = re.findall(r"\S+", paddle_line)
    gemma_norm = {_normalize_token(w) for w in re.findall(r"\S+", gemma_line)}
    common = [w for w in paddle_words if _normalize_token(w) in gemma_norm]

    min_common = max(1, min(len(paddle_words), len(gemma_norm)) // 3)
    if len(common) >= min_common:
        return " ".join(common)

    return paddle_line if len(paddle_line) >= len(gemma_line) else gemma_line


def _line_supported_in(text: str, line: str) -> bool:
    """True if most tokens in line also appear somewhere in full text."""
    tokens = [_normalize_token(w) for w in re.findall(r"\S+", line) if _normalize_token(w)]
    if not tokens:
        return False
    haystack = _normalize_line(text)
    hits = sum(1 for t in tokens if t in haystack)
    return hits >= max(1, len(tokens) * 2 // 3)


def _reconcile_ocr_texts(paddle_text: str, gemma_text: str) -> str:
    """
    Merge PaddleOCR and Gemma 4 outputs.
    Matched lines use shared words; unmatched paddle lines are kept;
    gemma-only lines are added only when supported by paddle full text.
    """
    if not gemma_text or not gemma_text.strip():
        return paddle_text
    if not paddle_text or not paddle_text.strip() or paddle_text.startswith("[Image OCR"):
        return gemma_text

    p_lines = [l.strip() for l in paddle_text.splitlines() if l.strip()]
    g_lines = [l.strip() for l in gemma_text.splitlines() if l.strip()]
    used_g = set()
    merged = []

    for pl in p_lines:
        best_i, best_r = -1, 0.0
        pn = _normalize_line(pl)
        for i, gl in enumerate(g_lines):
            if i in used_g:
                continue
            r = SequenceMatcher(None, pn, _normalize_line(gl)).ratio()
            if r > best_r:
                best_r, best_i = r, i

        if best_i >= 0 and best_r >= _LINE_MATCH_THRESHOLD:
            used_g.add(best_i)
            merged.append(_pick_consensus_line(pl, g_lines[best_i]))
        else:
            merged.append(pl)

    for i, gl in enumerate(g_lines):
        if i not in used_g and len(gl) > 15 and _line_supported_in(paddle_text, gl):
            merged.append(gl)

    result = "\n".join(merged)
    if len(result.strip()) < 15:
        return paddle_text if len(paddle_text) >= len(gemma_text) else gemma_text
    return result


def _dual_ocr_pipeline(image_bytes: bytes, extension: str, label: str = "") -> str:
    """Run PaddleOCR + Gemma 4, return consensus-merged text."""
    tag = label or "image"
    print(f"[OCR] PaddleOCR (primary) for: {tag}")
    local = _ocr_local(image_bytes)

    gemma = ""
    if OCR_VISION_API_KEY:
        print(f"[OCR] Gemma 4 Vision for: {tag}")
        gemma = _ocr_vision_llm(image_bytes, extension)
    else:
        print(f"[OCR] Gemma 4 skipped (set OCR_VISION_API_KEY for dual OCR)")

    local_ok = local and not local.startswith("[Image OCR") and len(local.strip()) > 0
    gemma_ok = bool(gemma and len(gemma.strip()) > 0)

    if local_ok and gemma_ok:
        merged = _reconcile_ocr_texts(local, gemma)
        print(f"[OCR] Consensus merge -> {len(merged)} chars for: {tag}")
        return merged
    if local_ok:
        print(f"[OCR] Local only -> {len(local)} chars for: {tag}")
        return local
    if gemma_ok:
        print(f"[OCR] Gemma 4 only -> {len(gemma)} chars for: {tag}")
        return gemma
    return local or gemma or ""


def get_ocr_engine() -> str:
    parts = []
    if PYMUPDF_AVAILABLE:
        parts.append("pymupdf")
    if PADDLE_AVAILABLE:
        parts.append("paddleocr")
    elif TESSERACT_AVAILABLE:
        parts.append("tesseract")
    if OCR_VISION_API_KEY:
        parts.append("gemma4")
    return "+".join(parts) if parts else "none"


def vision_ocr_available() -> bool:
    return bool(OCR_VISION_API_KEY)


def _clean_ocr_text(raw: str) -> str:
    """Remove common OCR noise while preserving legal structure."""
    raw = re.sub(r"[-_=]{3,}", "", raw)
    lines = [l.strip() for l in raw.splitlines()]
    lines = [l for l in lines if len(l) > 1]
    return "\n".join(lines)


def _chunk_text_by_section(text: str) -> list[str]:
    """Split extracted text into logical legal chunks."""
    section_patterns = [
        r"\bFIR\b", r"\bFirst Information Report\b",
        r"\bCourt Order\b", r"\bJudgment\b",
        r"\bWitness Statement\b", r"\bAffidavit\b",
        r"\bApplication\b", r"\bPetition\b",
        r"\bComplaint\b", r"\bNotice\b",
        r"\bHearing\b",
    ]
    pattern = "|".join(section_patterns)
    parts = re.split(f"(?i)({pattern})", text)
    chunks = []
    current = ""
    for part in parts:
        current += part
        if re.search(pattern, part, re.IGNORECASE) and len(current) > 200:
            chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]


# ─── Main public interface ──────────────────────────────────────────────────

def extract_text(filepath: str | Path, file_type: str) -> tuple[str, list[str]]:
    """
    Extract text from any supported file.
    Returns (full_text, chunks)
    """
    filepath = Path(filepath)
    raw = ""

    if file_type == "pdf":
        raw = _extract_pdf(filepath)
    elif file_type in ("jpg", "jpeg", "png", "bmp", "tiff", "webp"):
        raw = _extract_image(filepath)
    elif file_type in ("txt", "text"):
        raw = filepath.read_text(encoding="utf-8", errors="ignore")
    else:
        raw = ""

    cleaned = _clean_ocr_text(raw)
    chunks = _chunk_text_by_section(cleaned)
    return cleaned, chunks


def _extract_pdf(filepath: Path) -> str:
    """Extract text from PDF using PyMuPDF; dual OCR on scanned pages."""
    if not PYMUPDF_AVAILABLE:
        return "[PDF processing unavailable — install PyMuPDF: pip install PyMuPDF==1.24.14]"

    import fitz

    doc = fitz.open(str(filepath))
    all_text = []

    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()

        if len(text) < 50:
            if PADDLE_AVAILABLE or TESSERACT_AVAILABLE or OCR_VISION_API_KEY:
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                label = f"{filepath.name} page {page_num + 1}"
                text = _dual_ocr_pipeline(img_bytes, ".png", label)
            else:
                text = f"[Page {page_num + 1}: scanned image – OCR unavailable]"

        if text:
            all_text.append(f"[Page {page_num + 1}]\n{text}")

    doc.close()
    return "\n\n".join(all_text)


def _extract_image(filepath: Path) -> str:
    """PaddleOCR + Gemma 4 dual OCR with consensus merge."""
    return _dual_ocr_pipeline(
        filepath.read_bytes(),
        filepath.suffix.lower(),
        filepath.name,
    )


# ── Vision LLM OCR (Gemma 4 via OpenRouter) ───────────────────────────────

VISION_OCR_PROMPT = """You are a document OCR engine. Extract ALL text from this image exactly as written.

RULES:
- Reproduce the text as faithfully as possible
- Preserve dates, names, numbers, legal terms, case numbers, FIR numbers
- If the image contains a legal document (FIR, court order, petition), extract every detail
- Include section headers, dates, party names, court names, police station names
- If text is in Urdu/Hindi alongside English, extract BOTH languages
- Do NOT add any commentary, just output the raw extracted text
- If you cannot read certain parts clearly, make your best guess and include it"""


def _ocr_vision_llm(image_bytes: bytes, extension: str = ".jpg") -> str:
    """Use Gemma 4 Vision to extract text from an image via OpenRouter.
    Retries on 429 rate limit errors with exponential backoff."""
    import time

    if not OCR_VISION_API_KEY:
        return ""

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".webp": "image/webp",
    }
    mime = mime_map.get(extension, "image/jpeg")

    # Roboflow Serverless Workflow endpoint support
    if "roboflow.com" in OCR_VISION_URL.lower():
        url = OCR_VISION_URL
        if "api_key=" not in url and OCR_VISION_API_KEY:
            url += f"{'&' if '?' in url else '?'}api_key={OCR_VISION_API_KEY}"

        payload = {
            "inputs": {
                "image": {
                    "type": "base64",
                    "value": b64
                }
            }
        }
        headers = {"Content-Type": "application/json"}
        if OCR_VISION_API_KEY:
            headers["Authorization"] = f"Bearer {OCR_VISION_API_KEY}"

        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()

            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            if isinstance(data, dict):
                outputs = data.get("outputs") or data.get("output") or data.get("predictions") or data
                if isinstance(outputs, list) and len(outputs) > 0:
                    outputs = outputs[0]
                if isinstance(outputs, dict):
                    content = outputs.get("ocr") or outputs.get("text") or outputs.get("result") or outputs.get("content") or str(outputs)
                    return str(content).strip()
                elif isinstance(outputs, str):
                    return outputs.strip()
            return str(data).strip()
        except Exception as e:
            print(f"[OCR Vision LLM - Roboflow] Error: {e}")
            return ""

    payload = {
        "model": OCR_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {OCR_VISION_API_KEY}",
        "Content-Type": "application/json",
    }

    # Retry with backoff: 5s, 15s, 30s
    delays = [5, 15, 30]
    for attempt in range(len(delays) + 1):
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(OCR_VISION_URL, json=payload, headers=headers)
                resp.raise_for_status()

            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < len(delays):
                wait = delays[attempt]
                print(f"[OCR Vision LLM] Rate limited (429), retrying in {wait}s... (attempt {attempt + 1}/{len(delays)})")
                time.sleep(wait)
                continue
            print(f"[OCR Vision LLM] Error: {e}")
            return ""
        except Exception as e:
            print(f"[OCR Vision LLM] Error: {e}")
            return ""
        return ""


def get_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext if ext else "unknown"
