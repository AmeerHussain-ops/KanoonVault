# KanoonVault — Legal Memory OS

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)

**KanoonVault** is a self-hosted legal case workspace. Upload PDFs and images, extract text with **PyMuPDF** and **PaddleOCR**, build an automatic **case timeline**, and chat with AI that answers only from your uploaded documents.

> **Privacy-first:** SQLite + local `uploads/` — no cloud document storage required.

## Table of contents

- [Features](#features)
- [System requirements](#system-requirements)
- [Installation](#installation--setup)
- [Configuration](#configuration)
- [Architecture](#architecture--how-it-works)
- [API endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Publish on GitHub](#publish-on-github)
- [License](#license)

## Features

✨ **OCR & Document Processing**
- Supports PDF, images (JPG/PNG/BMP/TIFF/WebP), and plain text files

📄 **PDF processing (PyMuPDF)** — required for all PDF uploads
- **Text-layer PDFs**: PyMuPDF (`fitz`) extracts embedded text directly (fast, no OCR)
- **Scanned PDFs**: PyMuPDF renders each page to an image, then the dual OCR pipeline runs on that page
- Installed automatically via `requirements.txt` (`PyMuPDF==1.24.14`)

🔍 **Dual OCR pipeline** (images and scanned PDF pages rendered by PyMuPDF):
  1. **PaddleOCR** (primary, Python 3.10.x) with image preprocessing
  2. **Tesseract** (local fallback if Paddle yields little text)
  3. **Gemma 4 Vision** via OpenRouter (`google/gemma-4-31b-it:free`) when `OCR_VISION_API_KEY` is set
  4. **Consensus merge** — final text favors lines and words both PaddleOCR and Gemma agree on

- Intelligent text chunking by legal sections (FIR, Court Orders, Affidavits, etc.)

🤖 **AI-Powered Chat**
- Case-specific chat grounded in uploaded documents (no external knowledge)
- Chat uses **OpenRouter** with `z-ai/glm-5.2:free` (separate from the OCR vision model)
- Full-text search (FTS5) + vector similarity search (ChromaDB embeddings)
- Per-case isolated chat histories
- Automatic source attribution with document links

📅 **Case Timeline**
- Built automatically on **document upload** and when you **open the Timeline panel** (auto-sync if OCR exists but events are missing)
- **Regex extraction** first — supports `DD.MM.YYYY`, `DD/MM/YYYY`, month names, ordinals (e.g. “20th day of March, 2023”), and noisy OCR
- **Gemma 4** via OpenRouter (`TIMELINE_MODEL`) when regex finds few events (optional; works offline with regex + heuristics)
- Events linked to source filename; undated events show as “Date unknown”
- Keywords: FIR, hearings, petitions, circuit bench, notifications, court orders, and more

💾 **Case Management**
- Create and organize multiple legal cases
- Case status tracking (active, closed, reopened)
- Soft delete + trash recovery with configurable retention
- Audit logging for all actions

🔒 **Privacy & Data Control**
- Local SQLite database (no external data storage)
- Self-hosted deployment fully under your control
- Document file storage in local `uploads/` directory

## System Requirements

### Minimum
- **Python 3.10.x** (3.10.20 recommended — required for PaddleOCR; without it, only Tesseract + optional Gemma vision OCR apply)
- **Windows 10+, Linux, or macOS**
- **2GB RAM** (more recommended for embeddings)
- **500MB disk space** (grows with uploads)

### Optional Tesseract Setup (Windows)
If not using Python 3.10/3.11:
1. Download and install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
2. Add installation directory to PATH (e.g., `C:\Program Files\Tesseract-OCR`)
3. Restart your terminal/IDE

## Installation & Setup

### Quick Start

1. **Clone or download the project**
   ```bash
   cd KanoonVault
   ```

2. **Ensure Python 3.10.x is installed** (3.10.20 recommended)
   - Check: `py -3.10 --version`
   - Download from [python.org](https://www.python.org/downloads/)

3. **Configure API keys** (copy `.env.example` → `.env`)
   ```bash
   copy .env.example .env
   ```
   Set your OpenRouter key for chat, vision OCR, and timeline. See [Configuration](#configuration).

4. **Run the startup script**
   ```bash
   .\start.bat
   ```
   This will:
   - Verify Python 3.10.x is available
   - Install dependencies (first run only)
   - Verify **PyMuPDF** and **PaddleOCR** imports
   - Start the FastAPI server at `http://localhost:8000`

5. **Open the app**
   - Browser: [http://localhost:8000](http://localhost:8000)
   - Upload a legal document to get started

### Manual Installation

```bash
# Use Python 3.10 for PaddleOCR
py -3.10 -m pip install -r requirements.txt

# Start the server
py -3.10 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Project Structure

```
KanoonVault/
├── main.py                      # FastAPI backend (uploads, chat, cases, documents)
├── database.py                  # SQLite ORM and FTS5 search
├── models.py                    # Pydantic data models
├── config.py                    # Settings (loads from `.env`)
├── .env.example                 # Template for API keys and models
├── requirements.txt             # Python dependencies
├── start.bat                    # Windows startup script
│
├── services/
│   ├── ocr_service.py          # Dual OCR: PaddleOCR + Gemma 4 consensus merge
│   ├── llm_service.py          # OpenRouter streaming + source attribution
│   ├── case_service.py         # Upload pipeline + timeline sync
│   ├── timeline_service.py     # Regex + LLM date/event extraction
│   └── vector_memory_service.py # FTS5 + ChromaDB hybrid search
│
├── frontend/
│   ├── index.html              # Web UI
│   ├── app.js                  # Reactive case/chat logic
│   └── style.css               # Styling (dark legal theme)
│
├── uploads/                    # Stored document files
├── chroma_db/                  # ChromaDB vector database
├── kanoonvault.db              # SQLite database
├── scripts/
│   └── test_dual_ocr.py        # Test PaddleOCR + Gemma on a sample image
└── README.md                   # This file
```

## Configuration

All secrets and model names live in a local **`.env`** file (never commit it). `config.py` loads `.env` on startup.

Copy the template and fill in your keys:

```bash
copy .env.example .env
```

### Environment variables

| Variable | Purpose | Default model |
|----------|---------|----------------|
| `OPENROUTER_API_KEY` | Case chat (Q&A) | — |
| `OPENROUTER_MODEL` | Chat model | `z-ai/glm-5.2:free` |
| `OCR_VISION_API_KEY` | Vision OCR (dual OCR with Paddle) | — |
| `OCR_VISION_MODEL` | Vision OCR model | `google/gemma-4-31b-it:free` |
| `TIMELINE_API_KEY` | Timeline date/event extraction | — |
| `TIMELINE_MODEL` | Timeline model | `google/gemma-4-31b-it:free` |
| `MAX_CONTEXT_CHARS` | Max OCR text sent to chat LLM | `6000` |
| `PORT` | Server port | `8000` |

Example `.env` (use your own key; do not commit):

```env
# Chat — GLM (not used for OCR)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=z-ai/glm-5.2:free

# Vision OCR — Gemma 4 (dual OCR with PaddleOCR)
OCR_VISION_API_KEY=sk-or-v1-...
OCR_VISION_MODEL=google/gemma-4-31b-it:free

# Timeline extraction
TIMELINE_API_KEY=sk-or-v1-...
TIMELINE_MODEL=google/gemma-4-31b-it:free
```

You can use the same OpenRouter key for all three. Chat and OCR use **different models** on purpose.

**Free API keys:** https://openrouter.ai — models above are free-tier eligible.

### Test OCR locally

```bash
py -3.10 scripts\test_dual_ocr.py path\to\scan.png
```

On server startup, logs show the active OCR stack, e.g. `Primary OCR engine: pymupdf+paddleocr+gemma4`.

## Architecture & How It Works

### Document Processing Pipeline
```
Upload → Dual OCR/Extract → Text Chunks → FTS5 Index + Embeddings → Storage
```

1. **OCR Service** extracts text:
   - **All PDFs** opened with **PyMuPDF** (`import fitz`)
   - PDF with selectable text → `page.get_text()` (no OCR)
   - PDF with scanned/empty pages → PyMuPDF `get_pixmap()` → dual OCR (PaddleOCR + Gemma consensus)
   - Standalone images → same dual OCR pipeline (no PyMuPDF)
2. **Text Chunking** splits content by legal sections
3. **Embedding Creation** generates vector embeddings (sentence-transformers)
4. **Dual Indexing**:
   - **FTS5** (full-text search) for keyword queries
   - **ChromaDB** (vector search) for semantic similarity

### Chat/Query Flow
```
User Question → Retrieve Chunks (FTS + Vector) → LLM Prompt → Stream Response
```

1. Sanitizes user input (prevents FTS5 syntax errors)
2. Searches both FTS and vector databases
3. Merges results with deduplication
4. Formats context for LLM with source attribution
5. Streams response tokens (Server-Sent Events)
6. Appends source links and document references

### Timeline Pipeline
```
Upload OCR text → extract_timeline_events() → timeline_events table
Open Timeline panel → GET /timeline/{case_id} → auto-sync if empty but OCR exists
```

1. **On upload** — `process_upload()` runs timeline extraction and stores events per document
2. **On open** — if a case has stored OCR but no timeline rows, the server rebuilds from all documents automatically (no manual action)
3. **Extraction order** — regex dates + legal keywords → optional Gemma 4 LLM → heuristic keyword fallback → minimum one “document processed” event if text is substantial

### Case Isolation
- Each case has its own document collection
- Chat history stored per-case (restored when case is reopened)
- Query results filtered to active cases only
- Trash cases excluded from default queries

## Recommended Open Source Repos
These repositories are strong references for KanoonVault’s legal memory, retrieval, OCR, and memory OS architecture.

### Semantic RAG / Retrieval
- LlamaIndex — https://github.com/run-llama/llama_index
  - Core inspiration for chunk indexing, hierarchical retrieval, and metadata-aware search.
  - Your system is a simplified LlamaIndex + SQL control layer.
- LangChain — https://github.com/langchain-ai/langchain
  - Multi-step retrieval orchestration and tool-calling patterns.
  - Used as a design reference only, not a runtime dependency.
- RAG — https://github.com/ThomasJay/RAG
  - Minimal RAG pipeline reference.
  - Validates chunk injection and retrieval correctness.
- Ragent — https://github.com/nageoffer/ragent
  - Query decomposition and retrieval ranking inspiration.
  - Improves hybrid ranking logic design.

### Memory OS / Persistent Memory
- MemoryOS — https://github.com/BAI-LAB/MemoryOS
  - Persistent multi-layer memory design.
  - Inspires case isolation, timeline storage, and structured memory retrieval.
- EverOS — https://github.com/EverMind-AI/EverOS
  - Full AI OS architecture reference.
  - Useful for future tool + memory + agent integration.
- AgentOS — https://github.com/SpharxTeam/AgentOS
  - Multi-agent workflows for OCR, timeline, and retrieval agents.
- Memvid — https://github.com/memvid/memvid
  - Experimental long-term memory compression.
  - Useful for archiving old legal cases and reducing storage footprint.

### OCR & PDF Stack
- **PyMuPDF** — https://github.com/pymupdf/PyMuPDF
  - Required for every PDF: text extraction and page rendering for scanned pages.
  - Python package: `PyMuPDF` (import as `fitz`).
- PaddleOCR — https://github.com/PaddlePaddle/PaddleOCR
  - Primary local OCR engine (Python 3.10.x). Used after PyMuPDF renders scanned PDF pages, and for images.
- Gemma 4 Vision (`google/gemma-4-31b-it:free` via OpenRouter)
  - Secondary vision OCR; merged with Paddle output for higher accuracy on hard scans.
  - Configured via `OCR_VISION_*` in `.env` (not the chat model).
- Paddle2ONNX — https://github.com/PaddlePaddle/Paddle2ONNX
  - Converts OCR models for production speed and faster inference.
- PaddleOCR-json — https://github.com/hiroi-sora/PaddleOCR-json
  - Converts raw OCR output to structured JSON.
  - Improves timeline extraction and case metadata detection.

## Design References
For a broader architectural view, see `DESIGN_REFERENCES.md`.

## API Endpoints

### Cases
- `GET /cases` — List all active cases
- `POST /case/create` — Create a new case
- `GET /case/{case_id}` — Get case details
- `POST /case/update/{case_id}` — Update case status
- `POST /case/delete/{case_id}` — Soft delete a case

### Documents
- `POST /upload?case_id={id}` — Upload document to case
- `GET /documents/{doc_id}/preview` — Preview document text
- `GET /documents/{doc_id}/open` — Download/view full document

### Chat & Search
- `POST /chat/query` — Stream LLM response (Server-Sent Events)
- `POST /ocr/process` — Extract text from file (standalone)

### Timeline
- `GET /timeline/{case_id}` — List timeline events (auto-builds from stored OCR if the timeline is empty)
- `POST /timeline/event` — Manually add a timeline event

## Troubleshooting

### "Python 3.10.x is required"
- **Issue**: Running Python 3.11+ (no PaddleOCR)
- **Solution**: 
  - Install Python 3.10.20 alongside, OR
  - Install Tesseract OCR (fallback for images)

### PDF upload fails or no text from PDF
- **Issue**: PDFs not processed
- **Solutions**:
  1. Ensure PyMuPDF is installed: `py -3.10 -m pip install PyMuPDF==1.24.14`
  2. Re-run `start.bat` or `pip install -r requirements.txt`
  3. For scanned PDFs, also need PaddleOCR (Python 3.10) and optionally `OCR_VISION_API_KEY` for Gemma

### "Image OCR not available"
- **Issue**: Images not being OCR'd
- **Solutions**:
  1. Use Python 3.10: `py -3.10 -m pip install paddlepaddle==2.6.2 paddleocr==2.9.1`
  2. Install Tesseract: [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
  3. Ensure `pytesseract` is installed: `pip install pytesseract`

### Dual OCR / Gemma 4 not running
- **Issue**: Only PaddleOCR runs; no consensus merge
- **Solution**: Set `OCR_VISION_API_KEY` in `.env` (same OpenRouter key is fine). Restart the server.
- **Check**: Startup log should show `pymupdf+paddleocr+gemma4` (or similar). Run `py -3.10 scripts\test_dual_ocr.py your-image.png`
- **Note**: If OpenRouter returns **429**, local PaddleOCR text is still used; Gemma is skipped for that request

### Chat uses wrong model
- **Issue**: Chat should use GLM, not Gemma
- **Solution**: Keep `OPENROUTER_MODEL=z-ai/glm-5.2:free` for chat. Use `OCR_VISION_MODEL=google/gemma-4-31b-it:free` only for vision OCR.

### Timeline empty after upload
- **Issue**: Documents uploaded but Timeline panel shows “No timeline events yet”
- **Causes**:
  - Server was not restarted after a timeline code update (old uploads may have 0 events stored)
  - OpenRouter **429 rate limit** on timeline LLM (regex/heuristics still run without the API)
- **Solutions**:
  1. Restart the server (`start.bat` or `py -3.10 -m uvicorn main:app`)
  2. Open the case → click **Timeline** — auto-sync runs if OCR text exists
  3. Check the upload message for `Timeline events found: N` (should be > 0 for dated documents)
  4. Check server logs for `[Timeline] Total N events for ...`
  5. Set `TIMELINE_API_KEY` in `.env` for LLM-assisted extraction (same key as OpenRouter is fine)

### FTS5 Syntax Error
- **Issue**: Chat fails with "fts5: syntax error near ..."
- **Status**: Fixed — queries with punctuation are now sanitized
- **If persists**: Check `database.py` line ~490 (`search_chunks_fts`)

### Vector Search Not Working
- **Issue**: Embeddings disabled or models not loaded
- **Why**: sentence-transformers requires significant installation
- **Current State**: Optional — system falls back to FTS5 if unavailable
- **To Enable**: `pip install sentence-transformers`

### Port 8000 Already in Use
- **Solution**: Change PORT in `config.py` or use:
  ```bash
  python -m uvicorn main:app --port 8080
  ```

## Database Schema

### Core Tables
- **cases** — Legal case metadata (name, number, status, dates)
- **documents** — Uploaded files (path, MIME type, upload date)
- **text_chunks** — Chunked text with metadata (for LLM context)
- **timeline_events** — Extracted dates and events
- **audit_logs** — User actions and access logs

### Full-Text Search (FTS5)
- **chunk_texts** — Virtual FTS5 table for keyword search
- **ocr_texts** — Virtual FTS5 table for raw OCR content

### Vector Search
- **chroma_db/** — Persistent ChromaDB vector embeddings

## Development Notes

### Adding a New Document Type
1. Update `ocr_service.py` with extraction logic
2. Add MIME type to allowed list in `main.py`
3. Test via `/upload` endpoint

### Customizing AI Behavior
- Edit system prompts in `llm_service.py` (lines ~30-50)
- Adjust token budget/context in `.env` (`MAX_CONTEXT_CHARS`)
- Chat model: `OPENROUTER_MODEL` in `.env`
- Vision OCR model: `OCR_VISION_MODEL` in `.env`
- Timeline model: `TIMELINE_MODEL` in `.env`

### Extending Timeline Extraction
- Date/event regex and keywords: `services/timeline_service.py` (`DATE_PATTERNS`, `EVENT_KEYWORDS`)
- Auto-sync logic: `main.py` (`GET /timeline/{case_id}`) and `services/case_service.py` (`sync_case_timeline`)
- Adjust `TIMELINE_EXTRACTION_PROMPT` for LLM-based extraction

## License

KanoonVault is released under the **[MIT License](LICENSE)** (SPDX: `MIT`).

You may use, copy, modify, merge, publish, distribute, sublicense, and sell copies of the software, subject to including the copyright notice and license text in distributions.

To use your own name in the copyright line, edit the `Copyright (c)` line in `LICENSE` before publishing.

### Third-party components

KanoonVault depends on (not exhaustive):

- **FastAPI**, **SQLite**, **ChromaDB**, **PyMuPDF**, **PaddleOCR**, **Tesseract**, **OpenRouter** — each under their own licenses; see upstream projects for terms.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and pull request guidelines.

Report security issues privately — see [SECURITY.md](SECURITY.md).

## Publish on GitHub

Use this checklist before making the repository public.

### 1. Verify nothing sensitive is tracked

```bash
git status
```

Confirm these are **not** staged or committed:

| Path | Why |
|------|-----|
| `.env` | API keys |
| `kanoonvault.db` | Case data |
| `uploads/` | Uploaded documents |
| `chroma_db/` | Embeddings |
| `.venv/` | Local virtualenv |

All are listed in [`.gitignore`](.gitignore).

### 2. Create `.env` locally (never commit)

```bash
copy .env.example .env   # Windows
cp .env.example .env     # macOS/Linux
```

Add your [OpenRouter](https://openrouter.ai) API key(s). See [Configuration](#configuration).

### 3. Initialize git and push

```bash
git init
git add .
git status   # double-check no .env or database files
git commit -m "Initial public release: KanoonVault Legal Memory OS"
```

Create an empty repository on GitHub. When prompted for a license, choose **MIT** (or skip — this repo already includes [`LICENSE`](LICENSE)), then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/KanoonVault.git
git branch -M main
git push -u origin main
```

### 4. GitHub Actions (optional)

Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

- Runs **offline** smoke tests on every push (no API keys required).
- If you add repository secrets, API key checks run too:
  - `OPENROUTER_API_KEY`
  - `TIMELINE_API_KEY` (optional if same as OpenRouter)
  - `OCR_VISION_API_KEY` (optional)

Settings → **Secrets and variables** → **Actions** → **New repository secret**

### 5. Recommended repository settings

- Add a short **Description** and topics: `legal-tech`, `ocr`, `paddleocr`, `fastapi`, `rag`, `sqlite`
- Enable **Issues** for bug reports
- Set default branch to `main`

---

**KanoonVault** · [MIT License](LICENSE) · Python 3.10 · May 2026
