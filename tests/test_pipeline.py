import json

import pytest

from kb import pipeline
from kb.pipeline import PipelineError, run_pipeline, validate_document
from tests.conftest import TOPICS, WORDS, fake_embedder


class Compiler:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail or {}

    def __call__(self, client, topic, description, sources_text):
        self.calls.append(topic)
        if topic in self.fail:
            raise self.fail.pop(topic)
        return f"{topic} article {WORDS}"


class Transient(Exception):
    code = 503


def run(store, compiler, **kw):
    return run_pipeline(store, client=None, embedder=fake_embedder, topics=TOPICS,
                        compile_fn=compiler, sleep=lambda s: None, **kw)


def test_first_run_compiles_everything_and_publishes_artifacts(raw_store):
    c = Compiler()
    r = run(raw_store, c)
    assert r.ok and r.compiled == ["Affect", "Voice"] and not r.skipped
    assert sorted(raw_store.list("processed")) == ["Affect.md", "Voice.md"]
    assert {"index.json", "embeddings.npy", "embeddings_meta.json", "manifest.json"} <= set(raw_store.list("artifacts"))


def test_second_run_is_idempotent_no_gemini_calls(raw_store):
    run(raw_store, Compiler())
    c2 = Compiler()
    r = run(raw_store, c2)
    assert c2.calls == [] and r.skipped == ["Affect", "Voice"] and not r.compiled


def test_changed_raw_note_triggers_recompile(raw_store):
    run(raw_store, Compiler())
    raw_store.upload("raw", "01.md", b"edited notes about sad users")
    c = Compiler()
    assert run(raw_store, c).compiled == ["Affect", "Voice"]


def test_force_recompiles(raw_store):
    run(raw_store, Compiler())
    c = Compiler()
    run(raw_store, c, force=True)
    assert c.calls == ["Affect", "Voice"]


def test_transient_error_is_retried_then_succeeds(raw_store):
    c = Compiler(fail={"Affect": Transient()})
    r = run(raw_store, c)
    assert r.ok and c.calls.count("Affect") == 2


def test_failure_isolated_and_next_run_resumes_only_failed_topic(raw_store):
    class Hard(Exception):
        code = 400

    r = run(raw_store, Compiler(fail={"Affect": Hard("bad request")}))
    assert not r.ok and list(r.failed) == ["Affect"] and r.compiled == ["Voice"]
    c = Compiler()
    r2 = run(raw_store, c)
    assert r2.ok and c.calls == ["Affect"] and r2.skipped == ["Voice"]


def test_too_short_article_rejected(raw_store):
    r = run(raw_store, lambda *a: "tiny")
    assert set(r.failed) == {"Affect", "Voice"} and raw_store.list("processed") == []


def test_bad_documents_are_quarantined_not_fatal(raw_store):
    raw_store.upload("raw", "empty.md", b"   \n")
    raw_store.upload("raw", "binary.md", b"\xff\xfe\x00bad")
    r = run(raw_store, Compiler())
    assert set(r.quarantined) == {"empty.md", "binary.md"} and r.ok
    assert "empty file" in raw_store.download("quarantine", "empty.md.reason.txt").decode()
    assert raw_store.exists("raw", "empty.md")  # inputs are never deleted


def test_no_valid_documents_raises_and_leaves_wiki_untouched(store):
    store.upload("raw", "bad.md", b"")
    with pytest.raises(PipelineError):
        run(store, Compiler())


def test_corrupted_processed_article_is_recompiled(raw_store):
    run(raw_store, Compiler())
    raw_store.upload("processed", "Affect.md", b"# Affect\n\nhand edited")
    c = Compiler()
    run(raw_store, c)
    assert c.calls == ["Affect"]


def test_manifest_records_corpus_hash(raw_store):
    r = run(raw_store, Compiler())
    m = json.loads(raw_store.download("artifacts", "manifest.json"))
    assert m["corpus_hash"] == r.corpus_hash and set(m["topics"]) == {"Affect", "Voice"}


@pytest.mark.parametrize("data,expected", [
    (b"", "empty"), (b"x" * 600_000, "too large"), (b"\xff\xfe", "UTF-8"), (b"ok text", None)])
def test_validate_document(data, expected):
    reason = validate_document("a.md", data)
    assert (reason is None) if expected is None else (expected in reason)


def test_sync_raw_dir_uploads_only_changes(store, tmp_path):
    d = tmp_path / "src"
    d.mkdir()
    (d / "a.md").write_text("one")
    assert pipeline.sync_raw_dir(store, d) == {"uploaded": ["a.md"], "unchanged": []}
    assert pipeline.sync_raw_dir(store, d) == {"uploaded": [], "unchanged": ["a.md"]}
    (d / "a.md").write_text("two")
    assert pipeline.sync_raw_dir(store, d)["uploaded"] == ["a.md"]
