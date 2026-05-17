# Contributing to KanoonVault

Thank you for your interest in contributing.

## Development setup

1. **Python 3.10.x** (required for PaddleOCR)
2. Clone the repo and create a virtual environment:
   ```bash
   py -3.10 -m venv .venv
   .venv\Scripts\activate    # Windows
   source .venv/bin/activate # macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment template and add your keys (never commit `.env`):
   ```bash
   copy .env.example .env   # Windows
   cp .env.example .env     # macOS/Linux
   ```
5. Run the app:
   ```bash
   py -3.10 -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```
   Or on Windows: `start.bat`

## Pull requests

- Fork the repository, create a feature branch, and open a PR against `main`.
- Keep changes focused; describe what changed and how you tested it.
- Do not commit secrets, databases, or files from `uploads/`.

## Tests

```bash
py -3.10 scripts/ci_smoke.py --offline
py -3.10 scripts/test_dual_ocr.py path/to/sample.png
```

## Code style

- Match existing patterns in `services/` and `main.py`.
- Prefer small, readable functions over large refactors in drive-by PRs.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
