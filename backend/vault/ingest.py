from pathlib import Path
import re

from config import VAULT_PATH
from vault.vector_store import VectorStore


# --------------------
# helpers
# --------------------

def read_text_file(path: Path) -> str:
    try:
        if path.suffix.lower() == ".pdf":
            import fitz
            doc = fitz.open(str(path))
            text = ""
            for page in doc:
                # Extract text with table detection
                blocks = page.get_text("blocks")
                blocks.sort(key=lambda b: (b[1], b[0]))  # sort by y then x
                for block in blocks:
                    block_text = block[4].strip()
                    if block_text:
                        text += block_text + "\n\n"
            doc.close()
            return text

        elif path.suffix.lower() == ".docx":
            from docx import Document
            from docx.oxml.ns import qn
            doc = Document(str(path))
            parts = []

            for block in doc.element.body:
                # Paragraphs
                if block.tag == qn('w:p'):
                    runs = block.findall('.//' + qn('w:t'))
                    text = " ".join(r.text for r in runs if r.text)
                    if text.strip():
                        parts.append(text.strip())

                # Tables
                elif block.tag == qn('w:tbl'):
                    from docx.table import Table
                    table = Table(block, doc)
                    for row in table.rows:
                        row_text = " | ".join(
                            cell.text.strip()
                            for cell in row.cells
                            if cell.text.strip()
                        )
                        if row_text:
                            parts.append(row_text)

            return "\n\n".join(parts)

        else:
            return path.read_text(encoding="utf-8", errors="ignore")

    except Exception as e:
        print(f"  ⚠️ Failed to read {path.name}: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50):
    # Try markdown header splitting first
    section_pattern = re.compile(r'(?=^#{1,3}\s)', re.MULTILINE)
    sections = section_pattern.split(text)
    sections = [s.strip() for s in sections if s.strip()]

    # If no markdown headers found, split by double newlines (for PDFs)
    if len(sections) <= 1:
        sections = re.split(r'\n\s*\n', text)
        sections = [s.strip() for s in sections if s.strip()]

    # If still one section, split by single newline before title-case headings (PDF)
    if len(sections) <= 1:
        sections = re.split(r'\n(?=[A-Z][a-z]+ [A-Z]|[A-Z][a-z]+\n)', text)
        sections = [s.strip() for s in sections if s.strip()]

    # Last resort: split by word count
    if len(sections) <= 1:
        words = text.split()
        sections = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                sections.append(chunk)

    chunks = []
    for section in sections:
        words = section.split()
        if len(words) <= chunk_size:
            chunks.append(section)
        else:
            for i in range(0, len(words), chunk_size - overlap):
                chunk = " ".join(words[i:i + chunk_size])
                if chunk.strip():
                    chunks.append(chunk)
                if i + chunk_size >= len(words):
                    break

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
        return {
            "vault_path": str(VAULT_PATH),
            "file_count": 0,
            "empty_files": 0,
            "indexed_files": 0,
            "files": [],
        }

    print(f"📂 Scanning vault: {VAULT_PATH}")

    for path in VAULT_PATH.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in [".txt", ".md", ".pdf", ".docx"]:
            continue

        content = read_text_file(path)
        has_content = bool(content.strip())

        chunks = chunk_text(content) if has_content else []

        files.append({
            "name": path.name,
            "path": str(path),
            "extension": path.suffix.lower(),
            "empty": not has_content,
            "chunk_count": len(chunks),
            "chunks": chunks,
        })

        all_chunks.extend(chunks)
        
        if chunks:
            print(f"  ✅ {path.name}: {len(chunks)} chunks")

    # build embeddings ONLY from real chunks
    if all_chunks:
        vector_store.build(all_chunks)
    else:
        print("⚠️ No content found to index")

    empty_files = sum(1 for f in files if f["empty"])
    indexed_files = sum(1 for f in files if not f["empty"])

    print(f"\n📊 Scan complete:")
    print(f"  Files found: {len(files)}")
    print(f"  Indexed: {indexed_files}")
    print(f"  Total chunks: {len(all_chunks)}")

    return {
        "vault_path": str(VAULT_PATH),
        "file_count": len(files),          # filesystem truth
        "empty_files": empty_files,         # UX truth
        "indexed_files": indexed_files,     # knowledge truth
        "files": files,
    }


import re
from collections import defaultdict

MIN_SCORE = 0.2   # ← relevance threshold (important)


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def keyword_score(query: str, text: str) -> float:
    q = tokenize(query)
    t = tokenize(text)
    if not q or not t:
        return 0.0
    return len(q & t) / len(q)


def extract_text(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("chunk") or item.get("text") or ""
    return ""


def extract_score(item):
    if isinstance(item, dict):
        return float(item.get("score", 1.0))
    return 1.0


def retrieve_relevant_chunks(query: str, vault_data: dict, limit: int = 3):
    scored = defaultdict(float)

    # -------------------------
    # 1. Semantic search
    # -------------------------
    semantic_results = vector_store.search(query, k=limit * 3)

    for r in semantic_results:
        text = extract_text(r)
        if not text:
            continue
        scored[text] += 0.7 * extract_score(r)

    # -------------------------
    # 2. Keyword overlap (FIXED)
    # -------------------------
    for file in vault_data.get("files", []):
        for chunk in file.get("chunks", []):
            if not isinstance(chunk, str):
                continue

            ks = keyword_score(query, chunk)
            if ks > 0:
                scored[chunk] += 0.3 * ks

    # -------------------------
    # 3. Filter + rank
    # -------------------------
    ranked = sorted(
        scored.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    return [
        {"chunk": text, "score": score}
        for text, score in ranked
        if score >= MIN_SCORE
    ][:limit]