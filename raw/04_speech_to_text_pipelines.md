# STT notes

voice is the right modality for this platform. typing a coherent narrative about grief or illness is genuinely hard. voice is faster, more natural, more emotionally expressive. if we want to serve people who are in the middle of something hard, we need to meet them where they are.

---

main STT systems i've looked at:

whisper (openai, open source): trained on 680k hours of multilingual audio. models from tiny (39M params) to large-v3 (1.5B). handles accented speech and noisy environments well. no native streaming in the base implementation — WhisperX adds alignment. good for offline transcription of pre-recorded narratives. free to run locally.

google speech-to-text: ~300ms latency for real-time streaming. speaker diarization (who said what). medical model for clinical terminology. good for real-time conversation transcription. not free.

assemblyai: transcription + sentiment + topic detection + auto-chapters in one API call. speaker labels in real-time. probably the fastest path to a prototype.

deepgram nova-2: 2-5x faster than real-time. strong on spontaneous speech and conversational register. SDKs in python, node, go.

for prototype: probably assemblyai or deepgram. for production at scale with privacy requirements: whisper running locally (no data leaves device).

---

disfluency handling is important and subtle.

raw speech has: filler words (um, uh, like), false starts ("I was — I mean —"), repetitions ("and then and then"), emotional breaks (crying, laughter, long silences).

for most downstream NLP: remove disfluencies.
for affect analysis: KEEP THEM. they're signal.
- high filler word rate → cognitive load, uncertainty
- false starts → emotionally difficult topic
- long silences → grief, trauma processing, searching for words

so we need dual output: raw transcript (for affect) + cleaned transcript (for NLP/matching).

---

real-time streaming architecture:

client sends audio chunks via websocket (~100ms segments)
partial transcripts returned after each chunk
final transcript at end-of-utterance (VAD detects silence)
parallel: audio sent to affective feature extractor

latency targets:
- VAD to first word: <500ms
- end-of-utterance to final transcript: <300ms
- transcript to AI response generation start: <200ms
- total: user speaks → hears response < 2 seconds

streaming is non-negotiable for the latency budget.

---

privacy: audio is a biometric identifier. voice uniquely identifies a person.
- never store raw audio beyond the session
- on-device whisper (tiny/base) for max privacy — nothing leaves the device
- transcripts stored without audio linkage
- explicit user consent for any audio analysis beyond transcription

this is actually a strong product differentiator — "your audio never leaves your device" is a genuine privacy story for a sensitive platform.

---

multilingual: whisper large-v3 handles 99 languages. language detection before transcription improves model selection. this matters — the user base will be global.
