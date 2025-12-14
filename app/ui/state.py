from __future__ import annotations

import uuid
from typing import Dict, List

import streamlit as st


def init_state() -> None:
    if "conversations" not in st.session_state:
        st.session_state.conversations: Dict[str, List[Dict[str, str]]] = {}
    if "current_conversation" not in st.session_state:
        st.session_state.current_conversation = None


def new_conversation(title: str | None = None) -> str:
    conv_id = str(uuid.uuid4())
    st.session_state.conversations[conv_id] = []
    st.session_state.current_conversation = conv_id
    st.session_state[f"title_{conv_id}"] = title or "Conversation"
    return conv_id


def list_conversations() -> List[str]:
    return list(st.session_state.conversations.keys())


def select_conversation(conv_id: str) -> None:
    if conv_id in st.session_state.conversations:
        st.session_state.current_conversation = conv_id


def append_message(role: str, content: str) -> None:
    conv_id = st.session_state.current_conversation
    if not conv_id:
        conv_id = new_conversation()
    st.session_state.conversations[conv_id].append({"role": role, "content": content})


def current_messages() -> List[Dict[str, str]]:
    conv_id = st.session_state.current_conversation
    if not conv_id:
        return []
    return st.session_state.conversations.get(conv_id, [])
