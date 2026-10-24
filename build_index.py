"""
build_index.py
--------------
Rebuilds wiki/_index.json from the compiled wiki articles (no API calls).
"""

import json

from kb import config, wiki


def main():
    index = wiki.build_index(wiki.load_wiki())
    config.INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")

    print(f"Index written: {config.INDEX_PATH}")
    print(f"\n{'Topic':<35} {'Words':>5} {'Out':>4} {'In':>4}")
    print("-" * 52)
    for topic, meta in sorted(index.items()):
        print(f"{topic:<35} {meta['word_count']:>5} "
              f"{len(meta['outgoing_links']):>4} {len(meta['incoming_links']):>4}")


if __name__ == "__main__":
    main()
