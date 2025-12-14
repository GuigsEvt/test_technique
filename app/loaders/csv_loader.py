from __future__ import annotations

from app.core.utils import csv_to_text


def load_csv(content: bytes) -> str:
    text = content.decode("utf-8", errors="ignore")
    return csv_to_text(text)
