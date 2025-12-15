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
    "Exploratoire (recommande)": {
        "top_k": 20,
        "max_distance": 0.55,
        "max_chunks": 8,
        "tagline": "Couverture maximale des données; recommandé pour explorer le corpus.",
    },
    "Strict": {
        "top_k": 12,
        "max_distance": 0.38,
        "max_chunks": 6,
        "tagline": "Priorise la précision; davantage de refus si les sources sont faibles.",
    },
}
DEFAULT_PRESET = "Exploratoire (recommande)"


def build_search_query(
    latest_question: str, history: list[dict[str, str]], window: int = 6
) -> str:
    """Combine recent user messages to preserve conversational intent during retrieval."""
    user_messages = [msg["content"] for msg in history if msg.get("role") == "user"]
    recent = user_messages[-window:]
    if not recent or recent[-1] != latest_question:
        recent.append(latest_question)
    return "\n\n".join(recent).strip()


st.set_page_config(page_title="Chat", page_icon="💬", layout="wide")
try:
    base_settings = get_settings()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

state.init_state(base_settings.conversation_db)

st.sidebar.header("Conversations")
if st.sidebar.button("Nouvelle conversation", use_container_width=True):
    state.new_conversation("Nouvelle conversation")

for conv_id in state.list_conversations():
    title = st.session_state.get(f"title_{conv_id}", "Conversation")
    with st.sidebar.container():
        cols = st.columns([4, 1])
        if cols[0].button(title, key=conv_id, use_container_width=True):
            state.select_conversation(conv_id)
        if cols[1].button("🗑️", key=f"del_{conv_id}"):
            state.delete_conversation(conv_id)
            st.rerun()

# Auto-select the first conversation so messages are visible on load
if not st.session_state.current_conversation and state.list_conversations():
    state.select_conversation(state.list_conversations()[0])

with st.sidebar.expander("Mode de recherche", expanded=True):
    preset_name = st.radio(
        "Rigueur vs rappel",
        options=list(RETRIEVAL_PRESETS.keys()),
        index=list(RETRIEVAL_PRESETS.keys()).index(DEFAULT_PRESET),
        help="Règle la recherche (retriever) avant la génération de la réponse.",
    )
    preset = RETRIEVAL_PRESETS[preset_name]
    settings = replace(
        base_settings,
        top_k=preset["top_k"],
        max_distance=preset["max_distance"],
        max_chunks=preset["max_chunks"],
    )
    st.caption(
        f"{preset['tagline']}\n"
        f"Top-k: {settings.top_k} • Seuil distance: {settings.max_distance} • "
        f"Chunks max: {settings.max_chunks}"
    )

registry = load_registry(settings.registry_path)
collection = get_collection(settings)
chunk_count = count_chunks(collection)

col1, col2 = st.columns(2)
col1.metric("Documents indexés", len(registry))
col2.metric("Chunks", chunk_count)

st.divider()
chat_container = st.container()
prompt = st.chat_input("Posez votre question")

if prompt:
    # Optimistically add the user turn so it renders once in history
    state.append_message("user", prompt)
    history_messages = state.current_messages()

    with chat_container:
        for message in history_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        try:
            with st.chat_message("assistant"):
                with st.spinner("Je réfléchis…"):
                    search_query = build_search_query(prompt, history_messages)
                    contexts = retrieve(search_query, settings)
                    if not contexts:
                        bot_answer = FALLBACK
                        sources = []
                    else:
                        result = generate_answer(prompt, contexts, settings)
                        bot_answer = result.get("answer", FALLBACK)
                        sources = result.get("sources", [])

                st.markdown(bot_answer)
                components.render_sources(sources)
            state.append_message("assistant", bot_answer)
        except RetrievalError as exc:
            logger.error("Retrieval error: %s", exc)
            st.error(user_message(exc))
        except Exception as exc:  # pragma: no cover - streamlit UI
            logger.error("Erreur inattendue: %s", exc)
            st.error("Une erreur est survenue. Réessayez plus tard.")
else:
    with chat_container:
        for message in state.current_messages():
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
