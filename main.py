"""
KanoonVault – FastAPI Backend
The brain connecting OCR, Case Memory, Timeline and LLM chat.
"""
import os
import shutil
import asyncio
import json
import mimetypes
from pathlib import Path
from datetime import datetime, date

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

import database as db
from models import CaseCreate, CaseUpdate, TimelineEventCreate, ChatQuery, UploadRequest
from services.ocr_service import extract_text, get_file_type, get_ocr_engine
from services.case_service import process_upload, sync_case_timeline
from services.llm_service import stream_response, format_source_references

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="KanoonVault", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

FRONTEND_DIR = Path(__file__).parent / "frontend"

MAX_TEXT_PREVIEW_BYTES = 512 * 1024

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "tiff", "webp"}

TRASH_RETENTION_DAYS = int(os.getenv("TRASH_AUTO_PURGE_AFTER_DAYS", "30"))

PURGE_INTERVAL_SEC = int(os.getenv("TRASH_PURGE_INTERVAL_SEC", "86400"))


def _client_ip(request: Request | None) -> str | None:
    if not request or not request.client:
        return None
    return request.client.host


def _audit(
    request: Request | None,
    action: str,
    case_id: int | None = None,
    details: str | None = None,
    user_id: str | None = None,
):
    db.log_audit(
        action,
        case_id=case_id,
        user_id=user_id,
        details=details,
        ip_address=_client_ip(request),
    )


def _case_row(case_id: int):
    """Return case row if it exists."""
    row = db.get_case_row(case_id)
    if not row:
        raise HTTPException(404, "Case not found")
    return row


def _resolve_case(case_id: int, allow_trash: bool) -> dict:
    """
    require active case unless allow_trash (explicit Trash / recovery views).
    """
    row = _case_row(case_id)
    deleted = db.row_is_deleted(row)
    if allow_trash:
        if not deleted:
            raise HTTPException(400, "Trash access applies only to cases in Trash.")
        return row
    if deleted:
        raise HTTPException(404, "Case not found")
    return row


def _require_document_in_case(
    document_id: int,
    case_id: int,
    *,
    allow_trash: bool,
) -> dict:
    doc = db.get_document(document_id)
    if not doc or doc["case_id"] != case_id:
        raise HTTPException(404, "Document not found")
    _resolve_case(case_id, allow_trash)
    return doc


async def _trash_auto_purge_loop():
    """Permanently remove soft-deleted cases past retention."""
    await asyncio.sleep(120)
    while True:
        try:
            stale = db.case_ids_soft_deleted_before(TRASH_RETENTION_DAYS)
            for cid in stale:
                try:
                    purge_case_physical_scheduled(cid)
                except Exception as ex:
                    print(f"[purge] Failed case_id={cid}: {ex}")
        except Exception as ex:
            print(f"[purge] Loop error: {ex}")
        await asyncio.sleep(max(PURGE_INTERVAL_SEC, 3600))


def _purge_case_physical(case_id: int) -> tuple[bool, int, list[str]]:
    """
    Vector + SQLite cascade + unlink files (no HTTP semantics).
    Returns (ok, document_count_removed, skipped_paths_remaining).
    """
    if not db.get_case_row(case_id):
        return False, 0, []

    conn = db.get_conn()
    try:
        rc = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE case_id=?",
            (case_id,),
        ).fetchone()
        n_docs = int(rc[0] if rc else 0)
    finally:
        conn.close()

    from services.vector_memory_service import delete_vector_embeddings_for_case

    delete_vector_embeddings_for_case(case_id)

    paths, ok = db.delete_case_cascade_sql(case_id)
    if not ok:
        return False, n_docs, paths

    for p in paths:
        try:
            fp = Path(p)
            if fp.is_file():
                fp.unlink()
        except OSError:
            pass

    return True, n_docs, paths


def _run_permanent_delete(
    case_id: int,
    *,
    request: Request | None,
    audit_action: str,
    automated: bool = False,
):
    """Permanent delete exposed to HTTP; raises HTTPException."""
    conn = db.get_conn()
    try:
        existed = conn.execute("SELECT id FROM cases WHERE id=?", (case_id,)).fetchone()
    finally:
        conn.close()
    if not existed:
        raise HTTPException(404, "Case not found")

    try:
        ok, n_docs, paths = _purge_case_physical(case_id)
    except Exception as e:
        raise HTTPException(503, detail=f"Permanent deletion failed: {e}") from e

    if not ok:
        raise HTTPException(404, "Case not found")

    detail = {
        "document_count_removed": int(n_docs or 0),
        "automated": automated,
    }
    _audit(request, audit_action, case_id=case_id, details=json.dumps(detail))


def purge_case_physical_scheduled(case_id: int) -> None:
    """Background retention purge — logs only on success."""
    ok, n_docs, _paths = _purge_case_physical(case_id)
    if not ok:
        raise RuntimeError(f"purge_case_physical_scheduled failed for case_id={case_id}")
    detail = {"document_count_removed": int(n_docs or 0), "automated": True}
    _audit(None, "case_deleted_permanent", case_id=case_id, details=json.dumps(detail))


def _soft_delete(case_id: int, request: Request | None, deleted_by: str | None):
    """Move case to Trash (recoverable)."""
    row = _case_row(case_id)
    if db.row_is_deleted(row):
        raise HTTPException(409, "Case is already in Trash.")
    ok = db.soft_delete_case(case_id, deleted_by=deleted_by)
    if not ok:
        raise HTTPException(404, "Case not found")
    _audit(
        request,
        "case_moved_to_trash",
        case_id=case_id,
        details=json.dumps({"deleted_by": deleted_by}),
    )


@app.on_event("startup")
async def startup():
    db.init_db()
    print(f"[KanoonVault] Primary OCR engine: {get_ocr_engine()}")
    asyncio.create_task(_trash_auto_purge_loop())


# ── Static frontend ────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# ── SETUP / CONFIGURATION ──────────────────────────────────────────────────────
@app.get("/api/setup/status")
def setup_status():
    """Check if initial setup is complete (API key configured)."""
    try:
        from credentials import is_api_key_configured
        has_openrouter = is_api_key_configured("OPENROUTER")
        
        return {
            "setup_complete": has_openrouter,
            "has_openrouter_key": has_openrouter,
            "message": "Setup complete" if has_openrouter else "No API key configured"
        }
    except Exception as e:
        print(f"[Setup] Error checking status: {e}")
        return {
            "setup_complete": False,
            "has_openrouter_key": False,
            "error": str(e)
        }


@app.post("/api/setup/test-api-key")
async def test_api_key_endpoint(api_key: str):
    """
    Test an OpenRouter API key without saving it.
    
    Query parameter:
        api_key: The API key to test
        
    Returns detailed status about whether the key is valid.
    """
    if not api_key or not api_key.strip():
        return {
            "valid": False,
            "status": "empty",
            "message": "❌ API key cannot be empty"
        }
    
    try:
        from services.api_key_service import test_api_key_async
        result = await test_api_key_async(api_key.strip())
        
        return {
            "valid": result.valid,
            "status": result.status,
            "message": result.message,
            "details": result.details
        }
    except Exception as e:
        print(f"[Setup] Error testing API key: {e}")
        return {
            "valid": False,
            "status": "test_error",
            "message": f"❌ Test failed: {str(e)[:100]}",
            "details": {"error": str(e)}
        }


@app.post("/api/setup/save-api-key")
def save_api_key(api_key: str, key_type: str = "OPENROUTER"):
    """
    Save a validated API key to secure storage.
    
    Query parameters:
        api_key: The API key to save
        key_type: Type of key (OPENROUTER, OCR_VISION, TIMELINE)
        
    Note: Call /api/setup/test-api-key first to validate.
    """
    if not api_key or not api_key.strip():
        raise HTTPException(400, "API key cannot be empty")
    
    try:
        from credentials import save_api_key as save_key_func
        success = save_key_func(key_type, api_key.strip())
        
        if success:
            return {
                "ok": True,
                "message": f"API key saved successfully",
                "key_type": key_type
            }
        else:
            return {
                "ok": False,
                "message": "Failed to save API key",
                "key_type": key_type
            }
    except Exception as e:
        print(f"[Setup] Error saving API key: {e}")
        raise HTTPException(500, f"Failed to save API key: {e}")


# ── STORAGE CONFIGURATION ──────────────────────────────────────────────────────
@app.get("/api/setup/storage-location")
def get_storage_location():
    """Get the current or default storage location."""
    try:
        from storage_manager import get_current_storage_dir, get_default_storage_dir, is_first_run_complete
        
        current_dir = get_current_storage_dir()
        first_run_complete = is_first_run_complete()
        
        return {
            "default_storage_dir": str(current_dir),
            "first_run_complete": first_run_complete
        }
    except Exception as e:
        print(f"[Setup] Error getting storage location: {e}")
        return {
            "default_storage_dir": str(Path.home() / "AppData" / "Local" / "KanoonVault"),
            "first_run_complete": False,
            "error": str(e)
        }


@app.get("/api/setup/storage-info")
def get_storage_info(path: str):
    """Get information about a storage path."""
    try:
        from storage_manager import get_storage_info, get_available_disk_space, validate_storage_path
        
        storage_path = Path(path)
        
        # Validate path
        validation = validate_storage_path(storage_path)
        
        info = {
            "path": str(storage_path),
            "valid": validation["valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "disk_space": get_available_disk_space(storage_path),
            "existing_data": None
        }
        
        # Check if there's existing data
        if storage_path.exists():
            storage_detail = get_storage_info(storage_path)
            info["existing_data"] = {
                "size_mb": storage_detail["total_size_mb"],
                "file_count": storage_detail["file_counts"]["total"]
            }
        
        return info
    except Exception as e:
        print(f"[Setup] Error getting storage info: {e}")
        raise HTTPException(500, f"Failed to get storage info: {e}")


@app.post("/api/setup/browse-storage-location")
def browse_storage_location():
    """Open a folder selection dialog and return the selected path."""
    try:
        from folder_dialog import select_folder
        from storage_manager import get_current_storage_dir
        
        # Get current location to use as initial directory
        current_dir = get_current_storage_dir()
        
        # Open folder dialog
        selected = select_folder(
            title="Choose KanoonVault Storage Folder",
            initial_dir=str(current_dir)
        )
        
        if selected:
            return {
                "selected_path": selected,
                "cancelled": False
            }
        else:
            return {
                "selected_path": None,
                "cancelled": True
            }
    except Exception as e:
        print(f"[Setup] Error opening folder dialog: {e}")
        return {
            "selected_path": None,
            "cancelled": False,
            "error": f"Failed to open folder dialog: {e}"
        }


@app.post("/api/setup/confirm-storage-location")
def confirm_storage_location(body: dict):
    """
    Confirm and save the storage location.
    Handles data migration if location changes.
    """
    try:
        from storage_manager import (
            get_current_storage_dir,
            initialize_storage_directory,
            migrate_data,
            save_storage_config,
            validate_storage_path
        )
        
        new_dir_str = body.get("storage_dir")
        if not new_dir_str:
            raise HTTPException(400, "storage_dir is required")
        
        new_dir = Path(new_dir_str)
        
        # Validate the new path
        validation = validate_storage_path(new_dir)
        if not validation["valid"]:
            raise HTTPException(400, f"Invalid storage path: {', '.join(validation['errors'])}")
        
        # Initialize new directory
        if not initialize_storage_directory(new_dir):
            raise HTTPException(500, "Failed to initialize storage directory")
        
        # Get current storage directory
        current_dir = get_current_storage_dir()
        
        # Migrate data if path changed
        migration_info = {"skipped": True}
        if current_dir.resolve() != new_dir.resolve():
            print(f"[Setup] Migrating data from {current_dir} to {new_dir}")
            migration_info = migrate_data(current_dir, new_dir)
            
            if not migration_info.get("success"):
                raise HTTPException(500, f"Migration failed: {', '.join(migration_info.get('messages', []))}")
        
        # Save configuration
        if not save_storage_config(new_dir, first_run_complete=False):
            raise HTTPException(500, "Failed to save storage configuration")
        
        return {
            "ok": True,
            "message": "Storage location configured",
            "storage_dir": str(new_dir),
            "migration": migration_info
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Setup] Error confirming storage location: {e}")
        raise HTTPException(500, f"Failed to confirm storage location: {e}")


@app.post("/api/setup/mark-first-run-complete")
def mark_first_run_complete():
    """Mark the first-run setup as complete."""
    try:
        from storage_manager import get_current_storage_dir, save_storage_config
        
        current_dir = get_current_storage_dir()
        
        if not save_storage_config(current_dir, first_run_complete=True):
            raise HTTPException(500, "Failed to save configuration")
        
        return {
            "ok": True,
            "message": "First-run setup marked as complete"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Setup] Error marking first-run complete: {e}")
        raise HTTPException(500, f"Failed to mark first-run complete: {e}")


# ── UPLOAD ─────────────────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...), case_id: int = None):
    """
    CASE WORKSPACE MEMORY RULE:
    Upload must belong to currently active case workspace.
    No new cases are created during upload.
    """
    # Check if case workspace is open
    if case_id is None:
        raise HTTPException(400, "Please open or create a case before uploading documents.")
    
    # Verify case exists
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    
    file_type = get_file_type(file.filename)
    allowed = {"pdf", "jpg", "jpeg", "png", "bmp", "tiff", "webp", "txt"}
    if file_type not in allowed:
        raise HTTPException(400, f"Unsupported file type: .{file_type}")

    # Save file
    dest = UPLOAD_DIR / file.filename
    # Avoid name collision
    if dest.exists():
        stem = Path(file.filename).stem
        ext = Path(file.filename).suffix
        dest = UPLOAD_DIR / f"{stem}_{int(datetime.now().timestamp())}{ext}"

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # OCR
    try:
        ocr_text, chunks = extract_text(str(dest), file_type)
    except Exception as e:
        raise HTTPException(500, f"OCR failed: {e}")

    if not ocr_text.strip():
        ocr_text = "[No text could be extracted from this document]"

    # Case pipeline - FILES INHERIT CASE_ID FROM ACTIVE WORKSPACE
    try:
        result = process_upload(
            ocr_text=ocr_text,
            filename=dest.name,
            filepath=str(dest),
            file_type=file_type,
            case_id=case_id,  # REQUIRED - from currently active case workspace
        )
    except Exception as e:
        raise HTTPException(500, f"Upload processing failed: {e}")

    _audit(
        request,
        "document_uploaded",
        case_id=case_id,
        details=json.dumps(
            {
                "document_id": result.get("document_id"),
                "filename": result.get("filename"),
            }
        ),
    )

    return JSONResponse(result)


# ── OCR standalone ─────────────────────────────────────────────────────────────
@app.post("/ocr/process")
async def ocr_process(file: UploadFile = File(...)):
    """Extract raw OCR text from a file without creating a case."""
    file_type = get_file_type(file.filename)
    dest = UPLOAD_DIR / f"__ocr_temp_{file.filename}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        text, chunks = extract_text(str(dest), file_type)
    finally:
        dest.unlink(missing_ok=True)
    return {"text": text, "chunks": chunks, "chunk_count": len(chunks)}


# ── CASES ──────────────────────────────────────────────────────────────────────
@app.get("/cases")
def list_cases():
    return db.list_cases()


@app.post("/case/create")
def case_create(request: Request, body: CaseCreate):
    today = date.today().isoformat()
    cid = db.create_case(
        case_name=body.case_name,
        notes=body.notes,
        opened_on=today,
    )
    _audit(
        request,
        "case_created",
        case_id=cid,
        details=json.dumps({"case_name": body.case_name}),
    )
    return {"case_id": cid, "case_name": body.case_name}


@app.post("/case/update/{case_id}")
def case_update(request: Request, case_id: int, body: CaseUpdate):
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    db.update_case_status(case_id, body.status, body.date)
    _audit(
        request,
        "case_status_changed",
        case_id=case_id,
        details=json.dumps({"status": body.status, "date": body.date}),
    )
    return {"ok": True}


@app.get("/cases/trash")
def list_trash():
    """Soft-deleted cases (Trash)."""
    return db.list_trash_cases()


@app.get("/case/{case_id}")
def case_detail(case_id: int, allow_trash: bool = Query(False)):
    case = _resolve_case(case_id, allow_trash)
    docs = db.list_documents(case_id)
    timeline = db.get_timeline(case_id)
    return {**case, "documents": docs, "timeline": timeline}


@app.delete("/cases/{case_id}")
def delete_case_to_trash(
    case_id: int,
    request: Request,
    deleted_by: str | None = Query(None, description="Optional actor label"),
):
    """Move case to Trash (soft delete — recoverable)."""
    _soft_delete(case_id, request, deleted_by)
    return {"ok": True, "message": "Case moved to Trash."}


@app.post("/cases/{case_id}/restore")
def restore_deleted_case(case_id: int, request: Request):
    row = _case_row(case_id)
    if not db.row_is_deleted(row):
        raise HTTPException(409, "Case is not in Trash.")
    ok = db.restore_case(case_id)
    if not ok:
        raise HTTPException(404, "Case not found")
    _audit(request, "case_restored", case_id=case_id)
    return {"ok": True, "message": "Case restored successfully."}


@app.delete("/cases/{case_id}/permanent")
def delete_case_permanent(case_id: int, request: Request):
    """Irreversible delete (from Trash or dev tools)."""
    _run_permanent_delete(case_id, request=request, audit_action="case_deleted_permanent")
    return {"ok": True, "message": "Case permanently deleted."}


@app.get("/cases/{case_id}/documents")
def list_case_documents(
    case_id: int,
    allow_trash: bool = Query(False, description="Allow listing for trashed cases (Trash UI)"),
):
    """All uploaded files for a case with metadata (scoped by case_id)."""
    _resolve_case(case_id, allow_trash)
    rows = db.list_documents_with_meta(case_id)
    documents = []
    for d in rows:
        fname = d["original_filename"]
        ext = Path(fname).suffix.lower().lstrip(".") or (d.get("mime_type") or "")
        documents.append({
            "document_id": d["id"],
            "case_id": d["case_id"],
            "filename": fname,
            "uploaded_at": d["uploaded_at"],
            "file_type": ext or "unknown",
            "file_size": d["file_size"],
            "page_count": d["page_count"],
            "mime_type": d.get("mime_type"),
        })
    return {"case_id": case_id, "documents": documents}


# ── TIMELINE ───────────────────────────────────────────────────────────────────
@app.get("/timeline/{case_id}")
def get_timeline(case_id: int, allow_trash: bool = Query(False)):
    case = _resolve_case(case_id, allow_trash)
    events = db.get_timeline(case_id)
    if not events and db.list_case_documents_with_ocr(case_id):
        try:
            sync_case_timeline(case_id)
            events = db.get_timeline(case_id)
        except Exception as e:
            print(f"[Timeline] Auto-sync failed for case {case_id}: {e}")
    return {"case_id": case_id, "case_name": case["case_name"], "events": events}


@app.post("/timeline/event")
def add_event(request: Request, body: TimelineEventCreate):
    case = db.get_case(body.case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    db.add_timeline_event(
        case_id=body.case_id,
        event_date=body.event_date,
        event_desc=body.event_desc,
        source_file=body.source_file,
    )
    _audit(
        request,
        "timeline_modified",
        case_id=body.case_id,
        details=json.dumps(
            {
                "event_date": body.event_date,
                "preview": (body.event_desc or "")[:200],
            }
        ),
    )
    return {"ok": True}


# ── DOCUMENTS ─────────────────────────────────────────────────────────────────
@app.get("/documents/{document_id}/open")
def open_document(
    request: Request,
    document_id: int,
    case_id: int = Query(..., description="Case workspace (must own document)"),
    allow_trash: bool = Query(False, description="Allow access for trashed cases (Trash view)"),
):
    """Serve the original file; isolated by case_id."""
    doc = _require_document_in_case(document_id, case_id, allow_trash=allow_trash)
    _audit(
        request,
        "source_file_opened",
        case_id=case_id,
        details=json.dumps(
            {"document_id": document_id, "filename": doc.get("original_filename")}
        ),
    )
    file_path = Path(doc["stored_file_path"])
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk")

    guessed, _ = mimetypes.guess_type(doc["original_filename"])
    media = guessed
    if not media:
        ext_hint = (doc.get("mime_type") or Path(doc["original_filename"]).suffix).lower().lstrip(".")
        media = mimetypes.types_map.get(f".{ext_hint}") or "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        filename=doc["original_filename"],
        media_type=media,
    )


@app.get("/documents/{document_id}/preview")
def preview_document(
    document_id: int,
    case_id: int = Query(..., description="Case workspace (must own document)"),
    allow_trash: bool = Query(False),
):
    """Preview-friendly response: inline PDF/images, JSON text for .txt, or unsupported marker."""
    doc = _require_document_in_case(document_id, case_id, allow_trash=allow_trash)
    file_path = Path(doc["stored_file_path"])
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk")

    ext = file_path.suffix.lower().lstrip(".")
    fname = doc["original_filename"].lower()

    if ext == "pdf" or fname.endswith(".pdf"):
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=doc["original_filename"],
            content_disposition_type="inline",
        )

    if ext in IMAGE_EXTENSIONS:
        guessed, _ = mimetypes.guess_type(doc["original_filename"])
        mt = guessed or (
            "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        )
        return FileResponse(
            path=str(file_path),
            media_type=mt,
            filename=doc["original_filename"],
            content_disposition_type="inline",
        )

    if ext == "txt" or fname.endswith(".txt"):
        raw = file_path.read_bytes()[:MAX_TEXT_PREVIEW_BYTES]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        truncated = file_path.stat().st_size > len(raw)
        return JSONResponse(
            {"preview_type": "text", "text": text, "truncated": truncated},
        )

    return JSONResponse(
        status_code=415,
        content={
            "preview_type": "unsupported",
            "message": "Preview not available for this file type. Use Open to download the original.",
            "filename": doc["original_filename"],
        },
    )
@app.post("/chat/query")
async def chat_query(body: ChatQuery):
    """Stream LLM response grounded in relevant case chunks via SSE."""
    if body.case_id is not None and db.get_case(body.case_id) is None:
        raise HTTPException(404, "Case not found or in Trash")
    tokens = []
    source_metadata = None
    
    async def event_generator():
        nonlocal source_metadata
        try:
            async for token, metadata in stream_response(body.question, body.case_id):
                tokens.append(token)
                if metadata and source_metadata is None:
                    source_metadata = metadata
                # SSE format: data: <token>\n\n
                yield f"data: {token}\n\n"
        except Exception as e:
            yield f"data: [ERROR: {e}]\n\n"
        
        # After streaming is complete, send sources or special command result
        if source_metadata:
            if isinstance(source_metadata, dict) and source_metadata.get("special_command"):
                # Special command - return the file link directly
                yield f"data: {source_metadata['file_link']}\n\n"
            else:
                # Normal response - format with sources
                sources_text = format_source_references(source_metadata)
                yield f"data: \nSources:\n{sources_text}\n\n"
        
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )