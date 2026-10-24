import json

from kb import config, wiki


def test_extract_wikilinks():
    assert wiki.extract_wikilinks("See [[A]] and [[B C]], not [D].") == ["A", "B C"]


def test_build_index_links_and_counts():
    index = wiki.build_index({"A": "x [[B]] y", "B": "hello [[A]] [[B]]"})
    assert index["A"]["outgoing_links"] == ["B"]
    assert index["A"]["incoming_links"] == ["B"]
    assert index["B"]["incoming_links"] == ["A"]  # self-links not counted
    assert index["A"]["word_count"] == 3


def test_render_wikilinks_distinguishes_known_and_unknown():
    out = wiki.render_wikilinks("[[A]] and [[Z]]", {"A"})
    assert out == "**A** and *Z*"


def test_load_wiki_skips_underscore_files(tmp_path):
    (tmp_path / "A.md").write_text("a", encoding="utf-8")
    (tmp_path / "_hidden.md").write_text("h", encoding="utf-8")
    assert wiki.load_wiki(tmp_path) == {"A": "a"}


def test_load_wiki_missing_dir_returns_empty(tmp_path):
    assert wiki.load_wiki(tmp_path / "nope") == {}


def test_refactor_reproduces_committed_index():
    """Regression guard: the new code must give the same graph the project shipped with."""
    articles = wiki.load_wiki()
    committed = json.loads(config.INDEX_PATH.read_text(encoding="utf-8"))
    rebuilt = wiki.build_index(articles)
    for topic, meta in committed.items():
        assert rebuilt[topic]["outgoing_links"] == meta["outgoing_links"]
        assert sorted(rebuilt[topic]["incoming_links"]) == sorted(meta["incoming_links"])
