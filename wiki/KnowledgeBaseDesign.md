# KnowledgeBaseDesign

A [[KnowledgeBaseDesign]] leverages Large Language Models (LLMs) not merely as question-answering oracles, but as powerful curators and connectors to synthesize raw, often messy research notes into structured, interlinked wiki articles. This compilation process is crucial, adding significant value by resolving contradictions, imposing structure, and surfacing emergent connections across disparate sources. The resulting wiki serves as a grounded, auditable, and continuously improvable source of truth for the platform's [[DialogueSystem]].

## Key Concepts

*   **LLM as Curator/Connector:** An LLM reads all raw source material to synthesize structured wiki articles, rather than just summarizing individual documents. It identifies and resolves contradictions and draws out implied connections.
*   **Compilation Pipeline:** The process of transforming informal raw notes into formalized wiki articles. This step is where the LLM adds value by structuring and integrating knowledge.
*   **WikiLink Graph:** Articles are interconnected using `[[WikiLink]]` syntax, creating a navigable graph of related concepts. This enhances discoverability and contextual understanding.
*   **Retrieval Augmented Generation (RAG):** The practice of grounding LLM responses by first retrieving relevant information from the knowledge base and injecting it into the LLM's context, preventing hallucination and ensuring factual accuracy.
*   **Functional Grounding:** The principle that LLM responses must be based on the actual knowledge contained within the system's curated sources, rather than relying solely on its pre-trained parameters.

## How It Works

The core architecture involves a three-stage process: `raw/` notes → `compile_wiki.py` (LLM) → `wiki/` articles → `qa.py` (retrieval + LLM) → answers.

1.  **Compilation Process:** The `compile_wiki.py` script feeds all raw research notes into a single LLM context window. The LLM is prompted to synthesize comprehensive wiki articles for specific topics. This synthesis goes beyond mere summarization; it actively resolves contradictions found across sources and identifies connections or implications suggested by multiple notes that might not be explicitly stated in any single one. Each article is stored as a separate Markdown file.

2.  **Content Structure:** Each wiki article is designed to be highly structured, typically including sections like "Key Concepts," "How It Works," "Design Implications," and "Open Questions." Crucially, articles embed `[[WikiLink]]` references to other related wiki topics, such as [[ExperienceStorageRetrieval]] or [[AffectiveComputing]], fostering a rich, interconnected knowledge graph.

3.  **Retrieval Mechanisms:** When a user query is posed to the [[DialogueSystem]], the `qa.py` component retrieves relevant wiki articles. While simple keyword matching can work for very small wikis, it quickly becomes inadequate for semantic understanding. A more robust approach utilizes **embedding similarity**: wiki articles are embedded into a vector space, and the user's query is also embedded. Approximate Nearest Neighbor (ANN) search (e.g., using `pgvector` as described in [[ExperienceStorageRetrieval]]) quickly identifies a pool of top candidate articles. For sensitive applications like [[MentorMenteeSystem]] matching, a hybrid approach is preferred: fast embedding retrieval for candidates, followed by structured filtering, and then LLM re-ranking that generates an explanation for the match or retrieved information. This hybrid model ensures both speed and semantic accuracy, while also building user trust by explaining *why* certain information was retrieved.

4.  **Integration with Dialogue System:** The retrieved wiki articles are injected into the LLM's context as "Retrieved context:" blocks. This implements [[DialogueSystem]]'s Retrieval Augmented Generation (RAG) pattern, ensuring that the LLM's responses are grounded in the curated knowledge base