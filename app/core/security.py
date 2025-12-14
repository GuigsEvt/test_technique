from __future__ import annotations

import re
from typing import Iterable

SUSPICIOUS_PATTERNS: Iterable[str] = (
    r"ignore previous",
    r"reset instructions",
    r"override rules",
    r"system prompt",
)


def is_prompt_safe(text: str) -> bool:
    lowered = text.lower()
    return not any(re.search(pattern, lowered) for pattern in SUSPICIOUS_PATTERNS)


def redact_text(text: str, max_length: int = 2000) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + " ..."
