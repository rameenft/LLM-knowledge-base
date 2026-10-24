from kb import compiler


def test_prompt_mentions_topic_and_excludes_self_from_links():
    p = compiler.build_prompt("VoiceInterface", "desc", "SOURCES")
    assert "**VoiceInterface**" in p
    assert "SOURCES" in p
    links_line = p.split("from this list: ")[1].splitlines()[0]
    assert "VoiceInterface" not in links_line
    assert "AffectiveComputing" in links_line


def test_load_raw_sources_reads_only_markdown(tmp_path):
    (tmp_path / "01.md").write_text("one", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")
    assert compiler.load_raw_sources(tmp_path) == {"01.md": "one"}


def test_real_raw_notes_load():
    assert len(compiler.load_raw_sources()) == 10
