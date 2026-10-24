"""Retrieval-augmented answering with Gemini. Returns data; never prints or exits."""

from dataclasses import dataclass, field

from google import genai
from google.genai import types

from . import config, retrieval, wiki

ANSWER_PROMPT = """You are answering questions using a compiled wiki knowledge base about:
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


@dataclass
class Answer:
    text: str
    sources: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)


def build_prompt(question: str, articles: dict[str, str], topics: list[str]) -> str:
    context = "\n\n".join(f"=== {t} ===\n{articles[t]}" for t in topics)
    return ANSWER_PROMPT.format(context=context, question=question)


def get_client() -> genai.Client:
    return genai.Client(api_key=config.get_google_api_key())


def generate_text(client, prompt: str, on_chunk=None) -> str:
    """Stream a Gemini response. `on_chunk` lets a CLI show progress; services ignore it."""
    text = ""
    for chunk in client.models.generate_content_stream(
        model=config.QA_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=700, temperature=0.2),
    ):
        if chunk.text:
            text += chunk.text
            if on_chunk:
                on_chunk(chunk.text)
    return text


def answer_from_hits(
    question: str,
    articles: dict[str, str],
    hits: list[tuple[str, float]],
    client=None,
    on_chunk=None,
) -> Answer:
    """Generate a cited answer from already-retrieved (topic, score) hits."""
    topics = [t for t, _ in hits]
    client = client or get_client()
    text = generate_text(client, build_prompt(question, articles, topics), on_chunk)
    return Answer(
        text=wiki.render_wikilinks(text, set(articles)),
        sources=topics,
        scores=dict(hits),
    )


def answer_question(
    question: str,
    articles: dict[str, str],
    client=None,
    embedder: retrieval.Embedder = retrieval.default_embedder,
    top_k: int = 4,
    on_chunk=None,
) -> Answer:
    if not articles:
        raise ValueError("No wiki articles found. Run compile_wiki.py first.")
    hits = retrieval.retrieve(question, articles, top_k=top_k, embedder=embedder)
    return answer_from_hits(question, articles, hits, client=client, on_chunk=on_chunk)
