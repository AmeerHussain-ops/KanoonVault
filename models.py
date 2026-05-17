"""
KanoonVault Pydantic Models
"""
from pydantic import BaseModel, Field
from typing import Optional


class CaseCreate(BaseModel):
    case_name: str
    notes: str = ""


class CaseUpdate(BaseModel):
    status: str  # active | closed | reopened
    date: str    # YYYY-MM-DD


class TimelineEventCreate(BaseModel):
    case_id: int
    event_date: Optional[str] = None   # YYYY-MM-DD or None
    event_desc: str
    source_file: Optional[str] = None


class ChatQuery(BaseModel):
    question: str
    case_id: Optional[int] = None      # None = global search
    stream: bool = True


class UploadRequest(BaseModel):
    case_id: int  # REQUIRED - must have active case workspace


class UploadResponse(BaseModel):
    document_id: int
    case_id: int
    case_name: str
    filename: str
    ocr_preview: str
    events_extracted: int
    # Note: is_new_case removed - files always belong to current case workspace


class CaseResponse(BaseModel):
    id: int
    case_name: str
    case_number: Optional[str]
    court_name: Optional[str]
    status: str
    case_opened_on: Optional[str]
    case_closed_on: Optional[str]
    doc_count: int
    created_at: str


class TimelineEvent(BaseModel):
    id: int
    case_id: int
    event_date: Optional[str]
    event_desc: str
    source_file: Optional[str]
    created_at: str
