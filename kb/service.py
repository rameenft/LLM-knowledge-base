"""Read-side service: serves search/answer from articles and embeddings held in storage."""

import io
import json

import numpy as np

from . import answer as answer_mod
from . import retrieval
from .storage import BlobNotFound, Storage


class KnowledgeBase:
    def __init__(self, storage: Storage, embedder=retrieval.default_embedder, client_factory=answer_mod.get_client):
        self._storage = storage
        self._embedder = embedder
        self._client_factory = client_factory
        self._cache_key: tuple | None = None
        self._articles: dict[str, str] = {}
        self._topics: list[str] = []
        self._vectors: np.ndarray | None = None

    def _refresh(self) -> None:
        """Reload only when an article's checksum changed (cheap metadata calls, no downloads)."""
        names = [n for n in self._storage.list("processed") if n.endswith(".md")]
        versions = {n[:-3]: self._storage.info("processed", n).sha256 for n in names}
        key = tuple(sorted(versions.items()))
        if key == self._cache_key:
            return
        articles = {t: self._storage.download("processed", f"{t}.md").decode("utf-8") for t in versions}
        topics, vectors = self._load_or_compute_vectors(articles, versions)
        self._articles, self._topics, self._vectors, self._cache_key = articles, topics, vectors, key

    def _load_or_compute_vectors(self, articles, versions):
        # Use precomputed embeddings only if they were built from exactly these article versions.
        try:
            meta = json.loads(self._storage.download("artifacts", "embeddings_meta.json"))
            if meta["versions"] == versions:
                vectors = np.load(io.BytesIO(self._storage.download("artifacts", "embeddings.npy")))
                return meta["topics"], vectors
        except (BlobNotFound, KeyError, ValueError):
            pass
        topics = list(articles)
        texts = [retrieval.article_text_for_embedding(t, articles[t]) for t in topics]
        return topics, self._embedder(texts) if topics else np.zeros((0, 1))

    def list_articles(self) -> list[str]:
        self._refresh()
        return sorted(self._articles)

    def get_article(self, topic: str) -> str:
        self._refresh()
        if topic not in self._articles:
            raise KeyError(topic)
        return self._articles[topic]

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        self._refresh()
        if not self._articles:
            raise ValueError("Knowledge base is empty. Run the ingestion pipeline first.")
        q = self._embedder([query])[0]
        return [{"topic": t, "score": round(s, 4)} for t, s in retrieval.rank(q, self._vectors, self._topics, top_k)]

    def answer(self, question: str, top_k: int = 4) -> answer_mod.Answer:
        hits = [(h["topic"], h["score"]) for h in self.search(question, top_k)]
        return answer_mod.answer_from_hits(question, self._articles, hits, client=self._client_factory())
