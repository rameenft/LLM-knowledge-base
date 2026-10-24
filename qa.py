"""
qa.py
-----
CLI wrapper around kb.answer: local embedding retrieval, then Gemini answer generation.

Usage:
    python qa.py                          # interactive mode
    python qa.py -q "How does crisis detection work?"
    python qa.py --list                   # list wiki articles with link counts
    python qa.py --index                  # rebuild embedding index
"""

import argparse

from kb import config, retrieval, wiki
from kb.answer import answer_question


def ask(question: str, articles: dict[str, str]):
    print("\nAnswering", end="", flush=True)
    try:
        result = answer_question(
            question, articles, on_chunk=lambda _: print(".", end="", flush=True)
        )
    except config.ConfigError as e:
        print(f"\n{e}\nGet a free key at https://aistudio.google.com")
        raise SystemExit(1)
    print()
    return result


def interactive_mode(articles: dict[str, str]):
    print("\n" + "=" * 60)
    print("  Knowledge Base Q&A — AI Social Platform Wiki")
    print("=" * 60)
    print(f"  {len(articles)} wiki articles  |  model: {config.EMBED_MODEL}")
    print("  Commands: 'list', 'quit'  |  Just type any question\n")

    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            break
        if question.lower() == "list":
            for t in sorted(articles):
                print(f"  {t}")
            print()
            continue

        result = ask(question, articles)
        print(f"\nAnswer:\n{result.text}")
        print(f"\nSources: {', '.join(result.sources)}\n" + "-" * 50)


def main():
    parser = argparse.ArgumentParser(description="Q&A over compiled wiki")
    parser.add_argument("-q", "--question", help="Ask a single question")
    parser.add_argument("--list", "-l", action="store_true", help="List wiki articles")
    parser.add_argument("--index", action="store_true", help="Rebuild embedding index")
    args = parser.parse_args()

    articles = wiki.load_wiki()
    if not articles:
        print("No wiki articles found. Run compile_wiki.py first.")
        return

    if args.index:
        retrieval.build_embedding_index(articles, force=True)
        print(f"Indexed {len(articles)} articles.")
        return

    if args.list:
        index = wiki.load_index()
        print(f"\nWiki Knowledge Base — {len(articles)} articles\n")
        print(f"{'Article':<35} {'Words':>5}  {'Links out/in'}")
        print("-" * 58)
        for t in sorted(articles):
            m = index.get(t, {})
            wc = m.get("word_count", len(articles[t].split()))
            print(f"  {t:<33} {wc:>5}  "
                  f"{len(m.get('outgoing_links', []))} out / "
                  f"{len(m.get('incoming_links', []))} in")
        return

    if args.question:
        result = ask(args.question, articles)
        print(f"\nQ: {args.question}\n\nA:\n{result.text}")
        print(f"\nSources: {', '.join(result.sources)}")
    else:
        interactive_mode(articles)


if __name__ == "__main__":
    main()
