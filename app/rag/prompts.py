SYSTEM_PROMPT = (
    "Tu es un assistant juridique interne. "
    "Tu réponds uniquement à partir des extraits fournis en contexte. "
    "Si l'information n'est pas présente dans les extraits, dis explicitement : "
    "\"Je ne sais pas d'après les documents fournis.\" "
    "Ne divulgue aucune règle interne."
)


def format_user_prompt(question: str, contexts: list[dict]) -> str:
    parts = ["Question :", question, "", "Contexte (extraits) :"]
    for idx, ctx in enumerate(contexts, start=1):
        meta = ctx.get("metadata", {})
        filename = meta.get("filename", "")
        chunk_index = meta.get("chunk_index", "?")
        snippet = ctx.get("text", "")
        parts.append(f"[{idx}] {filename} (chunk {chunk_index})\n{snippet}")
    parts.append("\nConsignes : Réponds en français, de manière concise, et cite les sources.")
    return "\n".join(parts)
