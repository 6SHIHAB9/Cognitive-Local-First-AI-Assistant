# VaultAI — Privacy-First Local RAG System
 
A local-first AI assistant that answers questions **strictly using information from user-provided documents**.
 
VaultAI reads files from a local **vault** directory and generates answers **only when the information exists in those files**. If the information is not present, the system **refuses to answer instead of guessing**.
 
Everything runs locally. No data is uploaded. No external APIs are called.
 
---
 
## Core Idea
 
Most AI assistants prioritize fluent answers, even when information is missing.
 
VaultAI prioritizes **correctness over fluency**.
 
> Answers are generated only when they can be fully grounded in user-provided vault content.
 
The system is designed to:
- Avoid hallucinations by restricting the LLM to retrieved evidence only
- Refuse out-of-scope questions that are not covered by vault documents
- Preserve intent across follow-up questions using a context manager
- Provide deterministic, explainable, fully offline behavior
 
---
 
## How It Works
 
### Vault Ingestion
 
Users place files (`.txt`, `.md`, `.pdf`, `.docx`) inside a local `vault/` directory. On startup and before every query, the system:
 
- Scans the vault for new or modified files
- Reads and parses each file including PDF text extraction and DOCX table parsing
- Chunks content into segments of approximately 600 words preserving paragraph context
- Embeds each chunk using `mxbai-embed-large` via Ollama
- Stores all embeddings in a FAISS vector index
 
The vault syncs automatically — drop a file in the folder and it is indexed on the next query.
 
---
 
## Internal Question Processing Pipeline
 
Every user question passes through a **5-stage ML pipeline** before an answer is generated.
 
### Stage 1 — Intent Classification
 
A custom-trained **DeBERTa-v3-base** transformer classifies each question into one of three intents:
 
- **Factual** — a standalone question requiring vault retrieval
- **Continuation** — a follow-up referencing a previous question
- **Casual** — a greeting or conversational input
 
The model uses a two-pass classification strategy. The first pass checks casual confidence against a threshold of 0.6. The second pass runs with conversation context to distinguish factual from continuation. The model was trained on a custom dataset of 5,623 labeled examples across all three classes.
 
Casual questions are answered directly by the LLM without touching the vault. Factual and continuation questions proceed through retrieval.
 
### Stage 2 — Context Resolution (Continuation Only)
 
For continuation queries, the `ContextManager` retrieves the previous question from a rolling 3-turn history and merges it with the current question to form an explicit combined query. This resolved query is used for retrieval instead of the ambiguous follow-up.
 
### Stage 3 — Semantic Retrieval
 
The query is embedded using `mxbai-embed-large` via Ollama. FAISS performs a nearest-neighbour search across all stored chunk embeddings and returns the top 20 most similar chunks. Retrieved chunks are limited to the top 12 for downstream processing.
 
### Stage 4 — Multi-Stage Filtering Pipeline
 
Retrieved chunks pass through four sequential filters:
 
1. **Sentence splitter** — chunks are split into individual sentences, each tagged with its source chunk ID
2. **Deduplication** — repeated sentences across chunks are removed
3. **Topic coherence filter + sibling rescue** — a custom topic scorer keeps the most relevant sentences. Any sentence that passes the filter pulls in all sibling sentences from the same source chunk, preserving context around retrieved facts
4. **Cosine relevance pre-filter** — sentences below a minimum relevance score of 0.25 are dropped before the expensive reranker runs
 
### Stage 5 — Cross-Encoder Reranking
 
Surviving sentences are passed to `cross-encoder/ms-marco-MiniLM-L-6-v2`. Unlike embedding-based retrieval which compares vectors independently, the cross-encoder reads the question and each sentence together and produces a precise relevance score. The top 15 sentences are reranked and the top 8 by evidence weight are selected as the final allowed sentences.
 
---
 
## Answer Generation
 
The top 8 sentences are passed to `gemma2:2b-instruct` via Ollama with a strict grounding prompt:
 
- The LLM may only use the provided sentences
- Rephrasing and combining sentences is permitted
- No new information may be introduced
- Every fact must be directly present in the allowed sentences
 
If the sufficiency scorer determines that the retrieved evidence is insufficient (score below 0.60), the system refuses to answer rather than generating a low-confidence response.
 
Answers are streamed token-by-token to the frontend via Server-Sent Events (SSE).
 
---
 
## ML Models
 
| Model | Role | Type |
|---|---|---|
| DeBERTa-v3-base | Intent classification | Custom trained transformer |
| mxbai-embed-large | Query and chunk embedding | Local via Ollama |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | Sentence reranking | HuggingFace cross-encoder |
| Custom sufficiency scorer | Evidence adequacy check | Custom trained |
| Custom topic coherence filter | Sentence relevance scoring | Custom trained |
| Custom reference ranker | Evidence weighting | Custom trained |
| gemma2:2b-instruct-q4_K_M | Answer generation | Local via Ollama |
 
---
 
## Key Behaviors
 
- **Strict grounding** — answers are generated only from vault content, never from model training data
- **Out-of-scope refusal** — questions not covered by the vault are explicitly rejected
- **No hallucinations** — the LLM is prohibited from introducing any information not present in retrieved sentences
- **Intent-aware follow-ups** — continuation queries resolve pronouns and context before retrieval
- **Multi-format support** — txt, md, pdf, and docx files are all supported including table extraction
- **Fully offline** — no internet connection required after initial model download
- **Auto-sync** — vault changes are detected and indexed automatically
 
---
 
## Tech Stack
 
- **Backend:** FastAPI (Python)
- **Frontend:** React + TypeScript + Tailwind CSS
- **LLM Runtime:** Ollama (fully local)
- **LLM:** gemma2:2b-instruct-q4_K_M
- **Embeddings:** mxbai-embed-large (local via Ollama)
- **Vector Search:** FAISS
- **Intent Model:** DeBERTa-v3-base (custom trained)
- **Reranker:** cross-encoder/ms-marco-MiniLM-L-6-v2
- **PDF parsing:** PyMuPDF (fitz)
- **DOCX parsing:** python-docx
 
---
 
## Why Local-First?
 
- Complete data privacy — files never leave the device
- Works fully offline after setup
- No API costs or rate limits
- No cloud dependency or vendor lock-in
- Suitable for sensitive institutional data