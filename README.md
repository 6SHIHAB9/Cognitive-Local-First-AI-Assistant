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
- Chunks content into **800-word parent blocks** stored in a global `PARENT_STORE` dictionary in RAM, each assigned a unique `PARENT_ID`
- Further splits each parent block into **75-word child chunks** with a hidden `[PARENT_ID:xxx]` tag injected into each chunk
- Embeds only the child chunks using `mxbai-embed-large` via Ollama
- Stores child chunk embeddings in a FAISS vector index
The vault syncs automatically — drop a file in the folder and it is indexed on the next query. Parent blocks are persisted to `parent_docs.json` and loaded into RAM at server startup for zero disk I/O during queries.
 
---
 
## Internal Question Processing Pipeline
 
Every user question passes through a **multi-stage ML pipeline** before an answer is generated.
 
### Stage 1 — Intent Classification
 
A custom-trained **DeBERTa-v3-base** transformer classifies each question into one of three intents:
 
- **Factual** — a standalone question requiring vault retrieval
- **Continuation** — a follow-up referencing a previous question
- **Casual** — a greeting or conversational input
The model uses a two-pass classification strategy. The first pass checks casual confidence against a threshold of 0.6. The second pass runs with conversation context to distinguish factual from continuation. The model was trained on a custom dataset of domain-specific examples covering student records, pharmacy inventory, legal case files, HR policies, and general conversation.
 
Casual questions are answered directly by the LLM without touching the vault. Factual and continuation questions proceed through retrieval.
 
### Stage 2 — Context Resolution (Continuation Only)
 
For continuation queries, the `ContextManager` checks the cosine similarity between the current question and the previous question. If similarity is above 0.35, the previous question is merged with the current question to form a combined retrieval query. If similarity drops below 0.35, topic drift is detected and the query is treated as a new factual question.
 
### Stage 3 — Semantic Retrieval
 
The query is embedded using `mxbai-embed-large` via Ollama. FAISS performs a nearest-neighbour search across all stored child chunk embeddings and returns the top-K most similar 75-word chunks.
 
### Stage 4 — Cross-Encoder Reranking
 
Retrieved child chunks are passed to `cross-encoder/ms-marco-MiniLM-L-6-v2`. Unlike embedding-based retrieval which compares vectors independently, the cross-encoder reads the question and each chunk together and produces a precise relevance score. Chunks are sorted by score with **no hard cutoff threshold** — this ensures tabular data such as phone numbers and CGPAs is not penalized for lacking natural language fluency.
 
### Stage 5 — Parent Block Lookup (The Pivot)
 
The `[PARENT_ID:xxx]` tag is parsed from each winning child chunk using regex. The corresponding 800-word parent block is fetched instantly from `PARENT_STORE` in RAM. Up to 3 unique parent blocks are retrieved, providing up to 2400 words of rich, unbroken context to the LLM including surrounding sentences, table headers, and related facts.
 
### Stage 6 — Sufficiency Check
 
The sufficiency scorer grades the top 3 child chunks to verify that relevant evidence exists before proceeding to answer generation. If the score falls below 0.60 for continuation queries, the system refuses to answer rather than generating a low-confidence response.
 
---
 
## Answer Generation
 
The retrieved parent blocks are passed to `gemma2:2b-instruct` via Ollama with a strict grounding prompt:
 
- The LLM may only use the provided context
- Rephrasing and combining information is permitted
- No new information may be introduced
- Every fact must be directly present in the retrieved parent blocks
Answers are streamed token-by-token to the frontend via Server-Sent Events (SSE).
 
---
 
## ML Models
 
| Model | Role | Type |
|---|---|---|
| DeBERTa-v3-base | Intent classification | Custom trained transformer |
| mxbai-embed-large | Query and chunk embedding | Local via Ollama |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | Chunk reranking | HuggingFace cross-encoder |
| Custom sufficiency scorer | Evidence adequacy check | Custom trained |
| gemma2:2b-instruct-q4_K_M | Answer generation | Local via Ollama |
 
---
 
## Key Behaviors
 
- **Strict grounding** — answers are generated only from vault content, never from model training data
- **Out-of-scope refusal** — questions not covered by the vault are explicitly rejected
- **No hallucinations** — the LLM is prohibited from introducing any information not present in retrieved context
- **Parent-document retrieval** — small chunks for precise search, large parent blocks for rich LLM context
- **No reranking cutoff** — tabular data is never penalized for lacking natural language fluency
- **Intent-aware follow-ups** — continuation queries use cosine similarity for topic drift detection
- **Multi-format support** — txt, md, pdf, and docx files including table extraction
- **Fully offline** — no internet connection required after initial model download
- **Zero disk I/O during queries** — parent blocks loaded into RAM at startup for instant lookup
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
- Suitable for sensitive institutional data including hospitals, law firms, and educational institutions
