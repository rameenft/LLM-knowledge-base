"""
qa.py
-----
Q&A interface over the compiled wiki knowledge base.
Uses sentence-transformers (local, no API key needed) for embedding-based
retrieval, then Claude Haiku for answer generation.

Usage:
    python qa.py                          # interactive mode
    python qa.py -q "How does crisis detection work?"
    python qa.py --list                   # list wiki articles with link counts
    python qa.py --index                  # rebuild embedding index
"""

import os
import re
import json
import pickle
import argparse
import numpy as np

# Load .env if present
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line.startswith("GOOGLE_API_KEY="):
                os.environ.setdefault("GOOGLE_API_KEY", _line.split("=", 1)[1])

from google import genai
from google.genai import types

WIKI_DIR = os.path.join(os.path.dirname(__file__), "wiki")
INDEX_PATH = os.path.join(WIKI_DIR, "_index.json")
EMBEDDINGS_PATH = os.path.join(WIKI_DIR, "_embeddings.pkl")
EMBED_MODEL = "all-MiniLM-L6-v2"
QA_MODEL = "gemini-2.5-flash"


# ── Embedding utilities ────────────────────────────────────────────────────

def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


def build_embedding_index(articles: dict[str, str], force: bool = False) -> dict:
    """Compute and cache embeddings for all wiki articles."""
    if os.path.exists(EMBEDDINGS_PATH) and not force:
        with open(EMBEDDINGS_PATH, "rb") as f:
            cached = pickle.load(f)
        # Validate cache covers current articles
        if set(cached["topics"]) == set(articles.keys()):
            return cached

    print("Building embedding index...", flush=True)
    embedder = get_embedder()

    topics = list(articles.keys())
    # Embed topic name + first 500 words of article for richer signal
    texts = [f"{t}\n{' '.join(articles[t].split()[:500])}" for t in topics]
    vectors = embedder.encode(texts, show_progress_bar=False, normalize_embeddings=True)

    cache = {"topics": topics, "vectors": vectors}
    with open(EMBEDDINGS_PATH, "wb") as f:
        pickle.dump(cache, f)

    print(f"Indexed {len(topics)} articles.\n")
    return cache


def retrieve_by_embedding(question: str, articles: dict[str, str],
                          top_k: int = 4) -> list[str]:
    """Return top_k article names by cosine similarity to the question."""
    cache = build_embedding_index(articles)
    embedder = get_embedder()

    q_vec = embedder.encode([question], normalize_embeddings=True)[0]
    scores = cache["vectors"] @ q_vec  # cosine sim (vectors are unit-normed)
    ranked_idx = np.argsort(scores)[::-1]

    return [cache["topics"][i] for i in ranked_idx[:top_k]]


# ── Wiki utilities ─────────────────────────────────────────────────────────

def load_wiki() -> dict[str, str]:
    articles = {}
    if not os.path.isdir(WIKI_DIR):
        return articles
    for fname in sorted(os.listdir(WIKI_DIR)):
        if fname.endswith(".md") and not fname.startswith("_"):
            path = os.path.join(WIKI_DIR, fname)
            with open(path, "r", encoding="utf-8") as f:
                articles[fname[:-3]] = f.read()
    return articles


def load_index() -> dict:
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH) as f:
            return json.load(f)
    return {}


def render_wikilinks(text: str, available: set) -> str:
    def replace(m):
        t = m.group(1)
        return f"**{t}**" if t in available else f"*{t}*"
    return re.sub(r"\[\[([^\]]+)\]\]", replace, text)


# ── Answer generation ──────────────────────────────────────────────────────

def get_gemini_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        print("GOOGLE_API_KEY not set.")
        print("Get a free key at https://aistudio.google.com")
        print("Then create project2/.env with:  GOOGLE_API_KEY=your-key-here")
        raise SystemExit(1)
    return genai.Client(api_key=api_key)


def answer_question(question: str, articles: dict[str, str]) -> tuple[str, list[str]]:
    if not articles:
        return "No wiki articles found. Run compile_wiki.py first.", []

    relevant = retrieve_by_embedding(question, articles, top_k=4)

    context = "\n\n".join(
        f"=== {t} ===\n{articles[t]}" for t in relevant
    )

    prompt = f"""You are answering questions using a compiled wiki knowledge base about:
"AI-powered social platform for shared human experiences — mentor-mentee matching,
affective computing, voice dialogue systems, and empathetic AI design."

Relevant wiki articles:
{context}

---

Question: {question}

Instructions:
- Answer using only the wiki content above
- Cite articles you draw from (e.g. "According to AffectiveComputing, ...")
- Synthesize across multiple articles when relevant
- Use bullet points for multi-part answers
- If the wiki doesn't cover the question, say so
- Keep the answer under 300 words"""

    print("\nAnswering", end="", flush=True)
    client = get_gemini_client()
    answer = ""
    for chunk in client.models.generate_content_stream(
        model=QA_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=700, temperature=0.2),
    ):
        if chunk.text:
            answer += chunk.text
            print(".", end="", flush=True)
    print()

    answer = render_wikilinks(answer, set(articles.keys()))
    return answer, relevant


# ── CLI ────────────────────────────────────────────────────────────────────

def interactive_mode(articles: dict[str, str]):
    print("\n" + "=" * 60)
    print("  Knowledge Base Q&A — AI Social Platform Wiki")
    print("=" * 60)
    print(f"  {len(articles)} wiki articles  |  model: {EMBED_MODEL}")
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
            for t in sorted(articles.keys()):
                print(f"  {t}")
            print()
            continue

        answer, sources = answer_question(question, articles)
        print(f"\nAnswer:\n{answer}")
        print(f"\nSources: {', '.join(sources)}\n" + "-" * 50)


def main():
    parser = argparse.ArgumentParser(description="Q&A over compiled wiki")
    parser.add_argument("-q", "--question", help="Ask a single question")
    parser.add_argument("--list", "-l", action="store_true", help="List wiki articles")
    parser.add_argument("--index", action="store_true", help="Rebuild embedding index")
    args = parser.parse_args()

    articles = load_wiki()
    if not articles:
        print("No wiki articles found. Run compile_wiki.py first.")
        return

    if args.index:
        build_embedding_index(articles, force=True)
        return

    if args.list:
        index = load_index()
        print(f"\nWiki Knowledge Base — {len(articles)} articles\n")
        print(f"{'Article':<35} {'Words':>5}  {'Links out/in'}")
        print("-" * 58)
        for t in sorted(articles.keys()):
            m = index.get(t, {})
            wc = m.get("word_count", len(articles[t].split()))
            out = len(m.get("outgoing_links", []))
            inc = len(m.get("incoming_links", []))
            print(f"  {t:<33} {wc:>5}  {out} out / {inc} in")
        return

    if args.question:
        answer, sources = answer_question(args.question, articles)
        print(f"\nQ: {args.question}")
        print(f"\nA:\n{answer}")
        print(f"\nSources: {', '.join(sources)}")
    else:
        interactive_mode(articles)


if __name__ == "__main__":
    main()
