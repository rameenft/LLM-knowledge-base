# ExperienceMatching

The core of an AI-powered social platform for shared human experiences lies in its ability to effectively connect individuals based on their lived journeys. This [[ExperienceMatching]] system goes beyond simple categorization, leveraging advanced AI to understand the nuance, emotional texture, and temporal aspects of personal narratives to foster truly empathetic connections.

## Key Concepts

*   **Shared Lived Experience**: The fundamental basis for matching, recognizing that empathy is often most effectively transmitted between individuals who have navigated similar life events or challenges.
*   **Embedding Retrieval**: Using large language models (LLMs) to convert user narratives into dense numerical vectors (embeddings), allowing for semantic similarity search in a high-dimensional space.
*   **Two-Stage Re-ranking**: A hybrid matching approach combining fast, approximate embedding retrieval with a slower, more nuanced LLM-based re-ranking process that generates human-readable explanations.
*   **Match Explanation**: A concise, LLM-generated summary of *why* two users are a good match, crucial for building user trust and increasing acceptance rates in sensitive contexts.
*   **Affect Trajectory**: The longitudinal tracking of a user's emotional state over multiple sessions, serving as an implicit signal for match quality and a feedback mechanism for the matching algorithm.
*   **Mentor Capacity**: Explicit limits and support mechanisms for volunteer mentors to prevent burnout and ensure the quality and sustainability of peer support relationships.

## How It Works

The [[ExperienceMatching]] system employs a sophisticated, multi-stage process to connect users. It begins by representing each user's lived experience in a dual format, as detailed in [[ExperienceStorageRetrieval]]: a structured record (e.g., category, time since onset, duration, current status, emotional texture) and a dense embedding vector. This hybrid approach allows for both precise filtering and nuanced semantic search.

When a user seeks a connection, they provide a narrative of their experience, often via a [[VoiceInterface]] where speech-to-text (STT) transcription captures their story. An LLM then processes this narrative, extracting structured fields and generating an embedding vector that semantically represents their unique journey.

The matching process proceeds in two main stages:

1.  **Initial Candidate Retrieval**: The user's experience embedding is used to perform an approximate nearest-neighbor search (e.g., via pgvector) against a corpus of existing experiences. This rapidly identifies a pool of top-N (e.g., 100) semantically similar candidates.
2.  **Filtering and LLM Re-ranking**: This candidate pool is then subjected to several filters based on the structured record:
    *   **Availability and Capacity**: Ensuring potential mentors are active and within their [[MentorMenteeSystem]] capacity limits (e.g., max 3 active mentees).
    *   **Recency and Status**: Prioritizing mentors whose experiences are temporally relevant (e.g., someone 2 years past a diagnosis for a newly diagnosed person) or whose journey status aligns with the mentee's needs (e.g., "in remission" for someone seeking hope).
    *   **Emotional Texture**: Matching on shared emotional experiences (e.g., "isolation," "fear," "relief") even if the underlying category differs slightly.

The filtered candidates are then passed to an LLM for a more granular re-ranking. This LLM considers the full context of both users' narratives and generates a concise, empathetic **Match Explanation** for the top few candidates. This explanation, shown to both parties, is critical for building trust and increasing the likelihood of match acceptance, addressing the opacity inherent in pure embedding-based recommendations.

For new users, a "cold start" problem is mitigated through a structured onboarding interview. This interview not only gathers initial data but also serves as an important [[EmpathyDesign]] moment, making the user feel heard from the outset.

Beyond initial matching, the system continuously refines its understanding of match quality. [[AffectiveComputing]] plays a crucial role here, tracking the **affect trajectory** of mentees over multiple sessions. Mentors who consistently facilitate positive emotional shifts in their mentees are implicitly surfaced as higher-quality matches, providing a natural feedback loop for the matching algorithm.

## Design Implications

*   **Prioritize Transparency**: Always provide a clear, LLM-generated explanation for why a match was made. This builds trust, especially in sensitive contexts, and addresses user distrust of opaque AI recommendations.
*   **Hybrid Data Representation is Key**: Combining structured data with rich, semantic embeddings allows for both precise filtering (e.g., availability, capacity) and nuanced, context-aware matching that captures the emotional depth of experiences.
*   **Mentor Well-being is Paramount**: Implement strict capacity limits, automated check-ins, and structured off-ramps for mentors to prevent burnout. A sustainable pool of engaged mentors is vital for the platform's success.
*   **Continuous Learning Loop**: Integrate feedback from user interactions (match acceptance, conversation length, mentee helpfulness, affect trajectory) into a continuous improvement cycle for the matching algorithm. This ensures the system gets smarter over time.
*   **Privacy by Design**: Given the sensitive nature of shared experiences, ensure robust privacy controls. Raw narratives should never be shared directly, and user consent must be explicit for any data analysis beyond core functionality.

## Open Questions

*   **Optimizing for Long-Term Engagement vs. Acceptance**: How should the system weigh immediate match acceptance rates against the likelihood of a sustained, high-quality relationship? These metrics can sometimes conflict.
*   **Cultural Nuance in Matching**: How do cultural variations in expressing and processing experiences impact the effectiveness of current embedding models and matching algorithms? Does the system need to be calibrated for different cultural contexts?
*   **Dynamic Experience Evolution**: How best to represent and match against experiences that are constantly evolving (e.g., ongoing illness, long-term grief)? While versioning is planned, how does the system dynamically adjust match relevance as a user's journey progresses?

## See Also

*   [[ExperienceStorageRetrieval]]
*   [[MentorMenteeSystem]]
*   [[AffectiveComputing]]
*   [[EmpathyDesign]]
*   [[PlatformArchitecture]]