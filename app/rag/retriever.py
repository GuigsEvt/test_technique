from __future__ import annotations

from typing import Dict, List

from app.core.errors import RetrievalError
from app.core.logging import get_logger
from app.core.settings import Settings
from app.rag.store import get_collection

logger = get_logger(__name__)


def retrieve(query: str, settings: Settings) -> List[Dict]:
    collection = get_collection(settings)
    try:
        results = collection.query(
            query_texts=[query],
            n_results=settings.top_k,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:  # pragma: no cover - chroma internal
        raise RetrievalError(str(exc)) from exc

    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    if not docs:
        return []

    filtered: List[Dict] = []
    for chunk_id, text, metadata, distance in zip(ids, docs, metadatas, distances):
        if distance is None:
            continue
        if distance > settings.max_distance:
            continue
        similarity = max(0.0, 1 - float(distance))
        filtered.append({
            "id": chunk_id,
            "text": text,
            "metadata": metadata,
            "score": similarity,
        })

    return filtered
