# dialogue system notes

the hard part of dialogue is not generating good responses to isolated messages — it's maintaining coherence across many turns, tracking what the conversation is trying to accomplish, and knowing when to push forward vs let silence breathe.

in emotionally sensitive conversations this is all harder. misreading intent or responding too fast can break trust in a way that's hard to recover from.

---

two main architectures:

pipeline (classic): ASR → NLU (intent + entity extraction) → dialogue manager (state machine) → NLG → TTS. modular, each component improvable. but error propagation is brutal — one wrong intent classification cascades. and the state machine gets rigid fast.

end-to-end neural (modern): single LLM handles everything. conversation history in context, response generated directly. no explicit state machine — context managed implicitly in attention. chatgpt/claude/gemini all work this way. much more flexible, handles novel situations gracefully. but less controllable, harder to enforce specific behaviors.

we're going end-to-end for flexibility, but with explicit state tracking injected via system prompt to get the best of both.

---

state tracking. even in end-to-end systems, explicit state helps. track:
- user's primary experience (extracted at onboarding, updated over time)
- current emotional state (from affect classifier)
- conversation goal: narrative exploration? active mentor search? crisis support?
- outstanding questions (what has the user asked that hasn't been answered?)
- turn count + session metadata

store this in redis, inject as structured context in the system prompt each turn. LLM gets both the raw conversation history AND the structured state. much more reliable than hoping the model remembers everything from turn 1.

---

retrieval augmented generation. the dialogue system integrates retrieval from the experience corpus. before generating a response:
- if conversation_goal = mentor_search: fetch top candidate profiles from pgvector
- if conversation_goal = resource_seeking: fetch relevant articles
- inject into context as "Retrieved context:" block

this prevents fabricated mentor experiences. responses are grounded in real matched profiles.

---

conversation policies. the dialogue manager enforces these through system prompt instructions (not a state machine):

validation-first: before any information or action, validate the user's emotional experience. this is rule 1.
one question per turn: never ask multiple questions at once. too overwhelming.
reflect before advise: summarize what you've heard before offering any perspective.
pacing control: if user is sharing something heavy, don't pivot immediately. equivalent of "take your time."
graceful uncertainty: if the system doesn't know, say so. "I don't have enough information to suggest a mentor yet — can you tell me more about..."

---

context window management. for very long sessions:
- rolling window: keep last N turns
- summarization: compress older turns into a running summary
- memory extraction: pull key facts (name, experience, outstanding topics) into structured memory injected each turn

claude's 1M context means this is less urgent than for GPT-4 based systems, but structured memory injection still improves coherence even at shorter context lengths.

---

eval metrics for dialogue:
- task completion rate (did they find a mentor / get what they needed?)
- conversation coherence (human judges 1-5)
- empathy score (classifier or human)
- turns to task completion
- user satisfaction (NPS or likert post-session)

DO NOT use BLEU/ROUGE for dialogue evaluation. they measure n-gram overlap. they're terrible for this. you can generate a perfectly empathetic response that shares 0 words with a reference response.
