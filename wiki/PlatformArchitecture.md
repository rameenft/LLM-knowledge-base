# PlatformArchitecture

## Platform Architecture

The platform's architecture is designed to support real-time, empathetic, and privacy-preserving interactions for users sharing sensitive experiences. It leverages a microservices approach to manage complexity, optimize for low latency, and enable continuous improvement.

### Key Concepts

*   **Microservices Architecture**: A design pattern where the application is structured as a collection of loosely coupled, independently deployable services, each responsible for a specific function.
*   **Streaming Pipeline**: A sequence of processing steps where data (e.g., audio, text) is processed in small, continuous chunks rather than waiting for the entire input, crucial for low-latency real-time interactions.
*   **Latency Budget**: The maximum allowable delay for a specific operation or end-to-end user interaction, critical for natural conversation flow.
*   **Stateless Services**: Services that do not store session-specific data internally, allowing for easy horizontal scaling and resilience.
*   **Continuous Improvement Loop**: An iterative process where user interactions, feedback, and performance metrics feed back into the system to refine models, policies, and overall quality.

### How It Works

The platform integrates six core subsystems to deliver its functionality: the [[VoiceInterface]], [[DialogueSystem]], [[AffectiveComputing]] module, [[ExperienceStorageRetrieval]] service, [[ExperienceMatching]] engine, and [[SafetyAndEscalation]] system. These are implemented as distinct, horizontally scalable microservices:

1.  **Voice-Service**: Handles the [[VoiceInterface]], managing real-time audio streaming via WebSockets. It performs Speech-to-Text (STT) transcription (e.g., using Whisper for privacy or cloud providers for advanced features) and Text-to-Speech (TTS) synthesis, ensuring a natural and emotionally appropriate voice persona (e.g., using ElevenLabs or Azure TTS with SSML for prosody control). It produces both raw transcripts (for affect analysis) and cleaned transcripts (for NLP).
2.  **Dialogue-Service**: Orchestrates the [[DialogueSystem]], primarily driven by a large language model (LLM, such as Claude Opus for quality). It manages conversation flow, maintains explicit session state (retrieved from Redis), and integrates context from other services (e.g., retrieved experiences, match candidates) before generating responses.
3.  **Affect-Service**: Operates in parallel to the dialogue system, performing [[AffectiveComputing]]. It classifies emotional state, distress levels, and engagement quality from both audio (prosody, volume) and text (sentiment, emotion classification) modalities. This service is non-blocking, feeding affect scores and trajectory data into session state.
4.  **Experience-Service**: Manages the [[ExperienceStorageRetrieval]]. It uses LLMs to extract structured data (e.g., category, emotional texture, time since onset) from user narratives and computes embedding vectors. These are stored in Postgres with `pgvector` for efficient semantic similarity search.
5.  **Match-Service**: Implements the [[ExperienceMatching]] engine. It performs fast approximate nearest-neighbor searches in the embedding space (e.g., using HNSW indexes in `pgvector`) to find initial candidate mentors. A subsequent LLM re-ranking step refines these candidates and generates transparent explanations for why a match is suggested, significantly increasing user acceptance.
6.  **Safety-Service**: Monitors for crisis signals using fast lexical and neural detection methods, feeding into the [[SafetyAndEscalation]] protocols. It ensures conservative thresholds for intervention, prioritizing false positives over false negatives, and maintains comprehensive audit logs.

The data layer consists of Postgres with `pgvector` for persistent storage of experiences and user profiles, Redis for transient session state and affect scores (with short TTLs), and S3 for temporary transcript archives.

**Request Flow for a Voice Conversation Turn:**
1.  User speaks, audio streams via WebSocket to the **voice-service**.
2.  Voice Activity Detection (VAD) signals end-of-utterance; STT produces a transcript.
3.  **PARALLEL**: The **affect-service** classifies audio and text for emotional state and distress.
4.  The **dialogue-service** retrieves current session state from Redis.
5.  If the conversation goal is mentor search, the **match-service** fetches candidate profiles from `pgvector` and performs LLM re-ranking.
6.  The **dialogue-service** sends the conversation history, structured session state, and any retrieved context (e.g., match explanations) to the LLM.
7.  The LLM's response streams back to the **voice-service**, which begins TTS synthesis on the first sentence.
8.  Audio streams to the client, allowing for barge-in (user interruption).
9.  Session state in Redis is updated, and affect scores are appended to the user's emotional trajectory.

**Latency Budget**: To ensure a natural conversational feel, the target end-to-end latency from the user finishing speaking to the AI's first audio chunk reaching the user is approximately 1.4 seconds. This is achieved