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
    """
    Smarter chunker:
    1. Protects abbreviations (Mr. Mrs. Dr. Adv. Smt. Pvt. Ltd. etc.)
    2. Splits into sentences properly
    3. Groups sentences into chunks of ~chunk_size words with overlap
    4. Never splits mid-sentence
    """
    import re

    # ---- Step 1: Protect abbreviations from being treated as sentence ends ----
    abbreviations = [
        'Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Adv', 'Smt', 'Shri',
        'Pvt', 'Ltd', 'Inc', 'Corp', 'Co', 'St', 'Ave', 'Dept',
        'vs', 'etc', 'approx', 'govt', 'Govt', 'No', 'Fig', 'Jan',
        'Feb', 'Mar', 'Apr', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct',
        'Nov', 'Dec', 'approx', 'est', 'ref', 'vol', 'pg'
    ]
    protected = text
    for abbr in abbreviations:
        protected = re.sub(rf'\b{abbr}\.', f'{abbr}<P>', protected)

    # ---- Step 2: Split into sentences ----
    sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    raw_sentences = sentence_endings.split(protected)

    # Restore abbreviations
    sentences = []
    for s in raw_sentences:
        s = s.strip()
        for abbr in abbreviations:
            s = s.replace(f'{abbr}<P>', f'{abbr}.')
        if len(s.split()) >= 4:  # skip very short fragments
            sentences.append(s)

    if not sentences:
        # fallback: return whole text as one chunk if nothing parsed
        return [text.strip()] if text.strip() else []

    # ---- Step 3: Group sentences into chunks ----
    chunks = []
    current_sentences = []
    current_word_count = 0

    for sentence in sentences:
        word_count = len(sentence.split())

        # If adding this sentence exceeds chunk size, save current chunk and start new
        if current_word_count + word_count > chunk_size and current_sentences:
            chunk_text_str = ' '.join(current_sentences)
            if chunk_text_str.strip():
                chunks.append(chunk_text_str.strip())

            # Overlap: keep last N words worth of sentences
            overlap_sentences = []
            overlap_words = 0
            for s in reversed(current_sentences):
                w = len(s.split())
                if overlap_words + w <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_words += w
                else:
                    break

            current_sentences = overlap_sentences
            current_word_count = overlap_words

        current_sentences.append(sentence)
        current_word_count += word_count

    # Save last chunk
    if current_sentences:
        chunk_text_str = ' '.join(current_sentences)
        if chunk_text_str.strip():
            chunks.append(chunk_text_str.strip())

    return chunks if chunks else [text.strip()]

    
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