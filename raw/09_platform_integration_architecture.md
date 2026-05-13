# system architecture braindump

six subsystems that need to talk to each other:
1. voice interface (STT + TTS)
2. AI mediator (LLM dialogue)
3. experience storage/retrieval (pgvector)
4. matching engine (embedding sim + reranking)
5. affective computing (emotion classification)
6. safety/escalation (crisis detection + human moderation)

the challenge is integrating these without the latency budget blowing up. everything needs to either be parallel or very fast.

---

services breakdown:

voice-service: STT + TTS. websocket connections for audio streaming. stateless compute.
dialogue-service: LLM conversation (claude). calls experience-service and match-service to get context before generating response.
affect-service: runs emotion classifier + distress detector on each utterance. parallel to dialogue-service, not blocking.
experience-service: LLM extraction, embedding computation, pgvector queries.
match-service: candidate retrieval + LLM re-ranking + explanation generation.
safety-service: crisis detection (fast lexical + neural), escalation routing, audit logging.

data layer: postgres + pgvector (experiences, profiles), redis (session state, affect scores, 2h TTL), S3 (transcript archives, 30d then delete).

---

request flow for a voice conversation turn:
1. user speaks → websocket audio stream → voice-service
2. VAD detects end of utterance → STT produces transcript
3. PARALLEL: affect-service classifies audio + text
4. dialogue-service retrieves session state from redis
5. if mentor_search goal: match-service fetches candidates from pgvector
6. dialogue-service calls claude API (context = session state + retrieved context + conversation history)
7. LLM response streams → TTS begins on first sentence
8. audio streams to client
9. session state updated in redis; affect score appended to trajectory

steps 3 and 4-6 should be parallel. affective scoring doesn't block dialogue generation.

---

latency budget:

VAD end-of-speech: 200ms
STT transcription: 300ms
LLM first token: 500ms
TTS first chunk: 300ms
audio delivery: 100ms
TOTAL: ~1.4 seconds

this is achievable with streaming at every stage. non-streaming approaches will blow this budget easily.

---

scaling notes:

LLM calls are the bottleneck. strategy: haiku for classification tasks (affect, intent), opus for dialogue generation (quality matters there). don't use opus for everything.

pgvector + HNSW at 300k records: handles 1000 QPS fine. this is not the bottleneck.

websocket connections at 10k concurrent: need careful connection pooling and horizontal scaling of voice-service. this IS a scaling challenge.

all services should be stateless (state in redis/postgres). horizontal scaling is then straightforward.

---

continuous improvement loop:
user interactions → match ratings + conversation ratings + session completions
→ nightly pipeline:
  - poor matches → experience extraction quality review
  - good matches → positive training examples for re-ranker
  - affect trajectory analysis → update response policies  
  - crisis escalation review → threshold calibration

this is what turns a system that was good at launch into one that gets better over time. don't skip this.

---

ethical review cadence:
- quarterly matching audit (demographic bias in match assignments)
- monthly affect accuracy audit (200-sample human review)
- daily safety log review (automated + weekly human)
- annual security/data handling audit (third party)

these aren't optional. for a platform serving vulnerable populations, this is table stakes.
