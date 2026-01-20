## Cognitive Local-First AI Assistant with Grounded Retrieval and Context Memory

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

- Users place text files (`.txt`, `.md`, `.pdf`) inside a local `vault/` directory
- Files are:
  - read locally
  - chunked into 600-word segments (preserves paragraph context)
  - embedded using BGE-Large (state-of-the-art local embedding model)
  - stored in a FAISS vector database

---

## Internal Question Processing

Before any retrieval or answer generation occurs, each user question goes through an **LLM-driven processing and validation pipeline**.

### 1. Intent Classification
The system uses an LLM with **3-turn conversation history** to determine whether the input is:
- a new factual question
- a continuation of a previous question
- casual or non-informational input

The LLM analyzes conversation context to detect:
- pronoun references (it, that, this)
- cross-references (the first one, the second one)
- continuation signals (again, more, elaborate)

This ensures that unrelated or conversational inputs do not trigger unnecessary retrieval.

---

### 2. Pronoun Resolution
For continuation queries, the system uses an LLM to resolve pronouns before retrieval.

The LLM transforms ambiguous questions into explicit retrieval queries by replacing pronouns with their referents from conversation history.

This ensures semantic search retrieves the correct context.

---

### 3. Semantic Retrieval
The system performs retrieval using the resolved query:

- Queries are embedded using BGE-Large
- Relevant document chunks are retrieved using vector similarity search
- Hybrid scoring combines semantic similarity (70%) and keyword overlap (30%)
- Retrieved chunks are ranked by relevance score

---

### 4. LLM-Based Grounding
Retrieved chunks are passed to an LLM for sentence extraction.

The grounding LLM:
- receives the question and conversation context
- extracts sentences that could answer the question
- understands implicit answers (benefits = importance, outcomes = reasons)
- is instructed to be inclusive rather than exclusive

If no relevant sentences are found, the system **refuses to answer**.

---

## Context Memory (Controlled)

The assistant maintains a **lightweight, controlled context memory** to support follow-up questions.

- The system tracks the **last 3 question-answer pairs**
- Follow-up queries reuse validated context from previous turns
- Context is automatically cleared when a new, unrelated factual question is asked

This design ensures:
- continuity without long-term memory accumulation
- no cross-topic contamination
- predictable and bounded behavior
- support for cross-references across multiple turns

---

## Answer Generation

When a question passes validation and grounding checks:

1. Extracted sentences are validated and deduplicated
2. An LLM transforms the sentences into a natural language answer

**Rules:**
- Rephrasing and merging are allowed
- No new information may be introduced
- Every fact must be directly supported by vault content

If a valid answer cannot be produced, the assistant responds with:

> I don't have that information in my vault yet.

---

## Key Behaviors (By Design)

- **Strict grounding**  
  Answers are generated only from vault content

- **Out-of-scope refusal**  
  Questions not covered by the vault are explicitly rejected

- **No hallucinations**  
  The model is not allowed to invent or infer missing information

- **Intent-aware follow-ups**  
  Follow-up queries preserve the original intent (WHY vs WHAT vs HOW)

- **Safe comparisons**  
  Comparisons are allowed only when all compared topics exist in the vault

- **Deterministic behavior**  
  No cloud calls, no hidden state, no nondeterminism

- **Adaptive understanding**  
  No hardcoded keywords or patterns - LLMs handle semantic understanding

---

## Architecture Principles

### LLM-Driven, Not Rule-Based

The system uses **LLMs at every decision point** instead of hardcoded rules:

- **Intent classification:** LLM analyzes question + conversation history
- **Pronoun resolution:** LLM resolves references to previous topics
- **Grounding:** LLM extracts relevant sentences with semantic understanding
- **Answer generation:** LLM transforms grounded sentences

This approach:
- eliminates brittleness from keyword matching
- adapts to any domain without configuration
- handles natural language variation
- understands implicit questions and indirect answers

### No Hardcoded Logic

Zero hardcoded:
- keyword lists
- stop words
- pattern matching rules
- question templates

The system generalizes through LLM reasoning, not brittle heuristics.

---

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** React + TypeScript
- **LLM Runtime:** Ollama (local)
- **Models:**
  - Qwen 2.5:7B (intent classification, grounding, generation)
  - Mistral 7B Instruct (casual conversation)
- **Embeddings:** BGE-Large (local, state-of-the-art semantic search)
- **Vector Search:** FAISS (local vector database)

---

## Why Local-First?

- Full data privacy
- Works offline
- No API costs
- Complete user control over the knowledge source
- No latency from network calls

---

## Project Status

**Stable and complete.**

The project implements a fully working local Retrieval-Augmented Generation (RAG) system with:
- LLM-driven intent classification with 3-turn history
- pronoun resolution for continuation queries
- semantic retrieval with BGE-Large embeddings
- LLM-based sentence grounding
- controlled context memory
- grounded answer generation
- safe refusals and comparisons
- zero hardcoded patterns or keywords

Further improvements are possible, but the **core system behavior is intentionally locked** to preserve correctness.

---

## Design Philosophy

**Correctness over fluency.**

The system would rather refuse than guess.  
The system would rather be precise than be helpful.  
The system would rather say "I don't know" than hallucinate.

This makes it suitable for:
- personal knowledge bases
- research notes
- study materials
- sensitive documents
- any domain where accuracy matters more than coverage