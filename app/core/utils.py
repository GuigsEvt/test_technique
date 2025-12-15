from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


def normalize_text(text: str) -> str:
    """
    Normalizes the input text by replacing multiple whitespace characters with a single space,
    removing non-breaking spaces, and trimming leading and trailing whitespace.

    Args:
        text (str): The input string to normalize.

    Returns:
        str: The normalized string.
    """
    cleaned = re.sub(r"\s+", " ", text)
    cleaned = cleaned.replace("\xa0", " ")
    return cleaned.strip()


def strip_html(html: str) -> str:
    """
    Remove tags plus script/style content, normalize text, return newline-separated plain text.

    Args:
        html (str): The HTML content to be stripped and cleaned.

    Returns:
        str: Plain text extracted from the HTML with script and style contents removed.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [normalize_text(line) for line in text.splitlines() if normalize_text(line)]
    return "\n".join(lines)


def csv_to_text(csv_content: str, max_rows: int = 200) -> str:
    """
    Converts CSV content into a formatted plain text representation.

    Args:
        csv_content (str): The CSV data as a string.
        max_rows (int, optional): Maximum number of rows to include. Additional rows are truncated
            and a notice is appended. Defaults to 200.

    Returns:
        str: Formatted CSV with cells separated by " | " and rows by newlines.
            Truncated with a notice if rows exceed `max_rows`.
    """
    output_lines: list[str] = []
    reader = csv.reader(io.StringIO(csv_content))
    for idx, row in enumerate(reader):
        if idx >= max_rows:
            output_lines.append("[... sortie tronquée ...]")
            break
        cells = [cell.strip() for cell in row]
        output_lines.append(" | ".join(cells))
    return "\n".join(output_lines)


def compute_doc_id(filename: str, content: str) -> str:
    digest = hashlib.sha1((filename + "::" + content).encode("utf-8")).hexdigest()
    return f"doc::{digest}"


def make_chunks(
    text: str,
    doc_id: str,
    filename: str,
    source_type: str,
    max_chars: int = 1200,
    overlap: int = 180,
) -> list[tuple[str, str, dict]]:
    """
    Split a text into overlapping chunks of a maximum length.

    Args:
        text (str): Text to chunk.
        doc_id (str): Identifier for the document.
        filename (str): Name of the source file.
        source_type (str): Type or origin of the source.
        max_chars (int, optional): Max characters per chunk. Defaults to 1200.
        overlap (int, optional): Overlap between chunks. Defaults to 180.

    Returns:
        List[Tuple[str, str, dict]]: Each tuple contains chunk_id, chunk_text, and metadata
            (doc ID, filename, source type, chunk index, character range).

    If the input text is empty or only whitespace, returns an empty list.
    """
    normalized = text.strip()
    if not normalized:
        return []
    step = max_chars - overlap if max_chars > overlap else max_chars
    chunks: list[tuple[str, str, dict]] = []
    for idx, start in enumerate(range(0, len(normalized), step)):
        chunk_text = normalized[start : start + max_chars]
        metadata = {
            "doc_id": doc_id,
            "filename": filename,
            "source_type": source_type,
            "chunk_index": idx,
            "char_start": start,
            "char_end": start + len(chunk_text),
        }
        chunk_id = f"{doc_id}::chunk::{idx}"
        chunks.append((chunk_id, chunk_text, metadata))
    return chunks


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def ensure_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("{}", encoding="utf-8")
