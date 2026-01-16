from fastapi import APIRouter
from pydantic import BaseModel
import ollama
import re

from vault.ingest import scan_vault, retrieve_relevant_chunks, vector_store
from config import VAULT_PATH
from memory.memory import load_memory
from memory.context import get_context_block, update_context
from memory.extractor import extract_context_facts

# =========================
# Global vault state
# =========================
current_vault_data = None
last_vault_mtime = None

# Global context state (workaround for context storage issues)
active_subject_cache = None

router = APIRouter()

# =========================
# Models
# =========================
class AskRequest(BaseModel):
    question: str

class QuizRequest(BaseModel):
    topic: str
    answer: str | None = None


# =========================
# Helpers
# =========================
def normalize_chunks(results) -> list[str]:
    chunks = []
    for r in results:
        if isinstance(r, dict) and "chunk" in r:
            chunks.append(r["chunk"])
        elif isinstance(r, str):
            chunks.append(r)
    return chunks


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


# =========================
# Intent Classification
# =========================
def classify_intent(question: str) -> str:
    res = ollama.generate(
        model="qwen2.5:7b",
        prompt=f"""
Classify the user's message into ONE category.

- factual
- continuation
- casual

Respond with ONLY the category name.

Message:
{question}
""",
        options={"temperature": 0.0, "num_predict": 5},
    )
    return res["response"].strip().lower()


# =========================
# Vault change detection
# =========================
def get_latest_vault_mtime():
    if not VAULT_PATH.exists():
        return None
    return max(
        (p.stat().st_mtime for p in VAULT_PATH.rglob("*") if p.is_file()),
        default=None,
    )


def vault_has_changed():
    global last_vault_mtime
    latest = get_latest_vault_mtime()
    if last_vault_mtime is None:
        return True
    return latest != last_vault_mtime


# =========================
# Sync Vault
# =========================
@router.post("/sync")
def sync_vault():
    global current_vault_data, last_vault_mtime
    current_vault_data = scan_vault()
    last_vault_mtime = get_latest_vault_mtime()
    return {"status": "vault synced"}


# =========================
# Subject Extraction
# =========================
def extract_subject_tokens(question: str) -> list[str]:
    STOP = {
        "what","is","are","does","do","did","explain","define","describe",
        "tell","me","about","in","of","the","simple","terms","please",
        "how","why","when","where","which","again","it","that","this"
    }
    return [w for w in tokenize(question) if w not in STOP]


def get_active_subject():
    global active_subject_cache
    # Try context storage first
    ctx = get_context_block()
    if isinstance(ctx, dict):
        subject = ctx.get("active_subject")
        if subject:
            return subject
    # Fall back to cache
    return active_subject_cache


# =========================
# Ask (MAIN)
# =========================
@router.post("/ask")
def ask(req: AskRequest):
    global current_vault_data

    try:
        # 0. Sync
        if current_vault_data is None or vault_has_changed():
            sync_vault()

        question = req.question.strip()
        
        # DEBUG: Check context at start
        print(f"DEBUG: Context at request start: {get_context_block()}")

        # 1. Intent
        intent = classify_intent(question)
        print(f"DEBUG: Intent classified as: {intent}")

        # 2. Casual
        if intent == "casual":
            res = ollama.generate(
                model="mistral:7b-instruct",
                prompt=f"""
You are a friendly conversational assistant.
Keep it casual and short.

User:
{question}

Response:
""",
                options={"temperature": 0.7, "num_predict": 80},
            )
            return {"answer": res["response"].strip()}

        # 3. Retrieve (use active_subject for continuation queries)
        retrieval_query = question
        if intent == "continuation":
            active_subj = get_active_subject()
            print(f"DEBUG: Active subject from context: {active_subj}")
            if active_subj:
                retrieval_query = active_subj
        
        print(f"DEBUG: Retrieval query: {retrieval_query}")
        results = retrieve_relevant_chunks(retrieval_query, current_vault_data, limit=5)
        if not results:
            return {"answer": "I don't have that information in my vault yet."}

        chunks = normalize_chunks(results)
        vault_text = " ".join(chunks).lower()

        # 4. Subject resolution
        subjects = extract_subject_tokens(question)
        print(f"DEBUG: Extracted subjects: {subjects}")

        # Helper function for anchor checking
        def subject_anchored(subject: str, vault_text: str) -> bool:
            words = subject.split()
            return all(w in vault_text for w in words)

        # FIX: Try continuation if intent suggests it AND extracted subjects don't anchor
        if intent == "continuation":
            # Check if current subjects actually anchor to vault
            if not any(subject_anchored(s, vault_text) for s in subjects):
                print(f"DEBUG: Extracted subjects don't anchor, trying active_subject")
                last = get_active_subject()
                print(f"DEBUG: Got active_subject: {last}")
                if last:
                    subjects = [last]
                    print(f"DEBUG: Using active_subject, subjects now: {subjects}")

        print(f"DEBUG: Final subjects for processing: {subjects}")
        
        if not subjects:
            return {"answer": "I don't have that information in my vault yet."}

        # 5. Anchor check (SIMPLE + SAFE)
        if not any(subject_anchored(s, vault_text) for s in subjects):
            return {"answer": "I don't have that information in my vault yet."}


        # 6. Sentence grounding
        allowed = []
        for chunk in chunks:
            for sent in re.split(r'(?<=[.!?])\s+', chunk):
                sent_l = sent.lower()
                if any(s in sent_l for s in subjects):
                    allowed.append(sent.strip())

        allowed = list(dict.fromkeys(allowed))
        if not allowed:
            return {"answer": "I don't have that information in my vault yet."}

        allowed_text = "\n".join(f"- {s}" for s in allowed)
        
        # Extract key subject from allowed sentences for context memory
        allowed_lower = " ".join(allowed).lower()
        allowed_subjects = extract_subject_tokens(allowed_lower)

        # 7. Transform
        response = ollama.generate(
            model="qwen2.5:7b",
            prompt=f"""
You are a language transformer.

Rewrite ONLY the sentences below to answer the question.

RULES:
- Use ONLY the allowed sentences
- Do NOT add new information
- Do NOT explain or infer
- Do NOT mention missing knowledge
- Do NOT wrap the answer in quotes

YOU MAY:
- Rephrase
- Merge
- Reorder
- Remove redundancy

ALLOWED SENTENCES:
{allowed_text}

QUESTION:
{question}

ANSWER:
""",
            options={"temperature": 0.0, "top_p": 0.1, "num_predict": 140},
        )

        answer = response["response"].strip()

        # 8. Context memory
        global active_subject_cache
        
        # Save the subject based on what was actually discussed in allowed sentences
        # This captures what the answer is ABOUT, not just query noise words
        if allowed_subjects:
            # Use first 2 meaningful tokens from the actual answer content
            active_subject = " ".join(allowed_subjects[:2])
        elif subjects:
            # Fall back to query subjects if we can't extract from answer
            active_subject = " ".join(subjects)
        else:
            active_subject = None
        
        facts = extract_context_facts(question, answer)
        ctx = {"active_subject": active_subject}
        if isinstance(facts, dict):
            ctx.update(facts)
        print(f"DEBUG: Saving context with active_subject: {active_subject} (from allowed_subjects: {allowed_subjects[:3] if allowed_subjects else None})")
        update_context(ctx)
        # Also cache it globally as a backup
        active_subject_cache = active_subject

        return {"answer": answer}

    except Exception as e:
        print("ERROR:", e)
        return {"answer": "My brain just lagged. Say that again?"}




# =========================
# Summarize (stub)
# =========================
@router.post("/summarize")
def summarize():
    return {"summary": "Summarize mode response (stub)"}


# =========================
# Teach Mode
# =========================
@router.post("/teach")
def teach(req: AskRequest):
    scan_vault()
    memory = load_memory()
    context = vector_store.search(req.question)
    return {
        "mode": "teach",
        "question": req.question,
        "explanation_style": memory.get("learning_style"),
        "steps": [
            "First, let's understand the core idea.",
            "Then we'll look at an example.",
            "Finally, I'll ask you a question to check understanding.",
        ],
        "context": context,
    }


# =========================
# Quiz Mode
# =========================
@router.post("/quiz")
def quiz(req: QuizRequest):
    scan_vault()
    context = vector_store.search(req.topic)

    if req.answer is None:
        return {
            "mode": "quiz",
            "question": f"Can you explain: {req.topic}?",
            "context_hint": context[:1],
        }

    return {
        "mode": "quiz",
        "your_answer": req.answer,
        "feedback": "Good attempt. Here's what matters most:",
        "reference": context[:1],
    }