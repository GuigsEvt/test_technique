from __future__ import annotations

import re

import fitz
import pymupdf4llm


def load_pdf(content: bytes) -> str:
    with fitz.open(stream=content, filetype="pdf") as doc:
        md = pymupdf4llm.to_markdown(doc)
    return clean_pdf_markdown(md)


def clean_pdf_markdown(md: str) -> str:
    md = md.replace("\r\n", "\n").replace("\r", "\n")

    # 1) Fix common hyphenation across line breaks: "inter-\nnational" -> "international"
    md = re.sub(r"(\w)-\n(\w)", r"\1\2", md)

    # 2) Collapse single newlines inside paragraphs into spaces,
    # while keeping blank lines as paragraph separators.
    # Strategy: replace single newlines with spaces, without ruining lists or headings.
    lines = md.split("\n")
    out = []
    for line in lines:
        stripped = line.rstrip()

        # Keep blank lines
        if not stripped:
            out.append("")
            continue

        # Keep markdown structural lines as-is
        if stripped.lstrip().startswith(("#", "-", "*", ">")) or re.match(
            r"^\d+\.\s", stripped
        ):
            out.append(stripped)
            continue

        out.append(stripped)

    md = "\n".join(out)

    # Now collapse non-structural single newlines between text lines.
    # Replace "\n" with " " between two non-empty lines when not a boundary.
    md = re.sub(r"(?<!\n)\n(?!\n)", " ", md)

    # 3) Normalize excessive blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)

    return md.strip()
