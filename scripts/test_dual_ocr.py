"""Test dual OCR on a sample image. Usage: py -3.10 scripts/test_dual_ocr.py [image_path]"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # loads .env via config._load_dotenv

from services.ocr_service import (
    PADDLE_AVAILABLE,
    _dual_ocr_pipeline,
    _ocr_local,
    _ocr_vision_llm,
    _reconcile_ocr_texts,
    get_ocr_engine,
    vision_ocr_available,
)

img = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "test_petition.png"
if not img.exists():
    print("ERROR: image not found:", img)
    sys.exit(1)

print("=" * 60)
print("Image:", img)
print("Engine:", get_ocr_engine())
print("Paddle available:", PADDLE_AVAILABLE)
print("Gemma available:", vision_ocr_available())
print("=" * 60)

data = img.read_bytes()
ext = img.suffix.lower()

print("\n--- PaddleOCR (local) ---\n")
local = _ocr_local(data)
print(local[:4000] if local else "(empty)")
if local and len(local) > 4000:
    print(f"\n... [{len(local)} chars total]")

if vision_ocr_available():
    print("\n--- Gemma 4 Vision ---\n")
    gemma = _ocr_vision_llm(data, ext)
    print(gemma[:4000] if gemma else "(empty)")
    if gemma and len(gemma) > 4000:
        print(f"\n... [{len(gemma)} chars total]")

    print("\n--- Consensus merge ---\n")
    merged = _reconcile_ocr_texts(local, gemma) if local and gemma else local or gemma
    print(merged[:4000] if merged else "(empty)")
    if merged and len(merged) > 4000:
        print(f"\n... [{len(merged)} chars total]")

print("\n--- Full pipeline (_dual_ocr_pipeline) ---\n")
final = _dual_ocr_pipeline(data, ext, img.name)
print(final[:4000] if final else "(empty)")
if final and len(final) > 4000:
    print(f"\n... [{len(final)} chars total]")
print("\nDone. Chars:", len(final or ""))
