# storage and retrieval notes

the central technical problem: representing "lived experience" in a machine-readable form that supports fast semantic similarity search.

two representations for every experience, used together:
1. structured record (JSON, machine-filterable fields for hard constraints)
2. embedding vector (dense, semantic, for approximate nearest-neighbor search)

never just embeddings alone — you need the structured fields for filtering (is this mentor available? do they have capacity? are they in the right category?). never just structured fields alone — they lose all the nuance.

---

structured record schema (rough):
```json
{
  "experience_id": "exp_7291",
  "user_id": "u_4812",
  "category": "health",
  "subcategory": "cancer",
  "specificity": "breast cancer, stage 2",
  "time_since_onset_months": 30,
  "duration_months": 8,
  "current_status": "in_remission",
  "emotional_texture": ["fear", "isolation", "relief"],
  "outcome": "positive",
  "open_to_mentoring": true
}
```

the emotional_texture field is interesting — it captures something the category fields can't. two people with "breast cancer, stage 2" can have very different emotional journeys. the texture field enables texture-based matching in addition to experience-category matching.

---

LLM extraction pipeline:
user narrative (text or STT transcript) → LLM extraction prompt → structured JSON → embedding computation → insert into postgres + pgvector

edge cases:
- ambiguous timelines ("a few years ago") → store null, flag for follow-up
- multiple simultaneous experiences → multi-experience record with primary/secondary
- ongoing experiences → outcome = "ongoing", time_since_onset updates on each session

---

pgvector:
postgres extension, stores dense vectors, HNSW index for sub-millisecond approximate nearest-neighbor. supports online insertions. at 100k users × 3 experiences each = 300k records, handles ~1000 QPS at <5ms P99.

query flow:
new user embedding → HNSW ANN search → top-100 candidates → SQL filter (availability, category, capacity) → LLM re-ranking top-20 → return top-5 with explanations

the LLM re-ranking step is where the match explanation is generated. this is important — users accept matches more when they understand why the match was made.

---

experience evolution — experiences change. a person 3 months into unemployment vs 18 months later is different. handle this with:
- versioned records (each update creates new version, old retained for trajectory analysis)
- temporal weighting (more recent versions weighted higher in similarity scores)
- status transitions: active → graduated → mentor-ready

the versioning feeds back into the affect trajectory analysis (see affective computing notes) — you can track how the user's experience description changes over time, which itself is a wellbeing signal.

---

privacy:
- raw narrative text NEVER transmitted to other users, only LLM-generated summaries with consent
- candidate lists use anonymized user IDs until mutual match acceptance
- selective matchability: users can mark individual experiences "not matchable"
- right-to-deletion: records and embeddings purged within 24h on request (GDPR/CCPA)
- audit log: every retrieval query logged (timestamp, querying user, candidates returned)

---

implementation note: if we ever update the embedding model (e.g., switch from ada-002 to text-embedding-3-large), ALL existing embeddings need recomputation. this is expensive. design the schema with a model_version field so you can do incremental migration.
