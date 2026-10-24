"""
compile_wiki.py
---------------
CLI wrapper around kb.compiler. Reads raw notes and uses Gemini to synthesize
a structured, interlinked wiki.

Usage:
    python compile_wiki.py              # compile all (skip existing)
    python compile_wiki.py --force      # recompile everything
    python compile_wiki.py --topic AffectiveComputing
    python compile_wiki.py --dry-run    # show plan, don't call API
"""

import argparse
import json

from google import genai

from kb import config, wiki
from kb.compiler import WIKI_TOPICS, compile_article, load_raw_sources, sources_to_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--topic")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config.WIKI_DIR.mkdir(parents=True, exist_ok=True)

    client = None
    if not args.dry_run:
        try:
            client = genai.Client(api_key=config.get_google_api_key())
        except config.ConfigError as e:
            print(e)
            print("Get a free key at https://aistudio.google.com")
            return

    print(f"Loading raw sources from {config.RAW_DIR}/")
    raw = load_raw_sources()
    print(f"Loaded {len(raw)} files ({sum(len(v) for v in raw.values()):,} chars)\n")

    topics_to_run = WIKI_TOPICS
    if args.topic:
        topics_to_run = [(t, d) for t, d in WIKI_TOPICS if t == args.topic]
        if not topics_to_run:
            print(f"Unknown topic. Valid: {[t for t, _ in WIKI_TOPICS]}")
            return

    sources_text = sources_to_text(raw)
    compiled: dict[str, str] = {}

    for topic, description in topics_to_run:
        wiki_path = config.WIKI_DIR / f"{topic}.md"

        if wiki_path.exists() and not args.force:
            print(f"  skip (exists): {topic}  [--force to recompile]")
            compiled[topic] = wiki_path.read_text(encoding="utf-8")
            continue

        if args.dry_run:
            print(f"  would compile: {topic}")
            continue

        print(f"\n{'─' * 60}\nCompiling: {topic}\n{'─' * 60}")
        article = compile_article(
            client, topic, description, sources_text,
            on_chunk=lambda s: print(s, end="", flush=True),
        )
        print()
        wiki_path.write_text(f"# {topic}\n\n{article}", encoding="utf-8")
        compiled[topic] = article

    if args.dry_run:
        print("\n(dry run — no files written)")
        return

    if compiled:
        index = wiki.build_index(compiled)
        config.INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")
        print(f"\nCompiled {len(compiled)} articles → {config.WIKI_DIR}/")


if __name__ == "__main__":
    main()
