"""
KanoonVault Database Layer
SQLite with FTS5 for full-text search over OCR'd legal documents.
Storage and timeline design are inspired by MemoryOS and EverOS patterns.
Includes support for audit logs, case isolation, and structured legal memory.
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "kanoonvault.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate_soft_delete_audit(conn):
    """Add soft-delete columns, audit_logs; safe for existing DBs."""
    for stmt in (
        "ALTER TABLE cases ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE cases ADD COLUMN deleted_at TEXT",
        "ALTER TABLE cases ADD COLUMN deleted_by TEXT",
        "ALTER TABLE cases ADD COLUMN restored_at TEXT",
    ):
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass  # duplicate column


def row_is_deleted(row: dict) -> bool:
    v = row.get("is_deleted")
    return bool(v)


def _migrate_documents_schema(conn):
    """Upgrade legacy KanoonVault DBs that used filename/filepath/file_type."""
    colnames = [r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()]
    pairs = (
        ("filename", "original_filename"),
        ("filepath", "stored_file_path"),
        ("file_type", "mime_type"),
    )
    for old, new in pairs:
        colnames = [r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()]
        if old in colnames and new not in colnames:
            try:
                conn.execute(f"ALTER TABLE documents RENAME COLUMN {old} TO {new}")
            except sqlite3.OperationalError:
                pass
    colnames = [r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()]
    if "file_size" not in colnames:
        try:
            conn.execute("ALTER TABLE documents ADD COLUMN file_size INTEGER")
        except sqlite3.OperationalError:
            pass
    if "file_hash" not in colnames:
        try:
            conn.execute("ALTER TABLE documents ADD COLUMN file_hash TEXT")
        except sqlite3.OperationalError:
            pass


def _migrate_cases_schema(conn):
    """Add production-ready case metadata columns without rewriting existing tables."""
    colnames = [r[1] for r in conn.execute("PRAGMA table_info(cases)").fetchall()]
    if "fir_number" not in colnames:
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN fir_number TEXT")
        except sqlite3.OperationalError:
            pass
    if "updated_at" not in colnames:
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN updated_at TEXT")
        except sqlite3.OperationalError:
            pass


def _migrate_timeline_schema(conn):
    """Add timeline event metadata fields for improved retrieval."""
    colnames = [r[1] for r in conn.execute("PRAGMA table_info(timeline_events)").fetchall()]
    if "event_type" not in colnames:
        try:
            conn.execute("ALTER TABLE timeline_events ADD COLUMN event_type TEXT")
        except sqlite3.OperationalError:
            pass


def _ensure_production_tables(conn):
    """Create optional production-support tables without changing existing text chunk usage."""
    conn.execute("""
            CREATE TABLE IF NOT EXISTS ocr_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER REFERENCES cases(id),
                document_id INTEGER REFERENCES documents(id),
                chunk_text TEXT NOT NULL,
                chunk_hash TEXT,
                page_number INTEGER,
                section_type TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
    conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER,
                action TEXT,
                user_id TEXT,
                timestamp TEXT DEFAULT (datetime('now','localtime'))
            )
        """)


def init_db():
    """Create all tables on first run. Idempotent."""
    conn = get_conn()
    with conn:
        # --- Cases table ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                case_name       TEXT NOT NULL,
                case_number     TEXT,
                court_name      TEXT,
                status          TEXT DEFAULT 'active',
                case_opened_on  TEXT,
                case_closed_on  TEXT,
                case_reopened_on TEXT,
                notes           TEXT,
                created_at      TEXT DEFAULT (datetime('now','localtime')),
                is_deleted      INTEGER NOT NULL DEFAULT 0,
                deleted_at      TEXT,
                deleted_by      TEXT,
                restored_at     TEXT
            )
        """)
        _migrate_soft_delete_audit(conn)

        # --- Documents table ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id             INTEGER REFERENCES cases(id),
                original_filename   TEXT NOT NULL,
                stored_file_path    TEXT NOT NULL,
                mime_type           TEXT,
                file_size           INTEGER,
                uploaded_at         TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        _migrate_documents_schema(conn)
        _migrate_cases_schema(conn)
        _migrate_timeline_schema(conn)
        _ensure_production_tables(conn)

        # --- Timeline events table ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS timeline_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id     INTEGER REFERENCES cases(id),
                document_id INTEGER REFERENCES documents(id),
                event_date  TEXT,
                event_type  TEXT,
                event_desc  TEXT NOT NULL,
                source_file TEXT,
                page_number INTEGER,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        
        # Add missing columns if they don't exist (migration for existing databases)
        try:
            conn.execute("ALTER TABLE timeline_events ADD COLUMN document_id INTEGER")
        except:
            pass  # Column already exists
        try:
            conn.execute("ALTER TABLE timeline_events ADD COLUMN page_number INTEGER")
        except:
            pass  # Column already exists

        # --- OCR text FTS5 table ---
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS ocr_texts USING fts5(
                case_id UNINDEXED,
                document_id UNINDEXED,
                content,
                tokenize='porter unicode61'
            )
        """)

        # --- Text chunks table for vector search ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS text_chunks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id     INTEGER REFERENCES cases(id),
                document_id INTEGER REFERENCES documents(id),
                chunk_text  TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                page_number INTEGER,
                source_metadata TEXT,  -- JSON string with additional metadata
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)

        # --- FTS5 for chunks ---
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunk_texts USING fts5(
                chunk_id UNINDEXED,
                case_id UNINDEXED,
                document_id UNINDEXED,
                content,
                tokenize='porter unicode61'
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT,
                case_id     INTEGER,
                action      TEXT NOT NULL,
                timestamp   TEXT DEFAULT (datetime('now','localtime')),
                details     TEXT,
                ip_address  TEXT
            )
        """)

    conn.close()


# ── Case CRUD ─────────────────────────────────────────────────────────────────

def create_case(case_name: str, case_number: str = None, court_name: str = None,
                notes: str = "", opened_on: str = None) -> int:
    conn = get_conn()
    with conn:
        cur = conn.execute("""
            INSERT INTO cases (case_name, case_number, court_name, notes, case_opened_on)
            VALUES (?, ?, ?, ?, ?)
        """, (case_name, case_number, court_name, notes, opened_on))
        return cur.lastrowid


def _active_case_predicate(table_alias: str = "") -> str:
    """table_alias examples: '', 'c.' — must include trailing dot if used."""
    col = f"{table_alias}is_deleted" if table_alias else "is_deleted"
    return f"(COALESCE({col}, 0) = 0)"


def get_case_row(case_id: int) -> dict | None:
    """Return case row regardless of deleted flag."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    return dict(row) if row else None


def get_case(case_id: int) -> dict | None:
    """Active (non-soft-deleted) case only."""
    conn = get_conn()
    row = conn.execute(f"""
        SELECT * FROM cases
        WHERE id=? AND {_active_case_predicate()}
    """, (case_id,)).fetchone()
    return dict(row) if row else None


def list_cases() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT c.*, COUNT(d.id) as doc_count
        FROM cases c
        LEFT JOIN documents d ON d.case_id = c.id
        WHERE {_active_case_predicate('c.')}
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def list_trash_cases() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.*, COUNT(d.id) as doc_count
        FROM cases c
        LEFT JOIN documents d ON d.case_id = c.id
        WHERE COALESCE(c.is_deleted, 0) = 1
        GROUP BY c.id
        ORDER BY datetime(c.deleted_at) DESC, c.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def list_active_case_id_strings() -> set[str]:
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT id FROM cases WHERE {_active_case_predicate()}
    """).fetchall()
    return {str(r["id"]) for r in rows}


def soft_delete_case(case_id: int, deleted_by: str | None = None) -> bool:
    conn = get_conn()
    with conn:
        cur = conn.execute("""
            UPDATE cases SET
                is_deleted = 1,
                deleted_at = datetime('now','localtime'),
                deleted_by = ?,
                restored_at = NULL
            WHERE id = ? AND COALESCE(is_deleted, 0) = 0
        """, (deleted_by, case_id))
        return cur.rowcount == 1


def restore_case(case_id: int) -> bool:
    conn = get_conn()
    with conn:
        cur = conn.execute("""
            UPDATE cases SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL,
                restored_at = datetime('now','localtime')
            WHERE id = ? AND COALESCE(is_deleted, 0) = 1
        """, (case_id,))
        return cur.rowcount == 1


def update_case_status(case_id: int, status: str, date: str):
    conn = get_conn()
    col = {"closed": "case_closed_on", "reopened": "case_reopened_on"}.get(status)
    with conn:
        exists = conn.execute(f"""
            SELECT 1 FROM cases WHERE id=? AND {_active_case_predicate()}
        """, (case_id,)).fetchone()
        if not exists:
            return
        if col:
            conn.execute(f"UPDATE cases SET status=?, {col}=? WHERE id=?",
                         (status, date, case_id))
        else:
            conn.execute("UPDATE cases SET status=? WHERE id=?", (status, case_id))


def log_audit(
    action: str,
    case_id: int | None = None,
    user_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
):
    conn = get_conn()
    with conn:
        conn.execute("""
            INSERT INTO audit_logs (user_id, case_id, action, details, ip_address)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, case_id, action, details, ip_address))


def case_ids_soft_deleted_before(days: int) -> list[int]:
    """Candidates for automated permanent purge."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT id FROM cases
        WHERE COALESCE(is_deleted, 0) = 1
          AND deleted_at IS NOT NULL
          AND datetime(deleted_at) <= datetime('now', ?, 'localtime')
    """, (f'-{days} days',)).fetchall()
    return [r["id"] for r in rows]


# ── Document CRUD ──────────────────────────────────────────────────────────────

def create_document(case_id: int, original_filename: str, stored_file_path: str,
                  mime_type: str = None, file_size: int = None) -> int:
    conn = get_conn()
    with conn:
        cur = conn.execute("""
            INSERT INTO documents (case_id, original_filename, stored_file_path, mime_type, file_size)
            VALUES (?, ?, ?, ?, ?)
        """, (case_id, original_filename, stored_file_path, mime_type, file_size))
        return cur.lastrowid


def list_documents(case_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM documents WHERE case_id=? ORDER BY uploaded_at DESC",
        (case_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_document(document_id: int) -> dict | None:
    """Get document details by ID."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    return dict(row) if row else None


def get_document_path(document_id: int) -> str | None:
    """Get the stored file path for a document."""
    doc = get_document(document_id)
    return doc['stored_file_path'] if doc else None


# ── Timeline CRUD ──────────────────────────────────────────────────────────────

def add_timeline_event(case_id: int, event_date: str, event_desc: str,
                       source_file: str = None, document_id: int = None, page_number: int = None):
    """Store timeline event with full metadata including source document."""
    conn = get_conn()
    with conn:
        conn.execute("""
            INSERT INTO timeline_events (case_id, document_id, event_date, event_desc, source_file, page_number)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (case_id, document_id, event_date, event_desc, source_file, page_number))


def get_timeline(case_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM timeline_events
        WHERE case_id=?
        ORDER BY event_date ASC NULLS LAST, created_at ASC
    """, (case_id,)).fetchall()
    return [dict(r) for r in rows]


def clear_timeline(case_id: int):
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM timeline_events WHERE case_id = ?", (case_id,))


def list_case_documents_with_ocr(case_id: int) -> list[dict]:
    """Documents that have stored OCR text (for timeline rebuild)."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.id AS document_id, d.original_filename, o.content
        FROM documents d
        INNER JOIN ocr_texts o ON o.document_id = d.id
        WHERE d.case_id = ?
        ORDER BY d.uploaded_at ASC
    """, (case_id,)).fetchall()
    return [dict(r) for r in rows]


# ── OCR FTS ────────────────────────────────────────────────────────────────────

def store_ocr_text(case_id: int, document_id: int, content: str):
    conn = get_conn()
    with conn:
        conn.execute("""
            INSERT INTO ocr_texts (case_id, document_id, content)
            VALUES (?, ?, ?)
        """, (case_id, document_id, content))


def search_ocr(query: str, case_id: int = None) -> list[dict]:
    conn = get_conn()
    import re

    if not query:
        return []
    fts_query = re.sub(r"[^\w\s]", " ", query).strip()
    fts_query = re.sub(r"\s+", " ", fts_query)
    if not fts_query:
        return []

    if case_id:
        rows = conn.execute(f"""
            SELECT ocr_texts.* FROM ocr_texts
            JOIN cases c ON c.id = ocr_texts.case_id AND {_active_case_predicate('c.')}
            WHERE ocr_texts MATCH ? AND ocr_texts.case_id=?
            ORDER BY rank
            LIMIT 5
        """, (fts_query, case_id)).fetchall()
    else:
        rows = conn.execute(f"""
            SELECT ocr_texts.* FROM ocr_texts
            JOIN cases c ON c.id = ocr_texts.case_id AND {_active_case_predicate('c.')}
            WHERE ocr_texts MATCH ?
            ORDER BY rank
            LIMIT 5
        """, (fts_query,)).fetchall()
    return [dict(r) for r in rows]


def get_case_memory(case_id: int) -> str:
    """Build a full text blob of all OCR content for a case (for LLM context)."""
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT o.content, d.original_filename, d.uploaded_at
        FROM ocr_texts o
        JOIN documents d ON d.id = o.document_id
        JOIN cases c ON c.id = o.case_id AND {_active_case_predicate('c.')}
        WHERE o.case_id = ?
        ORDER BY d.uploaded_at ASC
    """, (case_id,)).fetchall()

    if not rows:
        return ""

    parts = []
    for r in rows:
        parts.append(f"[Document: {r['original_filename']} | Uploaded: {r['uploaded_at']}]\n{r['content']}")
    return "\n\n---\n\n".join(parts)


# ── Text Chunks CRUD ───────────────────────────────────────────────────────────

def create_text_chunk(case_id: int, document_id: int, chunk_text: str,
                      chunk_index: int, page_number: int = None,
                      source_metadata: str = None) -> int:
    """Store a text chunk in the database."""
    conn = get_conn()
    with conn:
        cur = conn.execute("""
            INSERT INTO text_chunks (case_id, document_id, chunk_text, chunk_index, page_number, source_metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (case_id, document_id, chunk_text, chunk_index, page_number, source_metadata))
        chunk_id = cur.lastrowid

        # Also store in FTS5 for full-text search
        conn.execute("""
            INSERT INTO chunk_texts (chunk_id, case_id, document_id, content)
            VALUES (?, ?, ?, ?)
        """, (chunk_id, case_id, document_id, chunk_text))

        return chunk_id


def get_chunks_for_case(case_id: int) -> list[dict]:
    """Get all chunks for a specific active case."""
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT tc.*, d.original_filename
        FROM text_chunks tc
        JOIN documents d ON d.id = tc.document_id
        JOIN cases cx ON cx.id = tc.case_id AND {_active_case_predicate('cx.')}
        WHERE tc.case_id = ?
        ORDER BY tc.chunk_index ASC
    """, (case_id,)).fetchall()
    return [dict(r) for r in rows]


def get_recent_chunks_for_case(case_id: int, limit: int = 10) -> list[dict]:
    """
    Direct fallback: load the most recent chunks for a case
    without requiring an FTS MATCH query. Used when FTS and vector
    search both return empty (e.g. vague queries like 'summarize this').
    """
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT tc.chunk_text, tc.page_number, tc.source_metadata,
               tc.case_id, tc.document_id,
               d.original_filename, d.stored_file_path, d.uploaded_at
        FROM text_chunks tc
        JOIN documents d ON d.id = tc.document_id
        JOIN cases cx ON cx.id = tc.case_id AND {_active_case_predicate('cx.')}
        WHERE tc.case_id = ?
        ORDER BY tc.created_at DESC, tc.chunk_index ASC
        LIMIT ?
    """, (case_id, limit)).fetchall()
    return [dict(r) for r in rows]


def search_chunks_fts(query: str, case_id: int = None, limit: int = 10) -> list[dict]:
    """Search chunks using FTS5 full-text search (active cases only)."""
    conn = get_conn()
    import re

    # Sanitize user query for FTS5 MATCH (remove punctuation that breaks FTS parser)
    if not query:
        return []
    fts_query = re.sub(r"[^\w\s]", " ", query).strip()
    # Collapse multiple spaces
    fts_query = re.sub(r"\s+", " ", fts_query)
    if not fts_query:
        return []

    # Execute using sanitized fts_query
    if case_id:
        rows = conn.execute(f"""
            SELECT chunk_texts.*, tc.chunk_text, tc.page_number, tc.source_metadata,
                   d.id as document_id, d.original_filename, d.stored_file_path,
                   d.uploaded_at, tc.case_id
            FROM chunk_texts
            JOIN text_chunks tc ON tc.id = chunk_texts.chunk_id
            JOIN documents d ON d.id = tc.document_id
            JOIN cases c ON c.id = tc.case_id AND {_active_case_predicate('c.')}
            WHERE chunk_texts MATCH ? AND chunk_texts.case_id = ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, case_id, limit)).fetchall()
    else:
        rows = conn.execute(f"""
            SELECT chunk_texts.*, tc.chunk_text, tc.page_number, tc.source_metadata,
                   d.id as document_id, d.original_filename, d.stored_file_path,
                   d.uploaded_at, tc.case_id
            FROM chunk_texts
            JOIN text_chunks tc ON tc.id = chunk_texts.chunk_id
            JOIN documents d ON d.id = tc.document_id
            JOIN cases c ON c.id = tc.case_id AND {_active_case_predicate('c.')}
            WHERE chunk_texts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, limit)).fetchall()

    return [dict(r) for r in rows]


def delete_chunks_for_document(document_id: int):
    """Delete all chunks for a specific document."""
    conn = get_conn()
    with conn:
        # Get chunk IDs first
        chunk_ids = conn.execute("SELECT id FROM text_chunks WHERE document_id = ?", (document_id,)).fetchall()
        chunk_ids = [r['id'] for r in chunk_ids]

        if chunk_ids:
            # Delete from FTS5
            placeholders = ','.join('?' * len(chunk_ids))
            conn.execute(f"DELETE FROM chunk_texts WHERE chunk_id IN ({placeholders})", chunk_ids)

            # Delete from main table
            conn.execute(f"DELETE FROM text_chunks WHERE document_id = ?", (document_id,))


def list_documents_with_meta(case_id: int) -> list[dict]:
    """
    All documents for a case with optional page_count from text_chunks (max page_number).
    """
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*,
               (SELECT MAX(tc.page_number) FROM text_chunks tc
                WHERE tc.document_id = d.id AND tc.page_number IS NOT NULL) AS page_count
        FROM documents d
        WHERE d.case_id = ?
        ORDER BY d.uploaded_at DESC
    """, (case_id,)).fetchall()
    return [dict(r) for r in rows]


def delete_case_cascade_sql(case_id: int) -> tuple[list[str], bool]:
    """
    Delete all DB rows scoped to case_id in one SQLite transaction.
    Returns (list of stored_file_path for disk cleanup, success).
    If the case does not exist, returns ([], False).
    """
    conn = get_conn()
    try:
        exists = conn.execute("SELECT 1 FROM cases WHERE id = ?", (case_id,)).fetchone()
        if not exists:
            return [], False

        path_rows = conn.execute(
            "SELECT stored_file_path FROM documents WHERE case_id = ?",
            (case_id,),
        ).fetchall()
        paths = [r["stored_file_path"] for r in path_rows]

        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM chunk_texts WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM text_chunks WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM ocr_texts WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM timeline_events WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM documents WHERE case_id = ?", (case_id,))
        cur = conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        if cur.rowcount != 1:
            conn.rollback()
            return [], False
        conn.commit()
        return paths, True
    except Exception:
        conn.rollback()
        raise
