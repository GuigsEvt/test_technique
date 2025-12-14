
import shutil

from app.core.settings import CHROMA_DIR, RAW_DIR, REGISTRY_PATH


def reset() -> None:
    shutil.rmtree(CHROMA_DIR, ignore_errors=True)
    shutil.rmtree(RAW_DIR, ignore_errors=True)
    REGISTRY_PATH.unlink(missing_ok=True)
    print("Index et données supprimés.")


if __name__ == "__main__":
    reset()
