# matching system notes

gale-shapley stable marriage — the theoretical foundation. two-sided market where both mentor and mentee have to accept. practically, stable matching is too strict — we'd rather optimize for expected engagement than strict stability. but the framing is useful.

---

what features matter for a good match?

temporal: when did the experience happen? someone 2 years past a diagnosis is more useful to a newly diagnosed person than someone 15 years past. the recency of the experience matters a lot.

severity and duration: 3-month job loss vs 2-year unemployment are really different experiences. we need to capture magnitude somehow.

emotional texture: was the experience primarily isolating? chaotic? grief-filled? matching on emotional texture might surface empathetic resonance that category matching misses. like, two people who both describe their experience as "totally isolating and no one understood" might connect better than two people who share a diagnosis but processed it differently.

outcome: did things get better? still ongoing? the person whose divorce resolved positively has different things to offer than someone still in it. should we match people by trajectory/status too?

---

embedding approach:
1. user writes/speaks their experience narrative
2. STT transcription if voice input
3. LLM embeds the narrative
4. nearest neighbor search in embedding space (FAISS or pgvector)
5. return candidate pool

problem: embeddings are opaque. the match seems good but you can't explain why. users distrust recommendations they don't understand, especially in sensitive contexts.

better approach: hybrid. fast embedding retrieval for top-100 candidates, then slower re-ranking with LLM that generates an explanation. the explanation is then shown to both parties. this increases acceptance rate dramatically (anecdotally — need to find a study on this).

---

cold start is a real problem. new users have no narrative. options:
- structured onboarding interview → synthetic narrative
- collaborative filtering fallback on demographics until behavioral data builds up
- progressive disclosure — let them add experience over time, matches improve

my instinct: the onboarding interview is important for the product anyway (it's the moment where the user feels heard for the first time), so lean into it. make the interview itself the value, not just a means to an end.

---

mentor capacity: max 3 active mentees. this is roughly what i see in peer support literature — more than that and quality degrades. need a real cap, not just a soft recommendation.

burnout is underappreciated. mentors are volunteers. if they're overwhelmed they just disappear. need:
- hard capacity limit
- automated check-ins ("how are you feeling about this relationship?")
- structured off-ramps
- mentor-only community (so helpers have their own support)

---

eval metrics:
- match acceptance rate (target >60%)
- first message within 48h
- still talking at 4 weeks (>40%)
- mentee helpfulness score (>4.0/5)
- mentor satisfaction monthly

note: these metrics conflict sometimes. optimizing pure acceptance rate could mean showing easy/obvious matches that don't actually lead to lasting relationships. need to weight long-term retention more.
