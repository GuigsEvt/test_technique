from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

# ----------------------------
# Text normalization helpers
# ----------------------------


def normalize_line(line: str) -> str:
    """
    Normalize a single line: collapse repeated spaces/tabs, remove NBSP,
    keep it as a single-line string.
    """
    line = line.replace("\xa0", " ")
    line = re.sub(r"[ \t]+", " ", line)
    return line.strip()


def normalize_paragraph(paragraph: str) -> str:
    """
    Normalize a paragraph while preserving paragraph boundaries.
    Keeps internal newlines within the paragraph as spaces, but does not
    collapse paragraph separators.
    """
    # Convert any internal line breaks to spaces, then normalize spaces.
    paragraph = paragraph.replace("\r\n", "\n").replace("\r", "\n")
    cleaned_lines = [normalize_line(line) for line in paragraph.split("\n")]
    paragraph = " ".join(line for line in cleaned_lines if line)
    paragraph = re.sub(r"\s+", " ", paragraph)
    return paragraph.strip()


def split_paragraphs(text: str) -> list[str]:
    """
    Split text into paragraphs using blank lines as separators, while
    keeping semantic structure for better retrieval.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    # Split on 1+ blank lines
    raw_paras = re.split(r"\n\s*\n+", text)
    paras = [normalize_paragraph(p) for p in raw_paras]
    return [p for p in paras if p]


# ----------------------------
# Source loaders helpers
# ----------------------------


def strip_html(html: str) -> str:
    """
    Remove tags plus script/style content, return paragraph-preserving text.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Preserve block-level separation as newlines
    text = soup.get_text(separator="\n")
    # Clean up: normalize each line but keep blank lines to form paragraphs
    lines = []
    for raw in text.splitlines():
        line = normalize_line(raw)
        if line:
            lines.append(line)
        else:
            # Keep blank line markers
            lines.append("")
    # Recreate text with blank lines (paragraph boundaries)
    # Collapse multiple blank lines
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def csv_to_text(csv_content: str, max_rows: int = 200) -> str:
    """
    Converts CSV content into a formatted plain text representation.
    Preserves rows as paragraphs.
    """
    output_lines: list[str] = []
    reader = csv.reader(io.StringIO(csv_content))
    for idx, row in enumerate(reader):
        if idx >= max_rows:
            output_lines.append("[... sortie tronquée ...]")
            break
        cells = [normalize_line(cell) for cell in row]
        # Skip fully empty rows
        if not any(cells):
            continue
        output_lines.append(" | ".join(cells))
    # Each row is a line; paragraph splitting will treat blank lines as separators
    return "\n".join(output_lines)


# ----------------------------
# Identifiers & file utilities
# ----------------------------


def compute_doc_id(filename: str, content: str) -> str:
    """
    Stable-ish doc id: depends on filename + content.
    If you want content-only stability, remove filename from the hash input.
    """
    digest = hashlib.sha1((filename + "::" + content).encode("utf-8")).hexdigest()
    return f"doc::{digest}"


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def ensure_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("{}", encoding="utf-8")


# ----------------------------
# Paragraph-aware chunking
# ----------------------------


def _split_long_text(text: str, max_chars: int) -> list[str]:
    """
    Split a long string into max_chars pieces on sentence-ish boundaries when possible,
    falling back to hard splits if needed.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    # Try to split on sentence boundaries.
    # This is a heuristic: it avoids cutting in the middle of a sentence when possible.
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end == len(text):
            parts.append(text[start:end].strip())
            break

        window = text[start:end]
        # Prefer splitting near the end on ".", "?", "!" or ";" then ":" then "," then space
        cut = max(
            window.rfind("."),
            window.rfind("?"),
            window.rfind("!"),
            window.rfind(";"),
        )
        if cut < int(max_chars * 0.6):
            cut = max(window.rfind(":"), window.rfind(","))
        if cut < int(max_chars * 0.6):
            cut = window.rfind(" ")

        if cut <= 0:
            # Hard split
            parts.append(window.strip())
            start = end
        else:
            parts.append(window[: cut + 1].strip())
            start = start + cut + 1

    return [p for p in parts if p]


def make_chunks(
    text: str,
    doc_id: str,
    filename: str,
    source_type: str,
    max_chars: int = 1000,
    overlap: int = 200,
) -> list[tuple[str, str, dict]]:
    """
    Paragraph-aware chunking:
    - Split text into paragraphs (blank-line separated)
    - Accumulate paragraphs until reaching max_chars
    - Use overlap by carrying the last `overlap` chars from the previous chunk
    - If a paragraph is longer than max_chars, split it on sentence-ish boundaries

    Returns list of (chunk_id, chunk_text, metadata).
    """
    raw = text.strip()
    if not raw:
        return []

    paragraphs = split_paragraphs(raw)
    if not paragraphs:
        return []

    chunks: list[tuple[str, str, dict]] = []
    buffer = ""
    idx = 0
    # We’ll build a normalized “joined” text for approximate char positions
    # (positions are best-effort for audit/debug; not exact original file offsets)
    joined_for_cursor = "\n\n".join(paragraphs)

    def emit_chunk(chunk_text: str, approx_end: int) -> None:
        nonlocal idx
        # Approximate char_start based on end - len(chunk_text)
        approx_start = max(0, approx_end - len(chunk_text))
        metadata = {
            "doc_id": doc_id,
            "filename": filename,
            "source_type": source_type,
            "chunk_index": idx,
            "char_start": approx_start,
            "char_end": approx_end,
            "created_at": now_iso(),
        }
        chunk_id = f"{doc_id}::chunk::{idx}"
        chunks.append((chunk_id, chunk_text, metadata))
        idx += 1

    # Build chunks
    cursor = 0
    for para in paragraphs:
        # If paragraph itself is too long, split it further
        para_parts = _split_long_text(para, max_chars=max_chars)

        for part in para_parts:
            # Candidate by adding this paragraph part
            candidate = (buffer + "\n\n" + part).strip() if buffer else part

            if len(candidate) <= max_chars:
                buffer = candidate
                # Update cursor approx: advance by part length plus a separator.
                # This keeps char_end increasing and roughly aligned.
                cursor = min(len(joined_for_cursor), cursor + len(part) + 2)
                continue

            # If buffer already has content, emit it
            if buffer:
                # Emit current buffer
                emit_chunk(buffer, approx_end=min(len(joined_for_cursor), cursor))

                # Create new buffer with overlap + current part
                if overlap > 0:
                    carry = buffer[-overlap:] if len(buffer) > overlap else buffer
                    buffer = (carry + "\n\n" + part).strip()
                else:
                    buffer = part

                cursor = min(len(joined_for_cursor), cursor + len(part) + 2)
            else:
                # No buffer but candidate too big (rare due to _split_long_text)
                emit_chunk(
                    part[:max_chars].strip(),
                    approx_end=min(len(joined_for_cursor), cursor + max_chars),
                )
                buffer = ""
                cursor = min(len(joined_for_cursor), cursor + len(part) + 2)

    # Emit remainder
    if buffer:
        emit_chunk(buffer, approx_end=min(len(joined_for_cursor), cursor))

    return chunks
