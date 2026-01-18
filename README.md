#Local-First AI Assistant

A local-first AI assistant that answers questions **strictly using information from user-provided files**.

The assistant reads text documents from a local **vault** and generates answers **only when the information exists in those files**.  
If the information is not present, the system **refuses to answer instead of guessing**.

Everything runs locally.  
No data is uploaded.  
No external APIs are used.

---

## Core Idea

Most AI assistants prioritize fluent answers, even when information is missing.

This project prioritizes **correctness over fluency**.

> Answers are generated only when they can be fully grounded in user-provided data.

The system is designed to:
- avoid hallucinations
- refuse out-of-scope questions
- preserve intent across follow-up questions
- provide deterministic, explainable behavior

---

## How It Works

### Vault Ingestion

- Users place text files (`.txt`, `.md`) inside a local `vault/` directory
- Files are:
  - read locally
  - chunked into smaller segments
  - embedded using a local embedding model
  - stored in a local vector database

---

## Internal Question Processing

Before any retrieval or answer generation occurs, each user question goes through an **internal processing and validation pipeline**.

### 1. Intent Classification
The system determines whether the input is:
- a new factual question
- a continuation of a previous question
- casual or non-informational input

This ensures that unrelated or conversational inputs do not trigger unnecessary retrieval.

---

### 2. Subject Resolution
The system extracts the core subject(s) of the question and normalizes them internally.  
This step helps anchor the question to concrete concepts that must be present in the vault.

---

### 3. Sub-Question Generation (Internal)
For complex, comparative, or explanatory queries, the system internally refines the original question into **simpler sub-questions or retrieval queries**.

These sub-questions are used to:
- improve alignment between the question and stored documents
- reduce dependency on the user’s exact phrasing
- avoid missing relevant information due to linguistic variation

Sub-questions are **not exposed to the user** and exist only for internal processing.

---

### 4. Retrieval & Grounding
Only after sub-question generation does the system perform retrieval:

- Refined queries are embedded
- Relevant document chunks are retrieved using vector similarity search
- Retrieved content is validated to ensure it directly supports the question

If sufficient grounding is not found, the system **refuses to answer**.

---

## Context Memory (Controlled)

The assistant maintains a **lightweight, controlled context memory** to support follow-up questions.

- The system tracks the **active subject** of the conversation
- Follow-up queries such as “explain it again” reuse the validated subject
- Context is automatically cleared when a new, unrelated factual question is asked

This design ensures:
- continuity without long-term memory accumulation
- no cross-topic contamination
- predictable and bounded behavior

---

## Answer Generation

When a question passes validation and grounding checks:

1. Retrieved sentences are filtered and deduplicated
2. Partial fragments and list headers are removed
3. A language model rewrites the remaining content

**Rules:**
- Rephrasing and merging are allowed
- No new information may be introduced
- Every fact must be directly supported by vault content

If a valid answer cannot be produced, the assistant responds with:

I don't have that information in my vault yet.

---

## Key Behaviors (By Design)

- **Strict grounding**  
  Answers are generated only from vault content

- **Out-of-scope refusal**  
  Questions not covered by the vault are explicitly rejected

- **No hallucinations**  
  The model is not allowed to invent or infer missing information

- **Intent-aware follow-ups**  
  Follow-up queries preserve the original intent (WHY vs WHAT)

- **Safe comparisons**  
  Comparisons are allowed only when all compared topics exist in the vault

- **Deterministic behavior**  
  No cloud calls, no hidden state, no nondeterminism

---

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** React + TypeScript
- **LLM:** Ollama (local models)
- **Embeddings:** nomic-embed-text (Ollama, local embedding model)
- **Vector Search:** FAISS (local vector database)

---

## Why Local-First?

- Full data privacy
- Works offline
- No API costs
- Complete user control over the knowledge source

---

## Project Status

**Stable and complete.**

The project implements a fully working local Retrieval-Augmented Generation (RAG) system with:
- internal question validation
- sub-question refinement before retrieval
- controlled context memory
- grounded answer generation
- safe refusals and comparisons

Further improvements are possible, but the **core system behavior is intentionally locked** to preserve correctness.
