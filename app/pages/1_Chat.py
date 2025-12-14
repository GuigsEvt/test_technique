from __future__ import annotations

from dataclasses import replace

import streamlit as st

from app.core.errors import RetrievalError, user_message
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.rag.answer import FALLBACK, generate_answer
from app.rag.retriever import retrieve
from app.rag.store import count_chunks, get_collection, load_registry
from app.ui import components, state

logger = get_logger(__name__)


RETRIEVAL_PRESETS = {
    "PoC safe (recommande)": {
        "top_k": 12,
        "max_distance": 0.28,
        "max_chunks": 6,
        "tagline": "Bon rappel + sources vérifiées (recommandé pour une démonstration).",
    },
    "Tres strict": {
        "top_k": 8,
        "max_distance": 0.22,
        "max_chunks": 4,
        "tagline": "Hallucinations minimales ; peut répondre plus souvent \"Je ne sais pas\".",
    },
    "Exploratoire": {
        "top_k": 20,
        "max_distance": 0.45,
        "max_chunks": 8,
        "tagline": "Couverture maximale des données; nécessite une requête très précise pour canaliser la réponse.",
    },
}
DEFAULT_PRESET = "PoC safe (recommande)"

st.set_page_config(page_title="Chat", page_icon="💬", layout="wide")
state.init_state()

try:
    base_settings = get_settings()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

st.sidebar.header("Conversations")
if st.sidebar.button("Nouvelle conversation", use_container_width=True):
    state.new_conversation("Nouvelle conversation")

for conv_id in state.list_conversations():
    title = st.session_state.get(f"title_{conv_id}", "Conversation")
    if st.sidebar.button(title, key=conv_id):
        state.select_conversation(conv_id)

with st.sidebar.expander("Mode de recherche", expanded=True):
    preset_name = st.radio(
        "Rigueur vs rappel",
        options=list(RETRIEVAL_PRESETS.keys()),
        index=list(RETRIEVAL_PRESETS.keys()).index(DEFAULT_PRESET),
        help="Ajustez la rigueur de la recherche d'informations (retriever) avant la génération de la réponse.",
    )
    preset = RETRIEVAL_PRESETS[preset_name]
    settings = replace(
        base_settings,
        top_k=preset["top_k"],
        max_distance=preset["max_distance"],
        max_chunks=preset["max_chunks"],
    )
    st.caption(
        f"{preset['tagline']}\nTop-k: {settings.top_k} • Seuil distance: {settings.max_distance} • Chunks max: {settings.max_chunks}"
    )

registry = load_registry(settings.registry_path)
collection = get_collection(settings)
chunk_count = count_chunks(collection)

col1, col2 = st.columns(2)
col1.metric("Documents indexés", len(registry))
col2.metric("Chunks", chunk_count)

st.divider()
for message in state.current_messages():
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Posez votre question")
if prompt:
    state.append_message("user", prompt)
    try:
        contexts = retrieve(prompt, settings)
        if not contexts:
            bot_answer = FALLBACK
            sources = []
        else:
            result = generate_answer(prompt, contexts, settings)
            bot_answer = result.get("answer", FALLBACK)
            sources = result.get("sources", [])

        state.append_message("assistant", bot_answer)
        with st.chat_message("assistant"):
            st.markdown(bot_answer)
            components.render_sources(sources)
    except RetrievalError as exc:
        logger.error("Retrieval error: %s", exc)
        st.error(user_message(exc))
    except Exception as exc:  # pragma: no cover - streamlit UI
        logger.error("Erreur inattendue: %s", exc)
        st.error("Une erreur est survenue. Réessayez plus tard.")
