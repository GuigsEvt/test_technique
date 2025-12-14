from __future__ import annotations

import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

logger = logging.getLogger(__name__)


def init_state(db_path: Path) -> None:
    """Initialize session state and hydrate from sqlite."""
    st.session_state.setdefault("conversation_db_path", db_path)
    db_path = Path(st.session_state["conversation_db_path"])
    _ensure_db(db_path)

    if "conversations" not in st.session_state:
        st.session_state.conversations = _load_conversations(db_path)
    if "current_conversation" not in st.session_state:
        st.session_state.current_conversation = None


def new_conversation(title: str | None = None, headline: Optional[str] = None) -> str:
    conv_id = str(uuid.uuid4())
    resolved_title = title or "Conversation"
    st.session_state.conversations[conv_id] = []
    st.session_state.current_conversation = conv_id
    st.session_state[f"title_{conv_id}"] = resolved_title
    if headline:
        st.session_state[f"headline_{conv_id}"] = headline
    _insert_conversation(conv_id, resolved_title, headline)
    return conv_id


def list_conversations() -> List[str]:
    return list(st.session_state.conversations.keys())[::-1]


def select_conversation(conv_id: str) -> None:
    if conv_id in st.session_state.conversations:
        st.session_state.current_conversation = conv_id


def delete_conversation(conv_id: str) -> None:
    if conv_id not in st.session_state.conversations:
        return
    _delete_conversation(conv_id)
    st.session_state.conversations.pop(conv_id, None)
    st.session_state.pop(f"title_{conv_id}", None)
    st.session_state.pop(f"headline_{conv_id}", None)
    if st.session_state.current_conversation == conv_id:
        remaining = list_conversations()
        st.session_state.current_conversation = remaining[0] if remaining else None


def append_message(role: str, content: str) -> None:
    conv_id = st.session_state.current_conversation
    if not conv_id:
        conv_id = new_conversation()
    st.session_state.conversations[conv_id].append({"role": role, "content": content})
    _insert_message(conv_id, role, content)


def current_messages() -> List[Dict[str, str]]:
    conv_id = st.session_state.current_conversation
    if not conv_id:
        return []
    return st.session_state.conversations.get(conv_id, [])


# --- Persistence helpers -------------------------------------------------


def _ensure_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                headline TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conv_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(conv_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
            """
        )
        _ensure_headline_column(conn)
        conn.commit()


def _load_conversations(db_path: Path) -> Dict[str, List[Dict[str, str]]]:
    conversations: Dict[str, List[Dict[str, str]]] = {}
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for row in conn.execute(
            "SELECT id, title, headline FROM conversations ORDER BY created_at ASC"
        ):
            conversations[row["id"]] = []
            st.session_state[f"title_{row['id']}"] = row["title"] or "Conversation"
            if row["headline"]:
                st.session_state[f"headline_{row['id']}"] = row["headline"]

        for row in conn.execute(
            "SELECT conv_id, role, content FROM messages ORDER BY created_at ASC, id ASC"
        ):
            conversations.setdefault(row["conv_id"], []).append(
                {"role": row["role"], "content": row["content"]}
            )
    return conversations


def _insert_conversation(conv_id: str, title: str, headline: Optional[str]) -> None:
    db_path = Path(st.session_state["conversation_db_path"])
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO conversations (id, title, headline) VALUES (?, ?, ?)",
                (conv_id, title, headline),
            )
            conn.commit()
    except sqlite3.Error as exc:
        logger.error("Failed to persist conversation %s: %s", conv_id, exc)


def _insert_message(conv_id: str, role: str, content: str) -> None:
    db_path = Path(st.session_state["conversation_db_path"])
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO messages (conv_id, role, content) VALUES (?, ?, ?)",
                (conv_id, role, content),
            )
            conn.commit()
    except sqlite3.Error as exc:
        logger.error("Failed to persist message for %s: %s", conv_id, exc)


def _delete_conversation(conv_id: str) -> None:
    db_path = Path(st.session_state["conversation_db_path"])
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM messages WHERE conv_id = ?", (conv_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()
    except sqlite3.Error as exc:
        logger.error("Failed to delete conversation %s: %s", conv_id, exc)


def _ensure_headline_column(conn: sqlite3.Connection) -> None:
    """Add headline column if migrating an older DB."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(conversations)")}
    if "headline" not in columns:
        conn.execute("ALTER TABLE conversations ADD COLUMN headline TEXT")
