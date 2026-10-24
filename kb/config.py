"""Central configuration. Everything comes from environment variables with local defaults."""

import os
from pathlib import Path

try:  # optional: load a local .env during development
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = Path(os.environ.get("KB_RAW_DIR", ROOT / "raw"))
WIKI_DIR = Path(os.environ.get("KB_WIKI_DIR", ROOT / "wiki"))
INDEX_PATH = WIKI_DIR / "_index.json"
EMBEDDINGS_PATH = WIKI_DIR / "_embeddings.npy"
EMBEDDING_TOPICS_PATH = WIKI_DIR / "_embedding_topics.json"

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COMPILE_MODEL = "gemini-2.5-flash"
QA_MODEL = "gemini-2.5-flash"


class ConfigError(RuntimeError):
    """Raised when required configuration (e.g. an API key) is missing."""


def get_google_api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        raise ConfigError(
            "GOOGLE_API_KEY is not set. Put it in a local .env file or the environment."
        )
    return key
