# LLM-Powered Personal Knowledge Base

INDENG 231 — Data Modeling, UC Berkeley, Spring 2026

---

## Overview

This project implements a Karpathy-style personal knowledge base using the Google Gemini API. The system demonstrates what an LLM compiler adds over a simple document store: it reads all raw source material simultaneously, resolves contradictions between sources, and surfaces cross-source implications that no single note contains on its own.

The topic is the design of an AI-powered social platform for shared human experiences — a platform that connects users who have navigated similar life challenges (illness, grief, career disruption, immigration) on a mentor-mentee model, mediated by a voice-enabled AI conversational interface.

---

## How It Works

The pipeline has three layers:

**Layer 1 — Raw notes**

Ten informal research notes covering the five main technical areas of the platform: shared experience platform design, mentor-mentee matching algorithms, affective computing, voice dialogue systems, and empathetic AI design. The notes are written informally with deliberate gaps, redundancy, and contradictions between files to give the compiler real synthesis work.

**Layer 2 — LLM compiler**

`compile_wiki.py` reads all ten notes in a single context window using Gemini 2.5 Flash and generates ten structured wiki articles. The compiler prompt explicitly instructs the model to synthesize across multiple sources (not summarize one), resolve contradictions, and surface implications that only emerge from reading sources together. Each article follows a consistent structure: Key Concepts, How It Works, Design Implications, Open Questions, and See Also with `[[WikiLink]]` cross-references. The compiler produced 6,085 words across ten articles with 90 WikiLinks.

**Layer 3 — Retrieval-augmented Q&A**

`qa.py` uses local sentence-transformer embeddings (`all-MiniLM-L6-v2`) for cosine similarity retrieval, then Gemini 2.5 Flash to generate cited answers from the top-4 retrieved articles. The embedding approach handles semantic queries that keyword matching would miss — for example, "how does the system detect sadness?" retrieves `AffectiveComputing` at 0.615 cosine similarity despite zero keyword overlap. Embeddings are cached locally so retrieval runs with no API calls.

The entire pipeline runs at zero cost: Gemini 2.5 Flash on the free tier for compilation and Q&A, sentence-transformers running locally for retrieval.

---

## Project Structure

```
.
├── raw/
│   ├── 01_shared_experience_platforms.md
│   ├── 02_mentor_mentee_matching.md
│   ├── 03_affective_computing.md
│   ├── 04_speech_to_text_pipelines.md
│   ├── 05_text_to_speech_synthesis.md
│   ├── 06_dialogue_systems.md
│   ├── 07_empathetic_ai_design.md
│   ├── 08_experience_storage_retrieval.md
│   ├── 09_platform_integration_architecture.md
│   └── 10_llm_knowledge_base_design.md
│
├── wiki/
│   ├── AffectiveComputing.md
│   ├── DialogueSystem.md
│   ├── EmpathyDesign.md
│   ├── ExperienceMatching.md
│   ├── ExperienceStorageRetrieval.md
│   ├── KnowledgeBaseDesign.md
│   ├── MentorMenteeSystem.md
│   ├── PlatformArchitecture.md
│   ├── SafetyAndEscalation.md
│   ├── VoiceInterface.md
│   ├── _index.json             link graph and word counts
│   └── _embeddings.pkl         cached sentence-transformer embeddings
│
├── compile_wiki.py             LLM compiler
├── qa.py                       Q&A interface
├── build_index.py              rebuild _index.json without API calls
├── test_pipeline.py            end-to-end validation
├── generate_report2.py         PDF report generator
└── INDENG231_Project2_Report.pdf
```

---

## Setup

**1. Install dependencies**
```bash
pip install google-genai sentence-transformers
```

**2. Get a free Google API key** at aistudio.google.com (no credit card required). Go to Get API key → Create API key.

**3. Create a `.env` file in the project root**
```
GOOGLE_API_KEY=your-key-here
```

**4. Verify everything is working**
```bash
python test_pipeline.py
```

---

## Usage

**Compile the wiki** (run once, takes 5-10 minutes on the free tier)
```bash
python compile_wiki.py                              # compile all 10 articles
python compile_wiki.py --force                      # recompile everything
python compile_wiki.py --topic AffectiveComputing   # single article
python compile_wiki.py --dry-run                    # preview without API calls
```

**Ask questions**
```bash
python qa.py -q "How does the platform detect when a user is in crisis?"
python qa.py -q "What is the latency budget for voice interaction?"
python qa.py -q "How does mentor burnout get prevented?"
python qa.py                   # interactive mode
python qa.py --list            # list all articles with word and link counts
python qa.py --index           # rebuild embedding index
```

---

## Wiki Statistics

| Article | Words | Links Out | Links In |
|---|---|---|---|
| AffectiveComputing | 719 | 16 | 8 |
| DialogueSystem | 703 | 14 | 7 |
| EmpathyDesign | 946 | 10 | 7 |
| ExperienceMatching | 895 | 12 | 5 |
| ExperienceStorageRetrieval | 409 | 6 | 8 |
| KnowledgeBaseDesign | 531 | 10 | 0 |
| MentorMenteeSystem | 916 | 12 | 6 |
| PlatformArchitecture | 669 | 12 | 4 |
| SafetyAndEscalation | 678 | 6 | 2 |
| VoiceInterface | 818 | 15 | 6 |

Total: 6,085 words, 90 WikiLinks across 10 articles.
