"""
KanoonVault Timeline Service
Extracts dates and legal events from OCR text using regex patterns.
Falls back to LLM (Gemma 4) when needed; works offline if regex/heuristics match.
"""
import re
import json
import time
import httpx
from typing import Optional

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TIMELINE_API_KEY, TIMELINE_MODEL, TIMELINE_URL, OPENROUTER_API_KEY

MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

EVENT_KEYWORDS = [
    (r"FIR\s+(?:No\.?|Number|Reg(?:istered)?\.?)?", "FIR Registered"),
    (r"First Information Report", "FIR Registered"),
    (r"administrative\s+notification", "Administrative Notification"),
    (r"circuit\s+bench", "Circuit Bench"),
    (r"notification\s+(?:No\.?|from)", "Official Notification"),
    (r"arrest(?:ed)?", "Arrest"),
    (r"bail\s+(?:granted|approved|rejected|denied)", "Bail Decision"),
    (r"hearing", "Court Hearing"),
    (r"order\s+(?:issued|passed|given)", "Court Order Issued"),
    (r"judgment|judgement", "Judgment Issued"),
    (r"chargesheet|charge sheet", "Chargesheet Filed"),
    (r"petition\s+filed", "Petition Filed"),
    (r"complaint\s+(?:filed|lodged|registered)", "Complaint Filed"),
    (r"witness\s+(?:statement|testimony|deposition)", "Witness Statement"),
    (r"adjourned|adjournment", "Hearing Adjourned"),
    (r"interim\s+order", "Interim Order"),
    (r"summons?\s+(?:issued|sent|served)", "Summons Issued"),
    (r"notice\s+(?:issued|sent|served)", "Notice Issued"),
    (r"\bPETITION\b", "Petition Filed"),
    (r"COURT\s+OF\s+APPEAL", "Court of Appeal"),
    (r"CERTIFIED\s+TRUE\s+COPY", "Certified Copy"),
    (r"\bNOTIFICATION\b", "Official Notification"),
]


def _timeline_api_key() -> str:
    from config import get_api_key
    return get_api_key("TIMELINE") or get_api_key("OPENROUTER")


def _expand_year(y: str) -> Optional[str]:
    y = re.sub(r"\D", "", y)
    if not y:
        return None
    if len(y) == 4:
        return y
    if len(y) == 2:
        n = int(y)
        return str(2000 + n if n < 50 else 1900 + n)
    if len(y) == 3:
        return "2" + y  # e.g. 025 -> 2025
    return None


def _normalize_dmY(d: str, m: str, y: str) -> Optional[str]:
    year = _expand_year(y)
    if not year:
        return None
    try:
        mi, di = int(m), int(d)
        if not (1 <= mi <= 12 and 1 <= di <= 31):
            return None
        return f"{year}-{str(mi).zfill(2)}-{str(di).zfill(2)}"
    except ValueError:
        return None


def _line_at(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    line = text[start:end].strip()
    return re.sub(r"\s+", " ", line)[:200]


def _find_dates_in_text(text: str) -> list[tuple[int, str]]:
    """Return (char_position, YYYY-MM-DD) from text including garbled OCR formats."""
    found: list[tuple[int, str]] = []

    for m in re.finditer(
        r"(?i)(?:dated|date|period)\s*[:\-]?\s*(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})",
        text,
    ):
        ds = _normalize_dmY(m.group(1), m.group(2), m.group(3))
        if ds:
            found.append((m.start(), ds))

    for m in re.finditer(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b", text):
        ds = _normalize_dmY(m.group(1), m.group(2), m.group(3))
        if ds:
            found.append((m.start(), ds))

    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        found.append((m.start(), f"{m.group(1)}-{m.group(2)}-{m.group(3)}"))

    month_pat = (
        r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(\d{4})\b"
    )
    for m in re.finditer(month_pat, text, re.IGNORECASE):
        d, m_name, y = m.groups()
        mo = MONTH_MAP.get(m_name.lower(), "01")
        found.append((m.start(), f"{y}-{mo}-{d.zfill(2)}"))

    for m in re.finditer(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
        text,
        re.IGNORECASE,
    ):
        m_name, d, y = m.groups()
        mo = MONTH_MAP.get(m_name.lower(), "01")
        found.append((m.start(), f"{y}-{mo}-{d.zfill(2)}"))

    for m in re.finditer(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?"
        r"(January|February|March|April|May|June|July|August|September|"
        r"October|November|December),?\s+(\d{4})\b",
        text,
        re.IGNORECASE,
    ):
        d, m_name, y = m.groups()
        mo = MONTH_MAP.get(m_name.lower(), "01")
        found.append((m.start(), f"{y}-{mo}-{d.zfill(2)}"))

    # Deduplicate overlapping matches at same position
    seen_pos: set[int] = set()
    unique = []
    for pos, ds in sorted(found, key=lambda x: x[0]):
        bucket = pos // 5
        if bucket in seen_pos:
            continue
        seen_pos.add(bucket)
        unique.append((pos, ds))
    return unique


def _find_events_near_date(text: str, date_pos: int, window: int = 300) -> str:
    start = max(0, date_pos - window)
    end = min(len(text), date_pos + window)
    snippet = text[start:end]
    for pattern, label in EVENT_KEYWORDS:
        if re.search(pattern, snippet, re.IGNORECASE):
            return label
    return "Legal Event"


def _event_description(text: str, date_pos: int) -> str:
    line = _line_at(text, date_pos)
    label = _find_events_near_date(text, date_pos)
    if line and len(line) > 12:
        if label != "Legal Event":
            return f"{label} — {line[:140]}"
        return line[:180]
    return label


def _merge_timeline_events(*groups: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    merged: list[dict] = []
    for group in groups:
        for ev in group:
            key = (ev.get("event_date"), ev.get("event_desc", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            merged.append(ev)
    merged.sort(key=lambda e: e.get("event_date") or "9999-99-99")
    return merged


def extract_timeline_events(text: str, source_file: str) -> list[dict]:
    """
    Parse OCR text → list of {event_date, event_desc, source_file}.
    Regex first, LLM supplement, heuristic fallback (no API required).
    """
    if not text or len(text.strip()) < 10:
        return []
    if text.strip().startswith("[No text") or text.strip().startswith("[Image OCR"):
        return []

    regex_events = _extract_timeline_regex(text, source_file)
    llm_events: list[dict] = []

    api_key = _timeline_api_key()
    if api_key and len(regex_events) < 3:
        print(f"[Timeline] Regex found {len(regex_events)} events, trying LLM...")
        llm_events = _extract_timeline_llm(text, source_file, api_key)

    events = _merge_timeline_events(regex_events, llm_events)

    if not events:
        events = _extract_timeline_heuristic(text, source_file)
        if events:
            print(f"[Timeline] Heuristic fallback found {len(events)} events")

    if not events and len(text.strip()) > 80:
        snippet = re.sub(r"\s+", " ", text.strip())[:160]
        events.append({
            "event_date": None,
            "event_desc": f"Document processed — {snippet}",
            "source_file": source_file,
        })

    print(f"[Timeline] Total {len(events)} events for {source_file}")
    return events


def _extract_timeline_regex(text: str, source_file: str) -> list[dict]:
    dates = _find_dates_in_text(text)
    seen: set[tuple] = set()
    events: list[dict] = []

    for pos, date_str in dates:
        desc = _event_description(text, pos)
        key = (date_str, desc[:80])
        if key not in seen:
            seen.add(key)
            events.append({
                "event_date": date_str,
                "event_desc": desc,
                "source_file": source_file,
            })

    events.sort(key=lambda e: e["event_date"] or "9999-99-99")
    return events


def _extract_timeline_heuristic(text: str, source_file: str) -> list[dict]:
    """Keyword + loose-date extraction when LLM is unavailable or OCR is noisy."""
    events: list[dict] = []
    seen: set[tuple] = set()

    for pos, date_str in _find_dates_in_text(text):
        desc = _event_description(text, pos)
        key = (date_str, desc[:60])
        if key not in seen:
            seen.add(key)
            events.append({
                "event_date": date_str,
                "event_desc": desc,
                "source_file": source_file,
            })

    for pattern, label in EVENT_KEYWORDS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            line = _line_at(text, m.start())
            desc = f"{label} — {line}" if line else label
            key = (None, desc[:80])
            if key not in seen and len(desc) > 8:
                seen.add(key)
                events.append({
                    "event_date": None,
                    "event_desc": desc[:200],
                    "source_file": source_file,
                })

    return events[:25]


TIMELINE_EXTRACTION_PROMPT = """You are a legal document analyst. Extract ALL dates and events from the following OCR text.

The text may be noisy, garbled, or poorly OCR'd. Do your best to identify:
- Any dates (even partially visible), including DD.MM.YYYY and DD-MM-YYYY
- What legal or administrative event happened on that date

Return ONLY a JSON array. Each item must have exactly these fields:
- "event_date": date in YYYY-MM-DD format (best guess if partially visible)
- "event_desc": short description of what happened

If you cannot find ANY dates or events, return an empty array: []

IMPORTANT: Return ONLY the JSON array, no explanation, no markdown, no code blocks.

OCR TEXT:
{ocr_text}"""


def _parse_llm_json_array(content: str) -> list:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        m = re.search(r"\[[\s\S]*\]", content)
        if m:
            try:
                data = json.loads(m.group(0))
                return data if isinstance(data, list) else []
            except json.JSONDecodeError:
                pass
    return []


def _extract_timeline_llm(text: str, source_file: str, api_key: str) -> list[dict]:
    """Gemma 4 via OpenRouter; retries on 429."""
    trimmed = text[:8000]
    payload = {
        "model": TIMELINE_MODEL,
        "messages": [
            {"role": "user", "content": TIMELINE_EXTRACTION_PROMPT.format(ocr_text=trimmed)}
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    delays = [5, 15, 30]
    for attempt in range(len(delays) + 1):
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(TIMELINE_URL, json=payload, headers=headers)
                resp.raise_for_status()

            content = resp.json()["choices"][0]["message"]["content"].strip()
            events_raw = _parse_llm_json_array(content)
            events = []
            for ev in events_raw:
                if not isinstance(ev, dict):
                    continue
                event_date = (ev.get("event_date") or "").strip()
                event_desc = (ev.get("event_desc") or "").strip()
                if not event_desc:
                    continue
                if event_date and not re.match(r"\d{4}-\d{2}-\d{2}", event_date):
                    event_date = ""
                events.append({
                    "event_date": event_date or None,
                    "event_desc": event_desc,
                    "source_file": source_file,
                })
            if events:
                print(f"[Timeline] LLM found {len(events)} events")
            return events

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < len(delays):
                wait = delays[attempt]
                print(f"[Timeline LLM] Rate limited (429), retry in {wait}s...")
                time.sleep(wait)
                continue
            print(f"[Timeline LLM] Error: {e}")
            return []
        except Exception as e:
            print(f"[Timeline LLM] Error: {e}")
            return []
    return []


def detect_case_metadata(text: str) -> dict:
    """Extract case number, FIR number, and court name from text."""
    meta = {"case_number": None, "court_name": None, "fir_number": None}

    m = re.search(
        r"\b(?:Case|Suit|C\.A\.|Crl\.|Cr\.P\.C|W\.P|Civil\s+Suit|Notification)\s*"
        r"(?:No\.?|#)?\s*([\w\d./\-]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        meta["case_number"] = m.group(1).strip()[:60]

    m = re.search(r"\bFIR\s*(?:No\.?|#)?\s*(\d+(?:[/-]\d+)*)", text, re.IGNORECASE)
    if m:
        meta["fir_number"] = m.group(1).strip()
        if not meta["case_number"]:
            meta["case_number"] = f"FIR-{meta['fir_number']}"

    m = re.search(
        r"((?:Sessions|High|Supreme|Civil|District|Magistrate|Judicial|Appeal)\s+"
        r"Court[^\n,]{0,60})",
        text,
        re.IGNORECASE,
    )
    if m:
        meta["court_name"] = m.group(1).strip()

    return meta
