from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CHROMA_DIR = DATA_DIR / "chroma"
REGISTRY_PATH = DATA_DIR / "registry.json"

for path in (DATA_DIR, RAW_DIR, CHROMA_DIR):
    path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    top_k: int = 12
    max_distance: float = 0.28
    max_chunks: int = 6
    raw_dir: Path = RAW_DIR
    chroma_dir: Path = CHROMA_DIR
    registry_path: Path = REGISTRY_PATH
    conversation_db: Path = DATA_DIR / "conversations.db"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY manquant. Définissez la variable d'environnement.")
    return Settings(openai_api_key=api_key)
