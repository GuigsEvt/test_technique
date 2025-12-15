from __future__ import annotations

from openai import OpenAI

from app.core.errors import LLMError
from app.core.security import is_prompt_safe
from app.core.settings import Settings
from app.rag.prompts import SYSTEM_PROMPT, format_user_prompt

FALLBACK = "Je ne sais pas d'après les documents fournis."


def generate_answer(question: str, contexts: list[dict], settings: Settings) -> dict:
    if not contexts:
        return {"answer": FALLBACK, "sources": []}
    if not is_prompt_safe(question):
        return {"answer": "Requête refusée (sécurité).", "sources": []}

    prompt = format_user_prompt(question, contexts[: settings.max_chunks])
    client = OpenAI(api_key=settings.openai_api_key)

    try:
        response = client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Low temperature for more focused answers; ideal for RAGs
            max_tokens=1000,
        )
    except Exception as exc:  # pragma: no cover - network
        raise LLMError(str(exc)) from exc

    choice = response.choices[0].message.content if response.choices else ""
    answer_text = (choice or "").strip()
    if not answer_text:
        return {"answer": FALLBACK, "sources": []}
    if answer_text == FALLBACK:
        return {"answer": FALLBACK, "sources": []}

    sources = _format_sources(contexts)
    if not sources:
        return {"answer": FALLBACK, "sources": []}

    return {"answer": answer_text, "sources": sources}


def _format_sources(contexts: list[dict]) -> list[dict]:
    formatted: list[dict] = []
    for ctx in contexts:
        meta = ctx.get("metadata", {})
        formatted.append(
            {
                "doc_id": meta.get("doc_id"),
                "filename": meta.get("filename"),
                "chunk_index": meta.get("chunk_index"),
                "score": ctx.get("score"),
                "preview": ctx.get("text", "")[:240],
            }
        )
    return formatted
