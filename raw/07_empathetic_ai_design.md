# empathy design notes

important distinction that i keep coming back to: true empathy (the felt experience of another's emotion) is not accessible to AI. what AI systems can produce is FUNCTIONAL empathy — responses that are perceived as empathetic by humans. this distinction matters for how you design the system and for what you promise users.

---

functional empathy requires:
1. accurate recognition of emotional state (see affective computing notes)
2. appropriate acknowledgment — naming the emotion without projecting
3. non-judgmental stance — no implicit evaluation of feelings or choices
4. perspective-taking language — "it makes sense that you'd feel..." NOT "you shouldn't feel..."
5. repair on misunderstanding — gracefully correcting when the system misreads

---

the biggest failure mode: premature advice-giving.

when a user shares a problem, AI systems trained on Q&A data default to solutions. this is almost always wrong in emotional support contexts. burleson (2003) is the key reference — acknowledgment and validation MUST come before advice. advice should only come if explicitly requested.

"I just found out I have cancer" → responding with "here are resources about treatment options" is experienced as cold and dehumanizing, even if the resources are accurate and helpful.

design principle: advice is never the first response. first: validate. second: ask what kind of support the user wants. advice (if given at all) is framed as options, not prescriptions.

---

other failure modes:

generic validation: "that sounds really hard. i'm sorry you're going through this." — fine once, reads as formulaic by the third time. prevention: vary acknowledgment language; reference specific details the user shared.

toxic positivity: "but think about the positive things in your life!" — actively harmful. makes people feel unheard and judged. explicit prohibition in system prompt.

over-identification: "i totally understand how you feel." — AI cannot understand how someone feels. use "it sounds like..." or "from what you're describing..."

therapist creep: AI gradually acting more like a therapist than a peer companion. need hard boundary in system prompt + periodic audit of conversation patterns.

---

prompt engineering pattern for this:

```
When the user shares something difficult:
1. Acknowledge their specific feelings (not generic).
2. Validate the reasonableness of their reaction.
3. Ask ONE open-ended question that invites elaboration.
4. Do NOT offer advice unless explicitly asked.
5. Never minimize ("at least..."), project ("you must be..."), or pivot to optimism.
6. Mirror their language register.
```

---

appropriate AI self-disclosure. research on peer support shows mentor self-disclosure increases perceived empathy. for an AI:
- don't claim human experiences (dishonest)
- CAN reference the platform's experience corpus: "many people in our community who've gone through this describe feeling completely isolated at first..."
- grounds empathy in real human experience without fabrication

---

measuring empathy quality:
- automated classifier (trained on counselor-annotated transcripts): empathic concern scale adaptation, rates each AI turn 1-5
- user surveys: "did you feel heard?" (binary) + 5-point quality rating. target: >85% yes, >4.0 rating
- human evaluation: monthly sample of 200 transcripts, trained annotators
- return rate as proxy: users who felt heard return. single-session dropout signals empathy failure.

one thing i'm not sure about: how do we handle cultural variation in empathetic expression? some cultures find explicit validation too direct. others find indirect acknowledgment cold. this is an open research problem and probably needs targeted fine-tuning or cultural calibration per user population.
