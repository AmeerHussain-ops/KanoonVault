"""
KanoonVault Case Service
Handles case detection from OCR text, creation, and updates.
"""
import re
import os
from datetime import date, datetime
from pathlib import Path

import database as db
from services.timeline_service import detect_case_metadata, extract_timeline_events
from services.vector_memory_service import process_document_for_vector_memory


def detect_or_create_case(ocr_text: str, filename: str) -> tuple[int, bool]:
    """
    Given OCR text from an uploaded document:
    1. Try to match against existing cases by case number / FIR number.
    2. If no match, create a new case with a name inferred from the document.
    Returns (case_id, is_new_case).
    """
    meta = detect_case_metadata(ocr_text)
    existing_cases = db.list_cases()

    # Try to match by case number
    if meta.get("case_number"):
        for c in existing_cases:
            if c["case_number"] and meta["case_number"].lower() in c["case_number"].lower():
                return c["id"], False

    # Try to match by FIR number in case name
    if meta.get("fir_number"):
        for c in existing_cases:
            if meta["fir_number"] in (c["case_name"] or "") or \
               meta["fir_number"] in (c["case_number"] or ""):
                return c["id"], False

    # Create new case
    case_name = _infer_case_name(ocr_text, meta, filename)
    today = date.today().isoformat()

    case_id = db.create_case(
        case_name=case_name,
        case_number=meta.get("case_number"),
        court_name=meta.get("court_name"),
        notes=f"Auto-created from upload: {filename}",
        opened_on=today,
    )
    return case_id, True


def _infer_case_name(text: str, meta: dict, filename: str) -> str:
    """
    Build a human-readable case name from available metadata.
    Priority: extracted case name → FIR info → filename stem.
    """
    # Try "State vs X" or "X vs Y"
    m = re.search(
        r"((?:State|Government|Govt\.?|Republic)\s+(?:of\s+\w+\s+)?v(?:s\.?|ersus)\s+[\w\s]+(?:&|and)?\s*[\w\s]*)",
        text, re.IGNORECASE
    )
    if m:
        return m.group(1).strip()[:100]

    m = re.search(r"([\w\s]+)\s+v(?:s\.?|ersus)\s+([\w\s]+)", text, re.IGNORECASE)
    if m:
        return f"{m.group(1).strip()} vs {m.group(2).strip()}"[:100]

    if meta.get("fir_number"):
        court = meta.get("court_name", "")
        return f"FIR {meta['fir_number']}{' - ' + court if court else ''}"[:100]

    if meta.get("case_number"):
        return f"Case {meta['case_number']}"[:100]

    # Fallback: filename without extension
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").title()
    return f"{stem} Case"[:100]


def process_upload(
    ocr_text: str,
    filename: str,
    filepath: str,
    file_type: str,
    case_id: int,
) -> dict:
    """
    Full pipeline for CASE WORKSPACE MEMORY:
    - Assign uploaded file to current case (no auto-case creation)
    - store document
    - store OCR text
    - extract and store timeline events
    Returns summary dict.
    
    IMPORTANT: case_id MUST be the currently active case workspace.
    Files uploaded in a case inherit: case_id, timeline, vector memory, OCR, metadata.
    """
    case = db.get_case(case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")

    # Get file size if file exists
    file_size = None
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)

    doc_id = db.create_document(
        case_id=case_id,
        original_filename=filename,
        stored_file_path=filepath,
        mime_type=file_type,
        file_size=file_size,
    )

    db.store_ocr_text(case_id, doc_id, ocr_text)

    # Process document for vector memory (chunking + embeddings)
    process_document_for_vector_memory(case_id, doc_id, ocr_text, filename)

    events = extract_timeline_events(ocr_text, filename)
    for ev in events:
        db.add_timeline_event(
            case_id=case_id,
            event_date=ev.get("event_date"),
            event_desc=ev["event_desc"],
            source_file=ev["source_file"],
            document_id=doc_id,  # Link timeline event to uploaded document
            page_number=ev.get("page_number"),  # Page number if extracted
        )

    preview = ocr_text[:300].replace("\n", " ") + ("..." if len(ocr_text) > 300 else "")

    return {
        "document_id": doc_id,
        "case_id": case_id,
        "case_name": case["case_name"],
        "filename": filename,
        "ocr_preview": preview,
        "events_extracted": len(events),
    }


def sync_case_timeline(case_id: int) -> dict:
    """Build or refresh timeline from stored OCR (used after upload and when timeline is opened)."""
    case = db.get_case(case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")

    docs = db.list_case_documents_with_ocr(case_id)
    db.clear_timeline(case_id)
    total = 0

    for doc in docs:
        events = extract_timeline_events(doc["content"], doc["original_filename"])
        for ev in events:
            db.add_timeline_event(
                case_id=case_id,
                event_date=ev.get("event_date"),
                event_desc=ev["event_desc"],
                source_file=ev["source_file"],
                document_id=doc["document_id"],
                page_number=ev.get("page_number"),
            )
        total += len(events)

    return {
        "case_id": case_id,
        "documents_processed": len(docs),
        "events_extracted": total,
    }
