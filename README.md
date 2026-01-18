# Local-First AI Assistant

This project is a **local-first AI assistant** built using **FastAPI** and **React**.

The assistant works by reading text files from a local folder called a **vault** and answering questions **only using the information found in those files**.

Nothing is uploaded. Everything stays on the user’s machine.

---

## How It Works

1. You place text files (`.txt`, `.md`) inside a local `vault/` folder.
2. When the vault is synced:
   - Files are read
   - Text is chunked
   - Embeddings are created
   - Data is stored in a local vector database
3. When a question is asked:
   - The question is embedded
   - Relevant chunks are retrieved using vector search
   - An LLM generates an answer **only from those chunks**
4. If the information is not found in the vault, the assistant replies:
   
I don't have that information in my vault yet.


---

## Key Principles

- Local-first (no cloud, no uploads)
- Privacy-focused
- No hallucinations
- No guessing missing information
- Answers are strictly grounded in user files

---

## Tech Stack

- Backend: FastAPI (Python)
- Frontend: React + TypeScript
- LLM: Ollama (local models)
- Embeddings: Local embedding model
- Vector Search: Local vector database

---

## Project Status

This project is currently **paused** after reaching a working local RAG baseline.