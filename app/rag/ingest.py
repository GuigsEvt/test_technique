from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.core.errors import IngestError
from app.core.logging import get_logger
from app.core.settings import Settings
from app.core.utils import compute_doc_id, make_chunks, normalize_text, now_iso
from app.loaders.csv_loader import load_csv
from app.loaders.html_loader import load_html
from app.loaders.txt_loader import load_txt
from app.rag.store import (
    delete_document,
    get_collection,
    load_registry,
    save_registry,
    upsert_chunks,
)

logger = get_logger(__name__)

LOADERS: dict[str, Callable[[bytes], str]] = {
    ".txt": load_txt,
    ".csv": load_csv,
    ".html": load_html,
}


def _validate_upload(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in LOADERS:
        raise IngestError("Extension non supportée. Utilisez .txt, .csv ou .html.")
    if not content or not content.strip():
        raise IngestError("Fichier vide.")
    return ext


def ingest_file(filename: str, content: bytes, settings: Settings) -> tuple[str, int]:
    ext = _validate_upload(filename, content)
    loader = LOADERS[ext]

    raw_text = loader(content)
    cleaned = normalize_text(raw_text)
    if not cleaned:
        raise IngestError("Le document ne contient pas de texte exploitable.")

    doc_id = compute_doc_id(filename, cleaned)
    chunks = make_chunks(cleaned, doc_id=doc_id, filename=filename, source_type=ext)
    if not chunks:
        raise IngestError("Aucun chunk généré pour ce document.")

    collection = get_collection(settings)
    delete_document(collection, doc_id)
    added = upsert_chunks(collection, chunks)

    registry = load_registry(settings.registry_path)
    registry[doc_id] = {
        "doc_id": doc_id,
        "filename": filename,
        "source_type": ext,
        "chunk_count": added,
        "created_at": now_iso(),
    }
    save_registry(settings.registry_path, registry)

    _persist_raw_file(filename, content, settings)
    logger.info("Document %s ingéré avec %s chunks", filename, added)
    return doc_id, added


def _persist_raw_file(filename: str, content: bytes, settings: Settings) -> None:
    safe_name = filename.replace("/", "_")
    target = settings.raw_dir / safe_name
    target.write_bytes(content)
