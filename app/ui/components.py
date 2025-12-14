from __future__ import annotations

from typing import Dict, Iterable

import streamlit as st


def render_sources(sources: Iterable[Dict]) -> None:
    if not sources:
        return
    with st.expander("Sources"):
        for src in sources:
            filename = src.get("filename", "?")
            chunk_idx = src.get("chunk_index", "?")
            score = src.get("score")
            preview = src.get("preview", "").strip()
            score_txt = f" (score {score:.2f})" if isinstance(score, (int, float)) else ""
            st.markdown(f"- **{filename}** (chunk {chunk_idx}){score_txt}")
            if preview:
                st.caption(preview)
