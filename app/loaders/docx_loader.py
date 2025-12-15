from __future__ import annotations

from io import BytesIO

from docx import Document


def load_docx(content: bytes) -> str:
    document = Document(BytesIO(content))
    paragraphs = [
        para.text.strip() for para in document.paragraphs if para.text.strip()
    ]
    return "\n".join(paragraphs)
