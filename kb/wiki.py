"""Reading the wiki and building its link graph. Pure functions, no network."""

import json
import re
from pathlib import Path

from . import config

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def extract_wikilinks(text: str) -> list[str]:
    return _WIKILINK_RE.findall(text)


def build_index(articles: dict[str, str]) -> dict:
    """Link graph with word counts, in the same shape as wiki/_index.json."""
    index = {}
    for topic, content in articles.items():
        index[topic] = {
            "filename": f"{topic}.md",
            "word_count": len(content.split()),
            "outgoing_links": extract_wikilinks(content),
            "incoming_links": [],
        }
    for topic in index:
        index[topic]["incoming_links"] = [
            other
            for other, meta in index.items()
            if topic in meta["outgoing_links"] and other != topic
        ]
    return index


def load_wiki(wiki_dir: Path | None = None) -> dict[str, str]:
    wiki_dir = Path(wiki_dir or config.WIKI_DIR)
    if not wiki_dir.is_dir():
        return {}
    return {
        p.stem: p.read_text(encoding="utf-8")
        for p in sorted(wiki_dir.glob("*.md"))
        if not p.name.startswith("_")
    }


def load_index(index_path: Path | None = None) -> dict:
    index_path = Path(index_path or config.INDEX_PATH)
    if index_path.exists():
        return json.loads(index_path.read_text(encoding="utf-8"))
    return {}


def render_wikilinks(text: str, available: set[str]) -> str:
    """Bold links to existing articles, italicise links to missing ones."""

    def replace(m: re.Match) -> str:
        t = m.group(1)
        return f"**{t}**" if t in available else f"*{t}*"

    return _WIKILINK_RE.sub(replace, text)
