from pathlib import Path
import re

from config import VAULT_PATH
from vault.vector_store import VectorStore


# --------------------
# helpers
# --------------------

def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return ""


def chunk_text(text: str, chunk_size: int = 300):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", text.lower())


# --------------------
# global vector store
# --------------------

vector_store = VectorStore()


# --------------------
# vault scan
# --------------------

def scan_vault():
    files = []
    all_chunks = []

    if not VAULT_PATH.exists():
        return {"error": "Vault folder not found"}

    for path in VAULT_PATH.rglob("*"):
        if path.suffix.lower() not in [".txt", ".md"]:
            continue

        content = read_text_file(path)
        chunks = chunk_text(content)

        files.append({
            "name": path.name,
            "path": str(path),
            "extension": path.suffix,
            "chunks": chunks
        })

        all_chunks.extend(chunks)

    # 🔥 build embeddings here
    vector_store.build(all_chunks)

    return {
        "vault_path": str(VAULT_PATH),
        "file_count": len(files),
        "files": files
    }


# --------------------
# keyword fallback
# --------------------

def retrieve_relevant_chunks(query: str, vault_data: dict, limit: int = 3):
    matches = []

    query_words = normalize(query).split()

    for file in vault_data.get("files", []):
        for chunk in file.get("chunks", []):
            chunk_text = normalize(chunk)

            # score = number of query words found in chunk
            score = sum(1 for word in query_words if word in chunk_text)

            # 🔥 IMPORTANT: ignore weak matches
            if score >= 2:
                matches.append((score, chunk, file["name"]))

    # sort by relevance (highest score first)
    matches.sort(key=lambda x: x[0], reverse=True)

    # return top results
    return [
        {
            "file": name,
            "chunk": chunk,
            "score": score
        }
        for score, chunk, name in matches[:limit]
    ]
