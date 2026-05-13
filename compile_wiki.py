"""
compile_wiki.py
---------------
Reads all raw source notes and uses Gemini 2.0 Flash (free tier) to synthesize
a structured, interlinked wiki knowledge base.

Get a free API key at: https://aistudio.google.com  (no credit card)

The compiler explicitly:
  - Synthesizes across ALL sources, not just one
  - Identifies and resolves contradictions between sources
  - Adds connections and implications that emerge from reading sources together

Usage:
    python compile_wiki.py              # compile all (skip existing)
    python compile_wiki.py --force      # recompile everything
    python compile_wiki.py --topic AffectiveComputing
    python compile_wiki.py --dry-run    # show plan, don't call API
"""

import os
import re
import json
import argparse

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

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
WIKI_DIR = os.path.join(os.path.dirname(__file__), "wiki")
INDEX_PATH = os.path.join(WIKI_DIR, "_index.json")

COMPILE_MODEL = "gemini-2.5-flash"

TOPIC_OVERVIEW = (
    "AI-powered social platform for shared human experiences: "
    "mentor-mentee matching, affective computing, voice-driven dialogue, "
    "and empathetic AI design"
)

WIKI_TOPICS = [
    ("ExperienceMatching",
     "How the platform matches users by shared lived experience: embedding retrieval, "
     "two-stage re-ranking, match explanations, and evaluation"),
    ("AffectiveComputing",
     "Emotion recognition from text and audio, distress detection, emotional trajectory "
     "modeling, and how affect data drives conversation calibration"),
    ("VoiceInterface",
     "STT and TTS pipelines, streaming architecture, latency design, disfluency handling, "
     "and privacy for voice-first interaction"),
    ("DialogueSystem",
     "End-to-end LLM dialogue, conversation state tracking, retrieval-augmented generation, "
     "and policy enforcement for supportive conversations"),
    ("EmpathyDesign",
     "Design principles for empathetic AI: failure modes, prompt engineering, "
     "measuring empathy quality, and cultural variation"),
    ("MentorMenteeSystem",
     "Two-sided matching market, mentor capacity management, onboarding, "
     "cold-start handling, burnout prevention, and evaluation"),
    ("ExperienceStorageRetrieval",
     "Dual representation (structured + vector), pgvector, LLM-based extraction, "
     "versioning, privacy, and feedback loops"),
    ("PlatformArchitecture",
     "Microservices, request flow, latency budget, scaling, and "
     "the continuous improvement feedback loop"),
    ("SafetyAndEscalation",
     "Crisis detection architecture, escalation levels, human moderation, "
     "secondary trauma prevention, and ethical audit cadence"),
    ("KnowledgeBaseDesign",
     "The compilation pipeline, WikiLink graph, embedding retrieval, "
     "what works well, and what to improve"),
]

SYNTHESIS_PROMPT = """\
You are writing a wiki knowledge base on the topic:
"{overview}"

You have read the following raw research notes (written informally, with gaps, \
some redundancy, and occasional contradictions between files):

{sources}

---

Your task: write a comprehensive wiki article on the specific topic: **{topic}**
Topic scope: {description}

The article must do the following — this is where the value of compilation comes from:

1. **Synthesize across multiple raw sources** — do not summarize one source. \
Pull related ideas from different notes and combine them into a coherent picture.

2. **Resolve contradictions** — if the raw notes disagree (e.g., one says keyword \
retrieval is fine, another says it's inadequate), state the tension clearly and \
explain which view is better supported or under what conditions each applies.

3. **Surface cross-source implications** — identify connections and conclusions \
that are implied by reading multiple notes together but are not stated explicitly \
in any single one. These emergent insights are the most valuable part of the wiki.

4. **Use clear structure**:
   - Start directly with content (no "Introduction" section)
   - ## Key Concepts: 4-6 bullet definitions of the most important terms
   - ## How It Works: the main technical/design content
   - ## Design Implications: 3-5 actionable takeaways for a builder
   - ## Open Questions: 2-3 genuine tensions or unresolved issues from the notes
   - ## See Also: [[WikiLink]] references to 3-5 related wiki topics

5. **Use [[WikiLink]] format** to reference other wiki topics from this list: \
{other_topics}
   Embed links naturally in the text, not just in See Also.

6. Keep the article **600-900 words** — detailed enough to be useful, short enough \
to be readable.

Write the article now. Start immediately with the first section heading."""


def load_raw_sources() -> dict[str, str]:
    sources = {}
    for fname in sorted(os.listdir(RAW_DIR)):
        if fname.endswith(".md"):
            with open(os.path.join(RAW_DIR, fname), encoding="utf-8") as f:
                sources[fname] = f.read()
    return sources


def sources_to_text(sources: dict[str, str]) -> str:
    return "\n\n".join(
        f"=== {fname} ===\n{content}" for fname, content in sources.items()
    )


def compile_article(client: genai.Client, topic: str, description: str,
                    sources_text: str) -> str:
    other_topics = [t for t, _ in WIKI_TOPICS if t != topic]
    prompt = SYNTHESIS_PROMPT.format(
        overview=TOPIC_OVERVIEW,
        sources=sources_text,
        topic=topic,
        description=description,
        other_topics=", ".join(other_topics),
    )

    print(f"\n{'─'*60}")
    print(f"Compiling: {topic}")
    print(f"{'─'*60}")

    full = ""
    for chunk in client.models.generate_content_stream(
        model=COMPILE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=2500,
            temperature=0.4,
        ),
    ):
        if chunk.text:
            full += chunk.text
            print(chunk.text, end="", flush=True)

    print()
    return full


def extract_wikilinks(text: str) -> list[str]:
    return re.findall(r"\[\[([^\]]+)\]\]", text)


def build_index(articles: dict[str, str]) -> dict:
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
        index[topic]["incoming_links"] = [
            t for t, m in index.items()
            if topic in m["outgoing_links"] and t != topic
        ]
    return index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--topic")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    os.makedirs(WIKI_DIR, exist_ok=True)

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key and not args.dry_run:
        print("GOOGLE_API_KEY not set.")
        print("Get a free key at https://aistudio.google.com")
        print("Then create project2/.env with:  GOOGLE_API_KEY=your-key-here")
        return

    print(f"Loading raw sources from {RAW_DIR}/")
    raw = load_raw_sources()
    print(f"Loaded {len(raw)} files ({sum(len(v) for v in raw.values()):,} chars)\n")

    topics_to_run = WIKI_TOPICS
    if args.topic:
        topics_to_run = [(t, d) for t, d in WIKI_TOPICS if t == args.topic]
        if not topics_to_run:
            print(f"Unknown topic. Valid: {[t for t,_ in WIKI_TOPICS]}")
            return

    sources_text = sources_to_text(raw)
    compiled: dict[str, str] = {}

    client = genai.Client(api_key=api_key) if not args.dry_run else None

    for topic, description in topics_to_run:
        wiki_path = os.path.join(WIKI_DIR, f"{topic}.md")

        if os.path.exists(wiki_path) and not args.force:
            print(f"  skip (exists): {topic}  [--force to recompile]")
            with open(wiki_path, encoding="utf-8") as f:
                compiled[topic] = f.read()
            continue

        if args.dry_run:
            print(f"  would compile: {topic}")
            continue

        article = compile_article(client, topic, description, sources_text)
        with open(wiki_path, "w", encoding="utf-8") as f:
            f.write(f"# {topic}\n\n{article}")
        compiled[topic] = article

    if args.dry_run:
        print("\n(dry run — no files written)")
        return

    if compiled:
        index = build_index(compiled)
        with open(INDEX_PATH, "w") as f:
            json.dump(index, f, indent=2)

        print(f"\n{'='*60}")
        print(f"Compiled {len(compiled)} articles → {WIKI_DIR}/")
        print(f"\n{'Article':<35} {'Words':>5}  {'Out':>4}  {'In':>4}")
        print("-" * 52)
        for t, m in sorted(index.items()):
            print(f"  {t:<33} {m['word_count']:>5}  "
                  f"{len(m['outgoing_links']):>4}  {len(m['incoming_links']):>4}")


if __name__ == "__main__":
    main()
