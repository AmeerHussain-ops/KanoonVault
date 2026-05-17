"""
KanoonVault Vector Memory Service
Handles text chunking and hybrid search using FTS + ChromaDB.
Inspiration: simplified LlamaIndex semantics with a SQL control layer.
Hybrid ranking and chunk prioritization draw from RAG and Ragent design.
Note: ChromaDB/vector search disabled until sentence-transformers is properly installed.
"""
import os
import json
import chromadb
from typing import List, Dict, Any, Tuple

import database as db

# Initialize ChromaDB client (but won't use it until embeddings work)
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# Collection name for legal chunks
COLLECTION_NAME = "legal_chunks"

# Flag to enable/disable vector search
VECTOR_SEARCH_ENABLED = False
embedder = None

# Model for sentence embeddings (used when sentence-transformers is available)
MODEL_NAME = "all-MiniLM-L6-v2"

def _initialize_embedder():
    """Lazy initialization of the sentence transformer model."""
    global embedder, VECTOR_SEARCH_ENABLED
    if embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer(MODEL_NAME)
            VECTOR_SEARCH_ENABLED = True
            print("Vector search enabled with sentence-transformers")
        except Exception as e:
            print(f"Vector search disabled - failed to load sentence-transformers: {e}")
            VECTOR_SEARCH_ENABLED = False
            embedder = None


def get_or_create_collection():
    """Get or create the ChromaDB collection for legal chunks."""
    try:
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    except:
        collection = chroma_client.create_collection(name=COLLECTION_NAME)
    return collection


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for better retrieval.
    """
    if not text or len(text.strip()) == 0:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If we're not at the end, try to break at a sentence or word boundary
        if end < len(text):
            # Look for sentence endings within the last 100 characters
            sentence_endings = ['. ', '! ', '? ', '\n\n']
            best_break = end
            for ending in sentence_endings:
                last_ending = text.rfind(ending, start, end + 100)
                if last_ending != -1 and last_ending > best_break - 200:
                    best_break = last_ending + len(ending)
                    break

            # If no good sentence break, try word boundary
            if best_break == end:
                space_pos = text.rfind(' ', start, end + 50)
                if space_pos != -1:
                    best_break = space_pos + 1

            end = best_break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position with overlap
        start = max(start + 1, end - overlap)

    return chunks


def create_embeddings(chunks: List[str]) -> List[List[float]]:
    """Create embeddings for text chunks."""
    if not VECTOR_SEARCH_ENABLED:
        _initialize_embedder()

    if not VECTOR_SEARCH_ENABLED or embedder is None:
        # Return dummy embeddings if vector search is disabled
        return [[0.0] * 384 for _ in chunks]  # 384 is typical embedding dimension
    result = embedder.encode(chunks)
    return result.tolist() if hasattr(result, 'tolist') else list(result)


def store_chunks_in_vector_db(case_id: int, document_id: int, chunks: List[str],
                             embeddings: List[List[float]], metadata_list: List[Dict[str, Any]]):
    """
    Store chunks and their embeddings in ChromaDB.
    """
    collection = get_or_create_collection()

    # Create IDs for the chunks
    chunk_ids = [f"case_{case_id}_doc_{document_id}_chunk_{i}" for i in range(len(chunks))]

    # Prepare metadata
    metadatas = []
    for i, metadata in enumerate(metadata_list):
        meta = {
            "case_id": str(case_id),
            "document_id": str(document_id),
            "chunk_index": str(i),
            **metadata
        }
        metadatas.append(meta)

    # Store in ChromaDB
    collection.add(
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
        ids=chunk_ids
    )


def process_document_for_vector_memory(case_id: int, document_id: int, ocr_text: str,
                                      filename: str = None, page_number: int = None):
    """
    Process OCR text: chunk it, create embeddings, store in both SQLite and ChromaDB.
    """
    if not ocr_text or len(ocr_text.strip()) == 0:
        return

    # Get document details for comprehensive metadata
    doc_details = db.get_document(document_id)

    # Chunk the text
    chunks = chunk_text(ocr_text)

    if not chunks:
        return

    # Create embeddings
    embeddings = create_embeddings(chunks)

    # Store chunks in SQLite and prepare metadata
    metadata_list = []
    for i, chunk in enumerate(chunks):
        # Store in SQLite with comprehensive metadata
        source_metadata = json.dumps({
            "document_id": document_id,
            "original_file_name": doc_details['original_filename'] if doc_details else filename,
            "original_file_path": doc_details['stored_file_path'] if doc_details else None,
            "page_number": page_number,
            "chunk_text": chunk[:200] + "..." if len(chunk) > 200 else chunk,  # Preview
            "case_id": case_id,
            "upload_date": doc_details['uploaded_at'] if doc_details else None,
            "chunk_length": len(chunk),
            "chunk_index": i
        })

        db.create_text_chunk(
            case_id=case_id,
            document_id=document_id,
            chunk_text=chunk,
            chunk_index=i,
            page_number=page_number,
            source_metadata=source_metadata
        )

        # Prepare metadata for ChromaDB
        metadata_list.append({
            "document_id": str(document_id),
            "original_file_name": doc_details['original_filename'] if doc_details else filename or "unknown",
            "original_file_path": doc_details['stored_file_path'] if doc_details else None,
            "page_number": str(page_number) if page_number else "unknown",
            "case_id": str(case_id),
            "upload_date": doc_details['uploaded_at'] if doc_details else None,
            "chunk_length": str(len(chunk)),
            "chunk_index": str(i)
        })

    # Store in ChromaDB
    store_chunks_in_vector_db(case_id, document_id, chunks, embeddings, metadata_list)


def search_vector_db(query: str, case_id: int = None, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search ChromaDB for similar chunks using vector similarity.
    """
    if not VECTOR_SEARCH_ENABLED:
        _initialize_embedder()

    if not VECTOR_SEARCH_ENABLED or embedder is None:
        # Return empty results if vector search is disabled
        return []

    collection = get_or_create_collection()

    # Create embedding for the query
    query_result = embedder.encode([query])
    query_embedding = query_result.tolist()[0] if hasattr(query_result, 'tolist') else list(query_result[0])

    # Prepare where clause for filtering by case_id if provided
    where_clause = {"case_id": str(case_id)} if case_id else None

    # Search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_clause,
        include=['documents', 'metadatas', 'distances']
    )

    # Format results
    formatted_results = []
    if results['documents'] and len(results['documents'][0]) > 0:
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            formatted_results.append({
                "chunk_text": doc,
                "metadata": metadata,
                "similarity_score": 1 - distance,  # Convert distance to similarity
                "source": "vector_search"
            })

    return formatted_results


def _normalize_chunk_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _keyword_score(result: Dict) -> float:
    if result.get("source") == "fts_search":
        try:
            rank = float(result.get("rank", 5))
            return max(0.0, 1.0 / (rank + 1.0))
        except Exception:
            return 0.1
    return 0.0


def _metadata_boost(result: Dict, query: str) -> float:
    boost = 0.0
    metadata = result.get("metadata") or {}
    case_id = str(metadata.get("case_id") or result.get("case_id") or "").strip()
    if case_id:
        boost += 0.30

    query_lower = query.lower().strip() if query else ""
    for key in ("fir_number", "court_name", "case_number", "original_file_name"):
        value = str(metadata.get(key, "") or "").lower().strip()
        if value and (value in query_lower or query_lower in value):
            boost += 0.20
            break

    # Small boost for timeline and source-rich chunks
    if result.get("source") == "direct_fallback":
        boost += 0.05
    return min(boost, 0.5)


def _recency_boost(result: Dict) -> float:
    from datetime import datetime

    date_value = result.get("uploaded_at") or result.get("created_at")
    if not date_value:
        return 0.0

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_value[:19], fmt)
            age_days = (datetime.now() - dt).days
            if age_days <= 30:
                return 0.10
            if age_days <= 90:
                return 0.05
            return 0.0
        except Exception:
            continue
    return 0.0


def _length_penalty(result: Dict) -> float:
    text = str(result.get("chunk_text") or "").strip()
    return -0.15 if len(text) < 50 else 0.0


def merge_search_results(fts_results: List[Dict], vector_results: List[Dict],
                        max_results: int = 10, query: str = "") -> List[Dict]:
    """
    Merge and deduplicate results from FTS and vector search.
    Prioritize hybrid relevance scores over raw ordering.
    """
    all_results = fts_results + vector_results

    # Combine and deduplicate chunks by normalized text.
    seen_chunks = set()
    unique_results = []
    for result in all_results:
        chunk_text = str(result.get("chunk_text", ""))
        chunk_key = _normalize_chunk_text(chunk_text)[:500]
        if not chunk_key or chunk_key in seen_chunks:
            continue
        seen_chunks.add(chunk_key)
        unique_results.append(result)

    scored_results = []
    for result in unique_results:
        vector_score = float(result.get("similarity_score", 0.0))
        keyword_score = _keyword_score(result)
        metadata_score = _metadata_boost(result, query)
        recency_score = _recency_boost(result)
        penalty = _length_penalty(result)

        if result.get("source") == "fts_search" and vector_score == 0.0:
            vector_score = 0.10

        score = (
            0.40 * vector_score
            + 0.30 * keyword_score
            + 0.20 * metadata_score
            + 0.10 * recency_score
            + penalty
        )
        result["hybrid_score"] = score
        scored_results.append(result)

    scored_results.sort(key=lambda r: r.get("hybrid_score", 0.0), reverse=True)
    return scored_results[:max_results]


def retrieve_relevant_chunks(query: str, case_id: int = None, max_results: int = 10) -> Tuple[str, List[Dict]]:
    """
    Main retrieval function: search both FTS and vector DB, merge results.
    Returns (formatted_context_string, source_metadata_list) tuple.
    """
    if case_id is not None and db.get_case(case_id) is None:
        return "", []

    # Search FTS5 (DB joins exclude soft-deleted cases globally)
    fts_results = db.search_chunks_fts(query, case_id, limit=max_results//2 + 1)

    # Add source indicator
    for result in fts_results:
        result["source"] = "fts_search"

    active_case_ids = db.list_active_case_id_strings()

    # Search vector DB
    vector_results = search_vector_db(query, case_id, n_results=max_results//2 + 1)

    # Drop embeddings tied to Trash / inactive cases (Chroma lacks is_deleted)
    filtered_vector = []
    for result in vector_results:
        md = result.get("metadata") or {}
        cid = str(md.get("case_id") or "").strip()
        if case_id is not None:
            if cid != str(case_id):
                continue
        elif cid and cid not in active_case_ids:
            continue
        filtered_vector.append(result)
    vector_results = filtered_vector

    # Merge results
    merged_results = merge_search_results(fts_results, vector_results, max_results, query)

    # ── CRITICAL FALLBACK ───────────────────────────────────────────────
    # If both FTS and vector search returned nothing (common for vague queries
    # like "summarize this" or "what is this about"), load recent chunks directly
    if not merged_results and case_id is not None:
        fallback_rows = db.get_recent_chunks_for_case(case_id, limit=max_results)
        for row in fallback_rows:
            merged_results.append({
                "chunk_text": row.get("chunk_text", ""),
                "source_metadata": row.get("source_metadata"),
                "document_id": row.get("document_id"),
                "original_filename": row.get("original_filename"),
                "stored_file_path": row.get("stored_file_path"),
                "uploaded_at": row.get("uploaded_at"),
                "page_number": row.get("page_number"),
                "case_id": row.get("case_id"),
                "source": "direct_fallback",
            })

    if not merged_results:
        return "", []

    # Extract comprehensive source metadata
    source_metadata = []
    context_parts = []

    for i, result in enumerate(merged_results):
        # Parse source metadata from JSON if available
        metadata = {}
        if result.get("source_metadata"):
            try:
                metadata = json.loads(result["source_metadata"])
            except:
                pass

        # Get document info
        doc_info = {
            "document_id": result.get("document_id") or metadata.get("document_id"),
            "original_file_name": result.get("original_filename") or metadata.get("original_file_name"),
            "original_file_path": result.get("stored_file_path") or metadata.get("original_file_path"),
            "page_number": result.get("page_number") or metadata.get("page_number"),
            "case_id": result.get("case_id") or metadata.get("case_id"),
            "upload_date": result.get("uploaded_at") or metadata.get("upload_date"),
            "chunk_text": result["chunk_text"]
        }

        source_metadata.append(doc_info)

        # Format context for LLM
        filename = doc_info["original_file_name"] or "unknown"
        page_number = doc_info["page_number"] or "unknown"

        context_parts.append(
            f"[Chunk {i+1} | Source: {filename} | Page: {page_number}]\n"
            f"{result['chunk_text']}"
        )

    return "\n\n---\n\n".join(context_parts), source_metadata


def delete_document_chunks(case_id: int, document_id: int):
    """Delete all chunks for a document from both SQLite and ChromaDB."""
    # Delete from SQLite (this also deletes from FTS5)
    db.delete_chunks_for_document(document_id)

    # Delete from ChromaDB (match stored ids + metadata filter)
    collection = get_or_create_collection()
    chunk_ids = [f"case_{case_id}_doc_{document_id}_chunk_{i}" for i in range(1000)]  # Broad range to catch all

    try:
        collection.delete(ids=chunk_ids)
    except Exception:
        pass  # Ignore errors if chunks don't exist


def delete_vector_embeddings_for_case(case_id: int) -> None:
    """Remove all ChromaDB embeddings whose metadata case_id matches (scoped hard delete)."""
    collection = get_or_create_collection()
    try:
        collection.delete(where={"case_id": str(case_id)})
    except Exception as e:
        raise RuntimeError(f"ChromaDB cleanup failed for case {case_id}: {e}") from e