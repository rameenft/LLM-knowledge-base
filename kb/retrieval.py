"""Embedding-based retrieval over wiki articles.

The ranking math (`rank`) is separate from the embedding model so it can be tested
with hand-made vectors and no model download.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np

from . import config

# An embedder maps a list of strings to an (n, dim) array of unit-length vectors.
Embedder = Callable[[list[str]], np.ndarray]


@lru_cache(maxsize=1)
def _load_model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=config.EMBED_MODEL)


def default_embedder(texts: list[str]) -> np.ndarray:
    """Local ONNX MiniLM embeddings (no PyTorch). Model is loaded once per process."""
    vectors = np.array(list(_load_model().embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.clip(norms, 1e-12, None)


def article_text_for_embedding(topic: str, content: str, max_words: int = 500) -> str:
    """Topic name plus the first `max_words` words (existing behaviour)."""
    return f"{topic}\n{' '.join(content.split()[:max_words])}"


def build_embedding_index(
    articles: dict[str, str],
    embedder: Embedder = default_embedder,
    vectors_path: Path | None = None,
    topics_path: Path | None = None,
    force: bool = False,
) -> dict:
    """Embed all articles, using an on-disk cache when it matches the current articles.

    The cache is a .npy array plus a JSON topic list (not pickle, so it is safe to
    later store in shared storage).
    """
    vectors_path = Path(vectors_path or config.EMBEDDINGS_PATH)
    topics_path = Path(topics_path or config.EMBEDDING_TOPICS_PATH)

    if not force and vectors_path.exists() and topics_path.exists():
        cached_topics = json.loads(topics_path.read_text(encoding="utf-8"))
        if set(cached_topics) == set(articles):
            return {"topics": cached_topics, "vectors": np.load(vectors_path)}

    topics = list(articles)
    vectors = embedder([article_text_for_embedding(t, articles[t]) for t in topics])
    vectors_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(vectors_path, vectors)
    topics_path.write_text(json.dumps(topics), encoding="utf-8")
    return {"topics": topics, "vectors": vectors}


def rank(
    query_vector: np.ndarray, vectors: np.ndarray, topics: list[str], top_k: int = 4
) -> list[tuple[str, float]]:
    """Top-k (topic, cosine score) pairs. Assumes unit-length vectors."""
    scores = vectors @ query_vector
    order = np.argsort(scores)[::-1][:top_k]
    return [(topics[i], float(scores[i])) for i in order]


def retrieve(
    question: str,
    articles: dict[str, str],
    top_k: int = 4,
    embedder: Embedder = default_embedder,
    **cache_paths,
) -> list[tuple[str, float]]:
    cache = build_embedding_index(articles, embedder=embedder, **cache_paths)
    q = embedder([question])[0]
    return rank(q, cache["vectors"], cache["topics"], top_k)
