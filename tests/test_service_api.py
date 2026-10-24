import json
from types import SimpleNamespace

import azure.functions as func
import pytest

import function_app
from kb import api, runtime
from kb.config import ConfigError
from kb.service import KnowledgeBase
from tests.conftest import WORDS, fake_embedder


class FakeGemini:
    def __init__(self):
        self.models = SimpleNamespace(generate_content_stream=lambda model, contents, config:
                                      iter([SimpleNamespace(text="See [[Affect]].")]))


@pytest.fixture
def kb(store):
    store.upload("processed", "Affect.md", f"# Affect sad {WORDS}".encode())
    store.upload("processed", "Voice.md", f"# Voice voice {WORDS}".encode())
    return KnowledgeBase(store, embedder=fake_embedder, client_factory=FakeGemini)


def test_search_ranks_relevant_article_first(kb):
    assert kb.search("sad users", 1)[0]["topic"] == "Affect"


def test_answer_cites_sources(kb):
    ans = kb.answer("sad users?")
    assert ans.sources[0] == "Affect" and ans.text == "See **Affect**."


def test_kb_reloads_when_article_changes(kb, store):
    assert kb.search("voice", 1)[0]["topic"] == "Voice"
    store.upload("processed", "Voice.md", f"# Voice sad sad sad {WORDS}".encode())
    store.upload("processed", "Affect.md", f"# Affect voice voice {WORDS}".encode())
    assert kb.search("voice", 1)[0]["topic"] == "Affect"


def test_stale_precomputed_embeddings_are_ignored(kb, store):
    store.upload("artifacts", "embeddings_meta.json", json.dumps({"topics": ["X"], "versions": {"X": "old"}}).encode())
    assert kb.search("sad", 1)[0]["topic"] == "Affect"


def test_empty_kb_raises_value_error(store):
    with pytest.raises(ValueError):
        KnowledgeBase(store, embedder=fake_embedder).search("q")


# ---- api handlers ----------------------------------------------------------

@pytest.mark.parametrize("body", [None, [], {}, {"query": ""}, {"query": "  "}, {"query": 5},
                                  {"query": "x" * 1001}, {"query": "ok", "top_k": 0},
                                  {"query": "ok", "top_k": 11}, {"query": "ok", "top_k": "3"},
                                  {"query": "ok", "top_k": True}])
def test_search_rejects_invalid_input(kb, body):
    status, resp = api.handle_search(kb, body)
    assert status == 400 and resp["error"]["code"] == "invalid_request" and resp["request_id"]


def test_search_success_shape(kb):
    status, resp = api.handle_search(kb, {"query": "sad", "top_k": 2})
    assert status == 200 and len(resp["results"]) == 2 and set(resp["results"][0]) == {"topic", "score"}


def test_answer_success_shape(kb):
    status, resp = api.handle_answer(kb, {"question": "sad?"})
    assert status == 200 and resp["answer"] and resp["sources"]


def test_answer_without_api_key_is_503_and_hides_details(store, monkeypatch):
    store.upload("processed", "Affect.md", f"# A {WORDS}".encode())

    def no_key():
        raise ConfigError("GOOGLE_API_KEY is not set")

    status, resp = api.handle_answer(KnowledgeBase(store, embedder=fake_embedder, client_factory=no_key), {"question": "q"})
    assert status == 503 and "GOOGLE_API_KEY" not in json.dumps(resp)


def test_upstream_failure_is_502_without_leaking(kb):
    class Boom:
        models = SimpleNamespace(generate_content_stream=lambda **k: (_ for _ in ()).throw(RuntimeError("secret detail")))

    kb._client_factory = Boom
    status, resp = api.handle_answer(kb, {"question": "sad?"})
    assert status == 502 and "secret detail" not in json.dumps(resp)


def test_empty_kb_is_503(store):
    status, resp = api.handle_search(KnowledgeBase(store, embedder=fake_embedder), {"query": "q"})
    assert status == 503 and resp["error"]["code"] == "knowledge_base_empty"


# ---- Azure Functions wrappers (called directly, no host needed) ------------

def _req(body: bytes, method="POST", route="search"):
    return func.HttpRequest(method=method, url=f"/api/{route}", body=body, headers={})


@pytest.fixture
def wired(kb, monkeypatch):
    monkeypatch.setattr(runtime, "get_kb", lambda: kb)


# get_functions() rebuilds on every call, so resolve the registered functions exactly once.
_REGISTERED = {f.get_function_name(): f for f in function_app.app.get_functions()}


def _call(name, req):
    return _REGISTERED[name].get_user_function()(req)


def test_function_search_end_to_end(wired):
    resp = _call("search", _req(b'{"query": "sad users"}'))
    assert resp.status_code == 200 and resp.mimetype == "application/json"
    assert json.loads(resp.get_body())["results"][0]["topic"] == "Affect"


def test_function_rejects_bad_json_and_oversize(wired):
    assert _call("search", _req(b"{not json")).status_code == 400
    assert _call("search", _req(b"x" * 20_000)).status_code == 413


def _registered_auth_levels():
    return {n: f.get_trigger().auth_level for n, f in _REGISTERED.items() if f.get_trigger().type == "httpTrigger"}


def test_health_is_anonymous():
    assert _registered_auth_levels()["health"] == func.AuthLevel.ANONYMOUS
    assert json.loads(_call("health", _req(b"", "GET", "health")).get_body()) == {"status": "ok"}


@pytest.mark.parametrize("name", ["search", "answer", "articles", "ingest"])
def test_protected_routes_require_function_key(name):
    assert _registered_auth_levels()[name] == func.AuthLevel.FUNCTION
