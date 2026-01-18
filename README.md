# Local-First AI Assistant

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

## Question Processing & Validation

Before answering, every user question goes through an **internal processing pipeline**:

1. **Intent classification**  
   The system determines whether the question is:
   - a new factual query  
   - a continuation of a previous question  
   - casual or non-informational  

2. **Subject resolution**  
   Core subject terms are extracted from the question and validated against retrieved vault content.

3. **Sub-question generation (internal)**  
   For complex or multi-part questions, the system internally breaks the query into **simpler sub-questions** to:
   - better align retrieval with the user’s intent
   - avoid missing relevant information due to phrasing differences
   - improve grounding accuracy

   These sub-questions are **not shown to the user** and are used only for internal retrieval and validation.

4. **Grounding check**  
   Retrieved content is verified to ensure it directly supports the resolved subject and sub-questions.  
   If sufficient grounding is not found, the system refuses to answer.

This process prevents:
- answering loosely related questions
- leaking partially relevant information
- hallucinations caused by semantic overlap

---

## Context Memory (Controlled)

The assistant maintains a **lightweight, controlled context memory** to support follow-up questions.

- The system tracks the **active subject** of the conversation
- Follow-up queries such as *“explain it again”* or *“explain it simply”* reuse the validated subject
- Context is **cleared automatically** when a new, unrelated factual question is asked

This ensures:
- continuity without long-term memory accumulation
- no cross-topic contamination
- predictable, bounded behavior

---

## Answer Generation

When a question passes validation:

1. Relevant chunks are retrieved using vector similarity
2. Individual sentences are filtered, cleaned, and deduplicated
3. A language model rewrites the allowed sentences

**Rules:**
- The model may rephrase, merge, and simplify sentences
- No new information may be introduced
- All facts must be directly supported by the vault content

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
- sub-question decomposition
- controlled context memory
- grounded answer generation
- safe refusals and comparisons

Further improvements are possible, but the **core system behavior is intentionally locked** to preserve correctness.
