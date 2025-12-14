from __future__ import annotations

from app.core.utils import strip_html


def load_html(content: bytes) -> str:
    text = content.decode("utf-8", errors="ignore")
    return strip_html(text)
