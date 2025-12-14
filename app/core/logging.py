import logging
from typing import Optional

_LOGGER: Optional[logging.Logger] = None


def get_logger(name: str = "app") -> logging.Logger:
    global _LOGGER
    if _LOGGER:
        return _LOGGER
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.propagate = False
    _LOGGER = logger
    return logger
