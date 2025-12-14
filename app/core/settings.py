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
    """
    Settings dataclass for application configuration.

    Attributes:
        openai_api_key (str): API key for accessing OpenAI services.
        embedding_model (str): Name of the embedding model to use (default: "text-embedding-3-small").
        chat_model (str): Name of the chat model to use (default: "gpt-4o-mini").
        top_k (int): Number of top results to retrieve in search or ranking operations (default: 10).
        max_distance (float): Maximum allowed distance (e.g., cosine similarity threshold) for filtering results (default: 0.3).
        max_chunks (int): Maximum number of text chunks to process or return (default: 8).
        raw_dir (Path): Path to the directory containing raw data files.
        chroma_dir (Path): Path to the directory used by Chroma for vector storage.
        registry_path (Path): Path to the registry file or directory for storing metadata or configuration.
    """
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    top_k: int = 12
    max_distance: float = 0.28
    max_chunks: int = 6
    raw_dir: Path = RAW_DIR
    chroma_dir: Path = CHROMA_DIR
    registry_path: Path = REGISTRY_PATH


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY manquant. Définissez la variable d'environnement.")
    return Settings(openai_api_key=api_key)
