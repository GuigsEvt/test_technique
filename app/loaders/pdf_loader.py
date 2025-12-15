from __future__ import annotations

import fitz
import pymupdf4llm


def load_pdf(content: bytes) -> str:
    with fitz.open(stream=content, filetype="pdf") as doc:
        return pymupdf4llm.to_markdown(doc)
