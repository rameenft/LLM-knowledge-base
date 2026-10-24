import numpy as np
import pytest

from kb import retrieval


def unit(v):
    v = np.array(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def fake_embedder(texts):
    """Deterministic: 'sad' texts point along axis 0, 'voice' along axis 1."""
    out = []
    for t in texts:
        t = t.lower()
        out.append(unit([2 if "sad" in t else 0.1, 2 if "voice" in t else 0.1, 0.1]))
    return np.array(out)


def test_rank_orders_by_cosine():
    vectors = np.array([unit([1, 0]), unit([0, 1]), unit([1, 1])])
    result = retrieval.rank(unit([1, 0.1]), vectors, ["x", "y", "z"], top_k=2)
    assert [t for t, _ in result] == ["x", "z"]
    assert result[0][1] > result[1][1]


def test_rank_top_k_larger_than_corpus():
    vectors = np.array([unit([1, 0])])
    assert len(retrieval.rank(unit([1, 0]), vectors, ["x"], top_k=5)) == 1


def test_retrieve_finds_expected_article(tmp_path):
    articles = {"Affect": "detecting sad users", "Voice": "voice latency budget"}
    paths = dict(vectors_path=tmp_path / "v.npy", topics_path=tmp_path / "t.json")
    hits = retrieval.retrieve("how do we spot sad people", articles, top_k=1,
                              embedder=fake_embedder, **paths)
    assert hits[0][0] == "Affect"


def test_cache_is_reused_when_topics_match(tmp_path):
    calls = []

    def counting(texts):
        calls.append(len(texts))
        return fake_embedder(texts)

    articles = {"A": "sad", "B": "voice"}
    paths = dict(vectors_path=tmp_path / "v.npy", topics_path=tmp_path / "t.json")
    retrieval.build_embedding_index(articles, embedder=counting, **paths)
    retrieval.build_embedding_index(articles, embedder=counting, **paths)
    assert calls == [2]  # second call hit the cache


def test_cache_rebuilds_when_articles_change(tmp_path):
    calls = []

    def counting(texts):
        calls.append(len(texts))
        return fake_embedder(texts)

    paths = dict(vectors_path=tmp_path / "v.npy", topics_path=tmp_path / "t.json")
    retrieval.build_embedding_index({"A": "sad"}, embedder=counting, **paths)
    retrieval.build_embedding_index({"A": "sad", "B": "voice"}, embedder=counting, **paths)
    assert calls == [1, 2]


def test_embedding_text_truncates_to_500_words():
    text = retrieval.article_text_for_embedding("T", " ".join(["w"] * 900))
    assert len(text.split()) == 501  # topic name + 500 words
