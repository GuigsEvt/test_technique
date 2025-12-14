class AppError(Exception):
    """Base application error."""


class IngestError(AppError):
    """Raised when ingestion fails."""


class VectorStoreError(AppError):
    """Raised when vector store operations fail."""


class RetrievalError(AppError):
    """Raised when retrieval fails."""


class LLMError(AppError):
    """Raised when LLM generation fails."""


USER_MESSAGES = {
    IngestError: "Impossible d'ingérer ce document.",
    VectorStoreError: "La base vectorielle n'est pas disponible.",
    RetrievalError: "Aucun résultat pertinent trouvé.",
    LLMError: "Le modèle de génération est indisponible pour le moment.",
}


def user_message(exc: Exception) -> str:
    for exc_type, message in USER_MESSAGES.items():
        if isinstance(exc, exc_type):
            return message
    return "Une erreur est survenue. Merci de réessayer."
