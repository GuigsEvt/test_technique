from __future__ import annotations


def load_txt(content: bytes) -> str:
    return content.decode("utf-8", errors="ignore")
