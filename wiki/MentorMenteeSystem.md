# MentorMenteeSystem

## MentorMenteeSystem

The Mentor-Mentee System is the core mechanism for connecting individuals on the platform, facilitating shared human experiences through peer support. It operates as a sophisticated two-sided matching market, prioritizing empathetic connections and long-term engagement over simple availability. The system is designed to manage mentor capacity, prevent burnout, and continuously improve match quality through advanced AI techniques.

### Key Concepts

*   **Two-Sided Matching Market**: A system where both mentors and mentees must accept a proposed match, optimizing for mutual satisfaction rather than just one party's preference.
*   **Hybrid Matching**: A two-stage approach combining fast, semantic similarity search using embeddings with a slower, more nuanced re-ranking by an LLM that also generates match explanations.
*   **Mentor Capacity Management**: Strict limits and proactive measures to ensure mentors are not overwhelmed, preserving the quality of support and preventing burnout.
*   **Cold Start Problem**: The challenge of providing meaningful matches for new users who have not yet generated sufficient interaction data or detailed experience narratives.
*   **Affect Trajectory**: The trend of a user's emotional state over multiple sessions, serving as a key indicator of a match's effectiveness and a mentor's impact.
*   **Functional Empathy**: The ability of the AI to produce responses perceived as empathetic by humans, crucial for facilitating trust and engagement in sensitive contexts.

### How It Works

The system begins by capturing a user's lived experience. While free-text narratives are rich, they are challenging to query directly. Therefore, a hybrid approach is used: users can provide their story via voice or text, which an LLM then processes. This [[ExperienceStorageRetrieval]] pipeline extracts structured fields (e.g., category, time since onset, duration, current status) and computes a dense embedding vector for the narrative. A crucial addition is the "emotional texture" field, which captures the qualitative feel of an experience (e.g., "isolation," "relief"), enabling more nuanced matching beyond simple categories.

Matching operates on a two-sided market principle, theoretically grounded in concepts like Gale-Shapley, but practically optimized for expected engagement and long-term retention. When a mentee seeks support, the [[DialogueSystem]] can trigger a mentor search. The process involves:
1.  **Candidate Retrieval**: The mentee's experience embedding is used for a fast approximate nearest-neighbor search (e.g., via pgvector) against the corpus of available mentor experiences. This yields a pool of top candidates.
2.  **Structured Filtering**: This pool is then filtered using structured criteria from the [[ExperienceStorageRetrieval]] system, such as mentor availability, capacity, and specific experience categories. Temporal recency of the mentor's experience is a significant factor, as someone two years past a diagnosis may be more relevant to a newly diagnosed person than someone 15 years past.
3.  **LLM Re-ranking and Explanation**: The filtered candidates undergo a slower, more detailed re-ranking by an LLM. This LLM considers the full context of both parties' narratives and generates a concise explanation for why a particular match is suitable. This transparency is vital, as users are more likely to accept matches they understand, especially in sensitive contexts.

For new users facing the [[Cold Start Problem]], a structured onboarding interview is critical. This interview not only collects initial data to generate a synthetic narrative for embedding but also serves as an initial moment where the user feels heard, adding immediate value. Matches then progressively improve as more behavioral data and narrative details are added over time.

Mentor well-being is paramount for the sustainability of the system. Hard capacity limits (e.g., a maximum of 3 active mentees) are enforced to prevent [[Mentor Burnout]]. Automated check-ins ("How are you feeling about this relationship?") and structured off-ramps are implemented. A dedicated mentor-only community is also planned to provide support for those who are supporting others.

Evaluation of the system is multi-faceted, extending beyond simple match acceptance rates. Key metrics include first message within 48 hours, conversation longevity (e.g., still talking at 4 weeks), mentee helpfulness scores, and mentor satisfaction. Crucially, the system leverages [[AffectiveComputing]] to track the "affect trajectory" of mentees over time. A mentee trending from "anxious-high" to "hopeful-medium" across sessions signals a successful match and a high-quality mentor, providing a natural, implicit quality signal that doesn't rely solely on explicit ratings.

### Design Implications

*   **Prioritize Mentor Well-being**: Sustaining the mentor pool requires proactive measures against burnout, including strict capacity limits and dedicated support systems.
*   **Transparency Builds Trust**: Providing clear, LLM-generated explanations for why a match was made significantly increases user acceptance and engagement in sensitive contexts.
*   **Onboarding as Value**: The initial onboarding interview should be designed as a valuable, empathetic experience in itself, not just a data collection exercise, to address the cold start problem and build initial trust.
*   **Dynamic Evaluation**: Rely on a blend of explicit user feedback and implicit signals like [[AffectiveComputing]] trajectories and long-term retention to truly measure match quality, rather than just immediate acceptance.
*   **Privacy-First Design**: Given the highly sensitive nature of shared experiences, ensure robust privacy controls, including explicit consent for data use, anonymized candidate lists, and selective matchability for individual experiences.

### Open Questions

*   **Optimizing Conflicting Metrics**: How to best weight match acceptance rates against long-term retention and positive affect trajectories when these metrics may sometimes conflict.
*   **Cultural Nuance in Matching**: How to account for cultural variations in what constitutes a "good" match or how empathetic support is expressed, potentially requiring targeted fine-tuning or calibration.
*   **Scaling Mentor Support**: How to effectively scale the mentor-only community and its support mechanisms without eventually overwhelming human moderators or creating new burnout vectors.

### See Also

*   [[ExperienceMatching]]
*   [[AffectiveComputing]]
*   [[EmpathyDesign]]
*   [[ExperienceStorageRetrieval]]
*   [[DialogueSystem]]