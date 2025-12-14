from __future__ import annotations

import streamlit as st

from app.core.errors import IngestError, VectorStoreError, user_message
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.rag.ingest import ingest_file
from app.rag.store import (
    count_chunks,
    delete_document,
    get_collection,
    load_registry,
    save_registry,
)

logger = get_logger(__name__)

st.set_page_config(page_title="Documents", page_icon="📁", layout="wide")

try:
    settings = get_settings()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

collection = get_collection(settings)
registry = load_registry(settings.registry_path)
chunk_count = count_chunks(collection)

col1, col2 = st.columns(2)
col1.metric("Documents indexés", len(registry))
col2.metric("Chunks", chunk_count)

st.subheader("Uploader des documents")
uploaded_files = st.file_uploader(
    "Choisissez des fichiers .txt, .csv, .html",
    type=["txt", "csv", "html"],
    accept_multiple_files=True,
)

if uploaded_files:
    for uploaded in uploaded_files:
        try:
            content = uploaded.getvalue()
            doc_id, added = ingest_file(uploaded.name, content, settings)
            registry[doc_id] = registry.get(doc_id, {}) | {
                "doc_id": doc_id,
                "filename": uploaded.name,
                "chunk_count": added,
            }
            st.success(f"{uploaded.name} indexé ({added} chunks)")
        except (IngestError, VectorStoreError) as exc:
            st.error(user_message(exc))
        except Exception as exc:  # pragma: no cover - streamlit UI
            logger.error("Erreur inattendue: %s", exc)
            st.error("Échec de l'upload pour ce fichier.")
    save_registry(settings.registry_path, registry)

st.divider()
st.subheader("Documents existants")

if not registry:
    st.info("Aucun document indexé pour le moment.")
else:
    for doc_id, info in registry.items():
        cols = st.columns([3, 2, 1])
        cols[0].markdown(f"**{info.get('filename', 'N/A')}**")
        cols[1].markdown(f"Chunks: {info.get('chunk_count', '?')}")
        if cols[2].button("Supprimer", key=doc_id):
            try:
                delete_document(collection, doc_id)
                registry.pop(doc_id, None)
                save_registry(settings.registry_path, registry)
                st.success("Document supprimé")
                st.experimental_rerun()
            except VectorStoreError as exc:
                st.error(user_message(exc))
