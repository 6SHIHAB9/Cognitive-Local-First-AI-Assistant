import json
import uuid
import re
from pathlib import Path
from collections import defaultdict

from config import VAULT_PATH
from vault.vector_store import VectorStore

# --------------------
# Parent Document Store Setup
# --------------------
PARENT_STORE_FILE = Path("parent_docs.json")
PARENT_STORE = {}

# Load existing parents into memory if they exist
if PARENT_STORE_FILE.exists():
    try:
        with open(PARENT_STORE_FILE, "r", encoding="utf-8") as f:
            PARENT_STORE = json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load parent docs: {e}")

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
                blocks = page.get_text("blocks")
                blocks.sort(key=lambda b: (b[1], b[0]))
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
                if block.tag == qn('w:p'):
                    runs = block.findall('.//' + qn('w:t'))
                    text = "".join(r.text for r in runs if r.text)
                    if text.strip():
                        parts.append(text.strip())
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

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150):
    section_pattern = re.compile(r'(?=^#{1,3}\s)', re.MULTILINE)
    sections = section_pattern.split(text)
    sections = [s.strip() for s in sections if s.strip()]

    if len(sections) <= 1:
        sections = re.split(r'\n\s*\n', text)
        sections = [s.strip() for s in sections if s.strip()]

    if len(sections) <= 1:
        sections = re.split(r'\n(?=[A-Z][a-z]+ [A-Z]|[A-Z][a-z]+\n)', text)
        sections = [s.strip() for s in sections if s.strip()]

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
    parent_store_temp = {}

    if not VAULT_PATH.exists():
        return {"vault_path": str(VAULT_PATH), "file_count": 0, "empty_files": 0, "indexed_files": 0, "files": []}

    print(f"📂 Scanning vault: {VAULT_PATH}")

    for path in VAULT_PATH.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in [".txt", ".md", ".pdf", ".docx"]:
            continue

        content = read_text_file(path)
        has_content = bool(content.strip())
        if not has_content:
            continue

        # 1. Chop into massive 800-word blocks (The Parents)
        big_chunks = chunk_text(content, chunk_size=800, overlap=150)
        file_small_chunks = []

        for big_chunk in big_chunks:
            # 2. Give the massive block an ID and save it
            parent_id = f"parent_{uuid.uuid4().hex[:8]}"
            parent_store_temp[parent_id] = big_chunk

            # 3. Chop the block into tiny 75-word search chunks
            small_chunks = chunk_text(big_chunk, chunk_size=75, overlap=15)
            
            for small in small_chunks:
                # 4. Inject the ID into the tiny chunks
                tagged_chunk = f"[PARENT_ID:{parent_id}]\n{small}"
                file_small_chunks.append(tagged_chunk)
                all_chunks.append(tagged_chunk)

        files.append({
            "name": path.name,
            "path": str(path),
            "extension": path.suffix.lower(),
            "empty": not has_content,
            "chunk_count": len(file_small_chunks),
            "chunks": file_small_chunks,
        })

        if file_small_chunks:
            print(f"  ✅ {path.name}: {len(file_small_chunks)} search chunks created.")

    # Save the Parents to disk
    global PARENT_STORE
    PARENT_STORE = parent_store_temp
    with open(PARENT_STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(PARENT_STORE, f)

    if all_chunks:
        vector_store.build(all_chunks)
    else:
        print("⚠️ No content found to index")

    empty_files = sum(1 for f in files if f["empty"])
    indexed_files = sum(1 for f in files if not f["empty"])

    print(f"\n📊 Scan complete:")
    print(f"  Files found: {len(files)}")
    print(f"  Indexed: {indexed_files}")
    print(f"  Total Search Chunks: {len(all_chunks)}")
    print(f"  Total Parent Documents: {len(PARENT_STORE)}")

    return {
        "vault_path": str(VAULT_PATH),
        "file_count": len(files),
        "empty_files": empty_files,
        "indexed_files": indexed_files,
        "files": files,
    }


# --------------------
# retrieval
# --------------------
MIN_SCORE = 0.2

def retrieve_relevant_chunks(query: str, vault_data: dict, limit: int = 15):
    scored = defaultdict(float)

    # Search the small chunks
    semantic_results = vector_store.search(query, k=limit * 3)
    for r in semantic_results:
        text = extract_text(r)
        if text: scored[text] += 0.7 * extract_score(r)

    for file in vault_data.get("files", []):
        for chunk in file.get("chunks", []):
            if isinstance(chunk, str):
                ks = keyword_score(query, chunk)
                if ks > 0: scored[chunk] += 0.3 * ks

    ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)

    # Return ONLY the small chunks with their hidden tags!
    return [{"chunk": text, "score": score} for text, score in ranked if score >= MIN_SCORE][:limit]