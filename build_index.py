"""
build_index.py
--------------
Builds _index.json from the pre-compiled wiki articles.
Run this once after pre-compilation or after any wiki edits.
"""

import os
import re
import json

WIKI_DIR = os.path.join(os.path.dirname(__file__), "wiki")
INDEX_PATH = os.path.join(WIKI_DIR, "_index.json")


def extract_wikilinks(text: str) -> list[str]:
    return re.findall(r"\[\[([^\]]+)\]\]", text)


def main():
    articles = {}
    for fname in os.listdir(WIKI_DIR):
        if fname.endswith(".md") and not fname.startswith("_"):
            path = os.path.join(WIKI_DIR, fname)
            with open(path, "r", encoding="utf-8") as f:
                topic = fname[:-3]
                articles[topic] = f.read()

    index = {}
    for topic, content in articles.items():
        links = extract_wikilinks(content)
        index[topic] = {
            "filename": f"{topic}.md",
            "word_count": len(content.split()),
            "outgoing_links": links,
            "incoming_links": [],
        }

    for topic in index:
        for other, meta in index.items():
            if topic in meta["outgoing_links"] and other != topic:
                index[topic]["incoming_links"].append(other)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    print(f"Index written: {INDEX_PATH}")
    print(f"\n{'Topic':<35} {'Words':>5} {'Out':>4} {'In':>4}")
    print("-" * 52)
    for topic, meta in sorted(index.items()):
        print(f"{topic:<35} {meta['word_count']:>5} {len(meta['outgoing_links']):>4} {len(meta['incoming_links']):>4}")


if __name__ == "__main__":
    main()
