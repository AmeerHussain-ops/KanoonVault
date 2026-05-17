# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Add OCR image fallback using `pytesseract` + system Tesseract binary.
- Add FTS5 query sanitization to avoid syntax errors for case-scoped queries.
- Add `.gitignore`, `.env.example`, and `config.py` environment variable handling.
- Add `README.md`, `LICENSE` (MIT), `scripts/ci_smoke.py`, and GitHub Actions workflow.
- Update `start.bat` to prefer Python 3.10 for PaddleOCR compatibility.

## [0.1.0] - 2026-05-16
- Initial stabilization and repository preparation for public release.
