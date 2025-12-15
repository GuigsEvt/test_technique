from __future__ import annotations

import json
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import EmbeddingFunction
from openai import OpenAI

from app.core.errors import VectorStoreError
from app.core.logging import get_logger
from app.core.settings import Settings
from app.core.utils import ensure_file

logger = get_logger(__name__)


class OpenAIEmbedding(EmbeddingFunction):
    """
    Embedding function that uses the OpenAI API to embed a list of texts.

    Args:
        settings (Settings): Carries API key and embedding model name.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)

    def __call__(self, texts: list[str]) -> list[list[float]]:  # type: ignore[override]
        embeddings: list[list[float]] = []
        for text in texts:
            response = self.client.embeddings.create(
                model=self.settings.embedding_model,
                input=text,
            )
            embeddings.append(response.data[0].embedding)
        return embeddings


@lru_cache(maxsize=1)
def get_collection(settings: Settings) -> Collection:
    try:
        client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        return client.get_or_create_collection(
            name="documents",
            embedding_function=OpenAIEmbedding(settings),
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as exc:  # pragma: no cover - chroma internal
        raise VectorStoreError(str(exc)) from exc


def load_registry(path: Path) -> dict[str, dict]:
    ensure_file(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_registry(path: Path, registry: dict[str, dict]) -> None:
    path.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def upsert_chunks(
    collection: Collection, chunks: Iterable[tuple[str, str, dict]]
) -> int:
    """
    Inserts or updates multiple document chunks in the given collection.

    Args:
        collection (Collection): The collection object where the chunks will be upserted.
        chunks (Iterable[Tuple[str, str, dict]]): An iterable of tuples, each containing:
            - chunk_id (str): The unique identifier for the chunk.
            - text (str): The text content of the chunk.
            - metadata (dict): Metadata associated with the chunk.

    Returns:
        int: The number of chunks successfully upserted.

    Raises:
        VectorStoreError: If an error occurs during the upsert operation.
    """
    ids, documents, metadatas = [], [], []
    for chunk_id, text, metadata in chunks:
        ids.append(chunk_id)
        documents.append(text)
        metadatas.append(metadata)
    if not ids:
        return 0
    try:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return len(ids)
    except Exception as exc:  # pragma: no cover - chroma internal
        raise VectorStoreError(str(exc)) from exc


def delete_document(collection: Collection, doc_id: str) -> None:
    try:
        collection.delete(where={"doc_id": doc_id})
    except Exception as exc:  # pragma: no cover - chroma internal
        raise VectorStoreError(str(exc)) from exc


def count_chunks(collection: Collection) -> int:
    try:
        return collection.count()
    except Exception as exc:  # pragma: no cover
        logger.error("Erreur lors du comptage des chunks: %s", exc)
        return 0


def fetch_document_chunks(
    collection: Collection, doc_id: str, limit: int = 3
) -> list[dict]:
    """Retourne un aperçu des chunks d'un document donné."""
    try:
        results = collection.get(
            where={"doc_id": doc_id}, include=["documents", "metadatas"]
        )
    except Exception as exc:  # pragma: no cover - chroma internal
        raise VectorStoreError(str(exc)) from exc

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    if not documents or not metadatas:
        return []

    entries: list[dict] = []
    for text, metadata in zip(documents, metadatas, strict=False):
        entries.append({"text": text, "metadata": metadata})

    entries.sort(key=lambda item: item.get("metadata", {}).get("chunk_index", 0))
    return entries[:limit]
