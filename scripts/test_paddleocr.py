"""
Test script for PaddleOCR.
Usage:
  py -3.10 scripts\test_paddleocr.py ocr_test_image.png

This script requires PaddleOCR to be installed in the Python interpreter you run it with.
"""
import sys
from pathlib import Path

try:
    from paddleocr import PaddleOCR
except Exception as e:
    print('ERROR: paddleocr import failed:', e)
    print('Ensure you are running under Python 3.10 and have installed:')
    print('  pip install paddlepaddle==2.6.2 paddleocr==2.9.1')
    sys.exit(2)

img_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('ocr_test_image.png')
if not img_path.exists():
    print('ERROR: image not found:', img_path)
    sys.exit(2)

print('Using PaddleOCR to OCR', img_path)
ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
try:
    result = ocr.ocr(str(img_path), cls=True)
    lines = []
    for block in result:
        if block:
            for line in block:
                if line and len(line) >= 2 and line[1]:
                    text, conf = line[1][0], line[1][1]
                    lines.append(f"{text}  (conf={conf})")
    print('\n'.join(lines) if lines else '[no text detected]')
except Exception as e:
    print('PaddleOCR runtime error:', e)
    sys.exit(3)
