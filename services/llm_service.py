"""
KanoonVault LLM Service
Calls OpenRouter to power KanoonVault's chat interface.
Designed with retrieval prompt patterns inspired by LlamaIndex and RAG.
Responses are strictly grounded in stored case memory.
"""
import json
import httpx
from typing import AsyncIterator
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import OPENROUTER_URL, OPENROUTER_MODEL, OPENROUTER_API_KEY, MAX_CONTEXT_CHARS
from services.vector_memory_service import retrieve_relevant_chunks
from typing import AsyncIterator, Tuple, List, Dict

# Special commands that should return file links instead of AI answers
SPECIAL_COMMANDS = [
    "show original file", "open pdf", "where is this written", "show source",
    "download document", "view original", "open document", "get file"
]

# ── System Prompts ──────────────────────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """You are KanoonVault Legal Memory OS.

You are NOT a lawyer.
You are NOT allowed to give legal advice or predictions.

You are a STRICT retrieval-based legal intelligence system.

────────────────────────────
CORE RULES (NON-NEGOTIABLE)
────────────────────────────
1. Answer ONLY using provided CASE MEMORY.
2. If information is missing → say: "Not found in case memory."
3. Never hallucinate facts, laws, judgments, or assumptions.
4. Always prioritize:
   - FIR numbers
   - Court names
   - Dates
   - Case IDs
   - Parties involved
5. Keep answers structured and factual.
6. If asked for advice → refuse and redirect to case documents.

OUTPUT FORMAT
────────────────────────────
- Use bullet points for facts
- Use timelines for events
- Use short sentences
- Always cite document references when available

RETRIEVAL INJECTION
────────────────────────────
You are given extracted legal case chunks.
TASK:
- Use ONLY the provided chunks.
- Merge overlapping facts.
- Remove duplicates.
- Preserve chronology.
- Highlight contradictions if any exist.

DO NOT infer missing information.
DO NOT add external knowledge.

CASE MEMORY
────────────────────────────
{case_memory}
"""

NO_CASE_PROMPT = """You are KanoonVault Legal Memory OS.

You are NOT a lawyer.
You are NOT allowed to give legal advice or predictions.

You have no case memory to answer from.
Politely tell the user to:
1. Create or select a case from the sidebar
2. Upload legal documents (PDFs, images, text files) to build the case memory
3. Then ask questions about their case

If asked for legal advice, refuse and redirect to case documents.
Do NOT answer any legal questions without case memory.
"""


def is_special_command(question: str) -> bool:
    """Check if the question is asking for original file access."""
    question_lower = question.lower().strip()
    return any(cmd in question_lower for cmd in SPECIAL_COMMANDS)


def format_source_references(source_metadata: List[Dict]) -> str:
    """Format source metadata into the required format with clickable links."""
    if not source_metadata:
        return "Sources:\nNo sources available."

    sources = []
    seen_files = set()  # Avoid duplicate file references

    for metadata in source_metadata:
        filename = metadata.get("original_file_name", "Unknown")
        page_number = metadata.get("page_number", "Unknown")
        document_id = metadata.get("document_id", "Unknown")

        # Create unique key for deduplication
        file_key = f"{filename}_page_{page_number}"

        if file_key not in seen_files:
            if page_number and page_number != "Unknown":
                sources.append(f"[{filename}] — Page [{page_number}] — [DOC_ID:{document_id}]")
            else:
                sources.append(f"[{filename}] — [DOC_ID:{document_id}]")
            seen_files.add(file_key)

    return "Sources:\n" + "\n".join(sources)


async def stream_response(
    question: str,
    case_id: int = None,
) -> AsyncIterator[Tuple[str, List[Dict]]]:
    """
    Yields (token, source_metadata) tuples from OpenRouter as they stream in.
    Uses vector memory to retrieve relevant chunks for the question.
    """
    from config import get_api_key
    api_key = get_api_key("OPENROUTER")
    if not api_key:
        yield "❌ **API Key Missing**: OpenRouter API key is not configured. Please click on setup to configure your API key.", []
        return

    # Check for special commands
    if is_special_command(question):
        # For special commands, return empty response with source metadata
        case_memory, source_metadata = retrieve_relevant_chunks(question, case_id, max_results=5)
        yield "", source_metadata
        return

    # Retrieve relevant chunks using hybrid search (FTS + vector)
    case_memory, source_metadata = retrieve_relevant_chunks(question, case_id, max_results=8)

    if not case_memory.strip():
        system = NO_CASE_PROMPT
    else:
        system = SYSTEM_PROMPT_TEMPLATE.format(case_memory=case_memory)

    from config import OPENROUTER_FALLBACK_MODEL
    models_to_try = [OPENROUTER_MODEL]
    if OPENROUTER_FALLBACK_MODEL and OPENROUTER_FALLBACK_MODEL not in models_to_try:
        models_to_try.append(OPENROUTER_FALLBACK_MODEL)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kanoonvault.local",
        "X-Title": "KanoonVault"
    }

    last_error = ""

    for model_name in models_to_try:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": question}
            ],
            "stream": True,
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 1024,
        }

        try:
            tokens_yielded = False
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", OPENROUTER_URL, json=payload, headers=headers) as resp:
                    if resp.status_code != 200:
                        err_body = await resp.aread()
                        err_text = err_body.decode('utf-8', errors='replace')
                        last_error = f"HTTP {resp.status_code}: {err_text[:200]}"
                        print(f"[LLM Service] Model '{model_name}' failed with {last_error}. Trying fallback...")
                        continue

                    async for line in resp.aiter_lines():
                        if line.strip():
                            if line.startswith("data: "):
                                line = line[6:]  # Remove "data: " prefix
                            if line.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(line)
                                if data.get("error"):
                                    err_info = data.get("error")
                                    err_msg = err_info.get("message") if isinstance(err_info, dict) else str(err_info)
                                    raw_msg = err_info.get("metadata", {}).get("raw", "") if isinstance(err_info, dict) and isinstance(err_info.get("metadata"), dict) else ""
                                    last_error = f"{err_msg} ({raw_msg})" if raw_msg else str(err_msg)
                                    print(f"[LLM Service] Stream error on model '{model_name}': {last_error}. Trying fallback...")
                                    break

                                if data.get("choices") and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    token = delta.get("content", "")
                                    if token:
                                        tokens_yielded = True
                                        yield token, source_metadata
                            except json.JSONDecodeError:
                                continue

            if tokens_yielded:
                return

        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"[LLM Service] Exception on model '{model_name}': {last_error}. Trying fallback...")
            continue

    # If all models fail
    yield f"⚠️ **OpenRouter AI Error**: Unable to get response from primary model (`{OPENROUTER_MODEL}`) or fallback (`{OPENROUTER_FALLBACK_MODEL}`). Details: {last_error}", []


async def get_response(question: str, case_id: int = None) -> Tuple[str, List[Dict]]:
    """Non-streaming version, returns (response_string, source_metadata) tuple."""
    tokens = []
    source_metadata = []
    async for token, metadata in stream_response(question, case_id):
        tokens.append(token)
        if metadata and not source_metadata:  # Capture metadata once
            source_metadata = metadata
    return "".join(tokens), source_metadata
