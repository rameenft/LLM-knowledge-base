from types import SimpleNamespace

import pytest

from kb import answer, config
from tests.test_retrieval import fake_embedder


class FakeClient:
    """Mimics client.models.generate_content_stream without any network."""

    def __init__(self, pieces):
        self.prompts = []
        self.models = SimpleNamespace(generate_content_stream=self._stream)
        self._pieces = pieces

    def _stream(self, model, contents, config):
        self.prompts.append(contents)
        return iter(SimpleNamespace(text=p) for p in self._pieces)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EMBEDDINGS_PATH", tmp_path / "v.npy")
    monkeypatch.setattr(config, "EMBEDDING_TOPICS_PATH", tmp_path / "t.json")


def test_answer_uses_retrieved_articles_and_renders_links():
    articles = {"Affect": "sad detection", "Voice": "voice latency"}
    client = FakeClient(["See [[Affect]]", " and [[Missing]]."])
    result = answer.answer_question("sad?", articles, client=client,
                                    embedder=fake_embedder, top_k=1)
    assert result.sources == ["Affect"]
    assert result.text == "See **Affect** and *Missing*."
    assert "=== Affect ===" in client.prompts[0]
    assert "=== Voice ===" not in client.prompts[0]


def test_on_chunk_callback_receives_pieces():
    seen = []
    answer.answer_question("sad?", {"Affect": "sad"}, client=FakeClient(["a", "b"]),
                           embedder=fake_embedder, on_chunk=seen.append)
    assert seen == ["a", "b"]


def test_empty_wiki_raises_value_error():
    with pytest.raises(ValueError):
        answer.answer_question("q", {}, client=FakeClient([]))


def test_missing_api_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(config.ConfigError):
        config.get_google_api_key()
