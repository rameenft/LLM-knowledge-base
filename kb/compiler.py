"""LLM wiki compiler: raw notes -> synthesized wiki articles."""

from pathlib import Path

from google.genai import types

from . import config

COMPILE_MODEL = config.COMPILE_MODEL

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


def load_raw_sources(raw_dir: Path | None = None) -> dict[str, str]:
    raw_dir = Path(raw_dir or config.RAW_DIR)
    return {
        p.name: p.read_text(encoding="utf-8") for p in sorted(raw_dir.glob("*.md"))
    }


def sources_to_text(sources: dict[str, str]) -> str:
    return "\n\n".join(f"=== {name} ===\n{content}" for name, content in sources.items())


def build_prompt(topic: str, description: str, sources_text: str) -> str:
    return SYNTHESIS_PROMPT.format(
        overview=TOPIC_OVERVIEW,
        sources=sources_text,
        topic=topic,
        description=description,
        other_topics=", ".join(t for t, _ in WIKI_TOPICS if t != topic),
    )


def compile_article(client, topic: str, description: str, sources_text: str,
                    on_chunk=None) -> str:
    full = ""
    for chunk in client.models.generate_content_stream(
        model=COMPILE_MODEL,
        contents=build_prompt(topic, description, sources_text),
        config=types.GenerateContentConfig(max_output_tokens=2500, temperature=0.4),
    ):
        if chunk.text:
            full += chunk.text
            if on_chunk:
                on_chunk(chunk.text)
    return full
