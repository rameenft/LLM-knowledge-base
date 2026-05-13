# affective computing reading notes

picard 1997 — the original paper. basic claim: systems that recognize, interpret, process, simulate affect. three capabilities: recognition, modeling, generation. the generation piece is what's hard — you can classify emotion reasonably well now but generating emotionally calibrated responses without it feeling fake is still an open problem.

---

modalities for recognition:

text: sentiment analysis (positive/negative/neutral), emotion classification (joy/sadness/anger/fear/surprise/disgust — Ekman's 6, though there's debate about whether this list is right), distress signals (crisis language). 

main models right now: GoEmotions (google, 2020) — 27 emotion categories trained on reddit. EmoRoBERTa. VADER is older but still used for fast rule-based stuff.

voice/audio: prosody (pitch, speech rate, pausing), volume dynamics, voice quality (trembling = anxiety). acoustic features: MFCCs, zero-crossing rate. 

multimodal: combining text + audio is more accurate than either alone. audio catches what text misses — sarcasm, masked distress. someone can type "I'm fine" in a completely flat, robotic way that the text classifier misses but the audio catches.

---

for this platform specifically, the useful signals are:

distress score (0-1): feeds directly into the safety/escalation system. need a conservative threshold — false positives (unnecessary intervention) are MUCH better than false negatives (missing someone in crisis).

engagement quality: is this conversation going well? if both parties seem engaged and positive, the match is working. if one or both seem checked out, maybe suggest a check-in.

affect trajectory: tracking emotional state across MULTIPLE sessions is the interesting signal. is the mentee getting more positive over time? that's match quality. are they stuck in the same register? intervention signal.

---

the trajectory idea is underexplored. most affect systems give you a point-in-time score. but for a support platform what you really care about is trend. a mentee who's been "anxious-high" for 3 sessions in a row with the same mentor is different from one who's trending from "anxious-high" to "hopeful-medium" over 3 sessions.

this also feeds back into matching quality — mentors who consistently produce positive trajectory shifts in their mentees should be surfaced more. natural quality signal that doesn't require explicit rating.

---

ethical issues:
- consent: users may not know their emotional state is being classified
- accuracy disparities: models trained on majority populations perform worse for minority groups and culturally specific expression. GoEmotions is US-English Reddit. not representative.
- manipulation risk: knowing someone's emotional state gives you disproportionate influence. must constrain to supportive use only, never persuasive/commercial.
- data sensitivity: emotional state data is among the most sensitive personal data imaginable. access controls must be extremely tight.

TODO: look into whether there are affect datasets that are more culturally diverse. might be worth fine-tuning on a more representative corpus.
