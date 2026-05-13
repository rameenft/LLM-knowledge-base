# karpathy KB notes

karpathy's idea: use an LLM not as a Q&A oracle but as a curator/connector. the LLM reads your raw notes (which are messy, fragmented, redundant) and synthesizes them into structured wiki articles with cross-links. then Q&A runs against the wiki, not the raw notes.

key insight: the compilation step adds value that the raw sources don't have. it resolves contradictions, adds structure, creates connections across notes that you wrote separately, and distills key concepts. the wiki is better than the sum of its parts.

---

architecture:
raw/ (messy notes) → compile_wiki.py (LLM) → wiki/ (structured articles) → qa.py (retrieval + LLM) → answers

the three components:

1. compile_wiki.py: reads ALL raw sources in a single context window (1M tokens means the whole raw/ fits easily). for each concept, asks the LLM to synthesize a wiki article. articles use [[WikiLink]] format to cross-reference other articles.

2. wiki/: output of compilation. one .md file per concept. articles include Key Concepts section, Design Implications, See Also with wikilinks.

3. qa.py: user asks a question. system retrieves the most relevant wiki articles (by keyword overlap OR embedding similarity). injects retrieved content into LLM context. LLM answers with citations.

---

what makes this better than just asking the LLM about the topic directly?

- grounded: answers are constrained to what's in your actual notes/sources, not the LLM's training data
- structured: the wiki adds organization that makes answers more reliable
- updatable: add new raw sources, recompile affected articles, Q&A improves
- auditable: you can trace every answer back to specific wiki articles and then to specific raw sources

---

the compilation step needs careful prompting:

bad prompt: "summarize this document"
→ you get summaries that are just paraphrases of individual raw sources

good prompt: "you have read ALL of the following notes. synthesize a wiki article on [topic] that:
- draws from multiple sources, not just one
- resolves any contradictions you find between sources
- adds connections and implications that are suggested by multiple sources together but not stated in any single one
- uses [[WikiLink]] format to reference related topics"

the key is "resolves contradictions" and "adds connections implied by multiple sources." this is where the LLM actually adds value beyond reformatting.

---

retrieval options:

keyword (simple, no API): works fine for small wikis (< 20 articles). fails on semantic mismatches ("how does the system detect sadness" doesn't match "AffectiveComputing" by keyword).

embedding similarity (better): embed each wiki article, embed the query, cosine similarity. sentence-transformers (local, free, no API) works well. models like all-MiniLM-L6-v2 are 80MB and run in <50ms on CPU.

LLM-as-retriever: ask the LLM "which of these article topics is most relevant to this question?" — surprisingly effective, but costs an extra API call per query.

for production: embedding similarity. for prototype: keyword is fine to start.

---

gaps / things i want to improve:
- multi-hop retrieval: Q&A currently retrieves top-k articles but doesn't follow wikilinks to transitively relevant articles. "how does affective computing improve mentor matching over time?" needs both AffectiveComputing AND ExperienceMatching AND MentorMenteeSystem
- incremental compilation: currently need to recompile everything on any change. should detect which articles are affected by a new/changed raw source and only recompile those
- web UI for wikilink navigation: rendering [[WikiLink]] as bold text is fine for a prototype. a real UI would make them clickable
- evaluation: need a proper eval set — questions with ground-truth answers derivable from raw sources — to measure accuracy and hallucination rate
