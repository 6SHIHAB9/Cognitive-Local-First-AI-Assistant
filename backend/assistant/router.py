from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import ollama
import re
import time
import os
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

from fastapi.responses import StreamingResponse
import json
from vault.ingest import scan_vault, retrieve_relevant_chunks
from config import VAULT_PATH
from context_manager import context_manager

from models.reranker.loader import Reranker

from models.sufficiency_models.scorer import SufficiencyScorer

from models.topic_coherence_models.loader import load_topic_coherence_scorer

# =========================
# Global vault state
# =========================
current_vault_data = None
last_vault_mtime = None

router = APIRouter()

# =========================
# Model 1: Intent classifier
# =========================
INTENT_LABEL_MAP = {
    "LABEL_0": "factual",
    "LABEL_1": "continuation",
    "LABEL_2": "casual"
}

intent_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

intent_model_path = os.path.abspath("models/intent_models/intent_model_output/final")
intent_model = AutoModelForSequenceClassification.from_pretrained(
    intent_model_path,
    local_files_only=True
).to(intent_device)

intent_tokenizer = AutoTokenizer.from_pretrained(
    intent_model_path,
    local_files_only=True,
    fix_mistral_regex=True
)

intent_model.eval()

# =========================
# Model 2: Reference Ranker
# =========================


# =========================
# Model 3: Reranker (replaces binary grounding scorer)
# =========================
reranker = Reranker()

# =========================
# Model 4: Sufficiency Scorer
# =========================
sufficiency_scorer = SufficiencyScorer(
    model_path="models/sufficiency_models",
    base_model="sentence-transformers/all-MiniLM-L6-v2"
)

SUFFICIENCY_THRESHOLD = 0.60

# =========================
# Model 5: Topic Coherence Scorer
# =========================
topic_scorer = load_topic_coherence_scorer()


# =========================
# Models
# =========================
class AskRequest(BaseModel):
    question: str


# =========================
# Helpers
# =========================

def deduplicate_sentences(sentences: list[str]) -> list[str]:
    """
    Remove duplicate sentences while preserving order.
    Uses normalized comparison to catch near-duplicates.
    """
    seen = set()
    unique = []
    
    for sentence in sentences:
        # Normalize for comparison (lowercase, strip whitespace)
        normalized = sentence.strip().lower()
        
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(sentence)
    
    return unique


def normalize_chunks(results) -> list[str]:
    chunks = []
    for r in results:
        if isinstance(r, dict) and "chunk" in r:
            chunks.append(r["chunk"])
        elif isinstance(r, str):
            chunks.append(r)
    return chunks

from sentence_transformers import SentenceTransformer, util

topic_embedder = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2",
    device="cuda" if torch.cuda.is_available() else "cpu"
)


def select_dominant_topic(sentences: list[str], similarity_threshold=0.6) -> list[str]:
    """
    Clusters sentences by semantic similarity and keeps the largest cluster.
    """
    if len(sentences) <= 2:
        return sentences

    embeddings = topic_embedder.encode(sentences, convert_to_tensor=True)
    sim_matrix = util.cos_sim(embeddings, embeddings)

    clusters = []
    visited = set()

    for i in range(len(sentences)):
        if i in visited:
            continue

        cluster = [i]
        visited.add(i)

        for j in range(len(sentences)):
            if j not in visited and sim_matrix[i][j] >= similarity_threshold:
                cluster.append(j)
                visited.add(j)

        clusters.append(cluster)

    # pick largest cluster
    dominant = max(clusters, key=len)
    return [sentences[i] for i in dominant]


def score_evidence_roles(question: str, sentences: list[str]):
    """
    Scores sentences by how explanatory they are *for this question*.
    """
    q_embed = topic_embedder.encode(question, convert_to_tensor=True)
    s_embeds = topic_embedder.encode(sentences, convert_to_tensor=True)

    scores = util.cos_sim(q_embed, s_embeds)[0]

    weighted = []
    for score, sent in zip(scores, sentences):
        weighted.append((float(score), sent))

    # highest explanatory relevance first
    weighted.sort(key=lambda x: x[0], reverse=True)
    return weighted

def filter_by_topic_coherence(
    question: str,
    sentences: list[str],
    top_k: int = 8
) -> list[str]:
    if not sentences:
        return []

    scored = []
    for s in sentences:
        score = topic_scorer.score(question, s)
        scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [s for _, s in scored[:top_k]]





def split_into_sentences(chunks: list[str]) -> list[str]:
    sentences = []
    for chunk in chunks:
        parts = re.split(r'(?<=[.!?])\s+', chunk)
        sentences.extend([p.strip() for p in parts if len(p.strip()) >= 10])
    return sentences


# =========================
# Intent Classification
# =========================
def classify_intent(question: str, previous_q: str = None) -> str:

    # First pass: classify WITHOUT previous context
    text_solo = f"Current: {question}"
    inputs = intent_tokenizer(
        text_solo,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=512
    )
    inputs = {k: v.to(intent_device) for k, v in inputs.items()}

    with torch.inference_mode():
        logits = intent_model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        casual_confidence = probs[2].item()

    print(f"🎲 PROBS — factual:{probs[0]:.3f} continuation:{probs[1]:.3f} casual:{probs[2]:.3f}")

    if casual_confidence > 0.6:
        return "casual"

    # Second pass: classify WITH previous context
    if previous_q:
        text = f"Previous: {previous_q} Current: {question}"
    else:
        text = f"Current: {question}"

    inputs = intent_tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=512
    )
    inputs = {k: v.to(intent_device) for k, v in inputs.items()}

    with torch.inference_mode():
        logits = intent_model(**inputs).logits
        pred_id = torch.argmax(logits, dim=-1).item()

    return INTENT_LABEL_MAP.get(f"LABEL_{pred_id}", "factual")

# =========================
# ML BASED RETRIEVAL
# =========================
# =========================
# ML BASED RETRIEVAL
# =========================
def retrieve_for_question(question: str, intent: str, vault_data: dict) -> list[str]:
    results = retrieve_relevant_chunks(question, vault_data, limit=20) 
    chunks = normalize_chunks(results)


    return chunks[:12] 


# =========================
# ML-BASED GROUNDING
# =========================
def ml_ground_sentences(
    question: str,
    sentences: list[str],
    intent: str,
    top_k: int = 8,
    min_relevance: float = 0.25,
) -> list[str]:

    if not sentences:
        return []

    print("🧪 SENTENCES BEFORE RERANKING:")
    for s in sentences:
        print("  >", s[:80])

    # Build relevance query (combined context for continuation)
    relevance_query = question

    # Lower threshold for short/pronoun questions
    if len(question.split()) <= 6:
        min_relevance = 0.20
        print(f"📏 Short question detected → min_relevance=0.20")

    if intent == "continuation":
        prev_q = context_manager.get_previous_question()
        if prev_q:
            prev_embed = topic_embedder.encode(prev_q, convert_to_tensor=True)
            curr_embed = topic_embedder.encode(question, convert_to_tensor=True)
            topic_sim = float(util.cos_sim(prev_embed, curr_embed)[0][0])

            if topic_sim >= 0.30:
                relevance_query = prev_q + " " + question
                print(f"🔄 Combined context (sim={topic_sim:.3f}): '{relevance_query}'")
            else:
                print(f"⚠️ Topics differ (sim={topic_sim:.3f}) → using current question only")
            min_relevance = 0.20

    # Step 1: Cosine relevance pre-filter (removes clearly off-topic sentences)
    q_embed = topic_embedder.encode(relevance_query, convert_to_tensor=True)
    s_embeds = topic_embedder.encode(sentences, convert_to_tensor=True)
    relevance_scores = util.cos_sim(q_embed, s_embeds)[0]

    candidates = []
    for sentence, rel_score in zip(sentences, relevance_scores):
        rel_score = float(rel_score)
        if rel_score < min_relevance:
            print(f"  ❌ BELOW RELEVANCE ({rel_score:.3f}): {sentence[:60]}...")
            continue
        candidates.append(sentence)

    if not candidates:
        return []

    # Step 2: Rerank candidates with cross-encoder (no threshold, just ranking)
    ranked = reranker.rerank(relevance_query, candidates)

    print(f"📊 RERANKED SENTENCES:")
    for s, score in ranked:
        print(f"  ({score:.3f}): {s[:80]}...")

    # Step 3: Return top K — no hard threshold
    top = [s for s, _ in ranked[:top_k]]
    return top


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
    """Check if vault has changed since last sync"""
    global last_vault_mtime
    latest = get_latest_vault_mtime()
    
    if last_vault_mtime is None:
        return True
    
    if latest is None:
        return False
    
    return latest > last_vault_mtime


# =========================
# Sync Vault (Internal)
# =========================
def _internal_sync():
    """Internal sync function that returns sync info"""
    global current_vault_data, last_vault_mtime

    print("🔄 SYNCING VAULT...")
    
    current_vault_data = scan_vault()
    last_vault_mtime = get_latest_vault_mtime()
    indexed_at = time.time()

    sync_info = {
        "vault_path": str(current_vault_data["vault_path"]),
        "file_count": current_vault_data["file_count"],
        "empty_files": current_vault_data["empty_files"],
        "indexed_files": current_vault_data["indexed_files"],
        "last_indexed": indexed_at
    }
    
    print(f"✅ VAULT SYNCED: {sync_info['indexed_files']} files indexed")
    
    return sync_info


# =========================
# Sync Vault (API Endpoint)
# =========================
@router.post("/sync")
def sync_vault():
    """Manual sync endpoint"""
    return _internal_sync()


# =========================
# Ask (MAIN)
# =========================
@router.post("/ask")
def ask(req: AskRequest):
    global current_vault_data

    try:
        # 0. Sync and track if it happened
        sync_info = None
        if current_vault_data is None or vault_has_changed():
            sync_info = _internal_sync()

        question = req.question.strip()
        
        print(f"\n📝 QUESTION: {question}")
        
        # =========================
        # 1. Intent Classification
        # =========================
        intent = classify_intent(question, context_manager.get_previous_question())

        previous_q = context_manager.get_previous_question()
        use_previous_context = False

        # =========================
        # Topic + Explanation Continuity
        # =========================
        # =========================
        # Topic Continuity Check
        # =========================
        if intent == "continuation" and previous_q:
            # Use cosine similarity for question-to-question comparison
            prev_embed = topic_embedder.encode(previous_q, convert_to_tensor=True)
            curr_embed = topic_embedder.encode(question, convert_to_tensor=True)
            
            # Topic similarity: how similar are the two questions?
            topic_score = float(util.cos_sim(prev_embed, curr_embed)[0][0])
            
            print(f"🧠 TOPIC SCORE: {topic_score:.4f}")

            # If the score is below 0.35, it is a brand new topic. Period.
            if topic_score >= 0.35:
                use_previous_context = True
            else:
                print("🔁 Topic drift detected → re-anchoring topic")
                use_previous_context = False
                context_manager.clear_session()
                context_manager.set_topic_anchor(question)
                intent = "factual" # <--- This fixes the intent!
        print(f"🎯 INTENT: {intent}")
        # Continuation without history is invalid
        # Force factual if continuation but no history
        if intent == "continuation" and not previous_q:
            print("🔄 No history → forcing factual")
            intent = "factual"

        # Clear history only for fresh factual questions
        if intent == "factual":
            previous_q = context_manager.get_previous_question()
            if previous_q:
                # Use cosine similarity here too
                prev_embed = topic_embedder.encode(previous_q, convert_to_tensor=True)
                curr_embed = topic_embedder.encode(question, convert_to_tensor=True)
                topic_score = float(util.cos_sim(prev_embed, curr_embed)[0][0])
                
                if topic_score < 0.25:
                    context_manager.clear_session()

        # 2. Casual Chat
        if intent == "casual":
            previous_q = context_manager.get_previous_question()
            previous_a = None
            if previous_q and hasattr(context_manager, 'conversation_history') and context_manager.conversation_history:
                previous_a = context_manager.conversation_history[-1].get('answer', '')

            context_info = ""
            if previous_q and previous_a:
                context_info = f"\nPrevious conversation:\nUser: {previous_q}\nYou: {previous_a[:150]}...\n"

            casual_prompt = f"""You are a friendly conversational assistant.
        Keep it casual and short.{context_info}

        User:
        {question}

        Response:
        """

            def generate_casual():
                stream = ollama.generate(
                    model="gemma2:2b-instruct-q4_K_M",
                    prompt=casual_prompt,
                    stream=True,
                    options={"temperature": 0.7, "num_predict": 80},
                )
                for chunk in stream:
                    token = chunk.get("response", "")
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                yield f"data: {json.dumps({'done': True, 'metadata': None, 'sync_info': sync_info})}\n\n"

            return StreamingResponse(
                generate_casual(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
            )

        # 3. RETRIEVAL
        effective_question = question

        if intent == "continuation" and use_previous_context:
            effective_question = previous_q + " " + question

        chunks = retrieve_for_question(effective_question, intent, current_vault_data)

        print(f"📦 CHUNKS RETRIEVED: {len(chunks)}")
        
        if not chunks:
            response_data = {"answer": "I don't have that information in my vault yet."}
            if sync_info:
                response_data["sync_performed"] = sync_info
            return response_data

# =========================
        # 4. CHUNK-LEVEL ML PIPELINE
        # =========================
        
        # We start with the 75-word chunks from ingest.py
        small_chunks = chunks 
        print(f"🧪 SMALL CHUNKS BEFORE RERANKING: {len(small_chunks)}")

        # Build relevance query for your reranker
        relevance_query = question
        if intent == "continuation" and use_previous_context:
            relevance_query = previous_q + " " + question

        # -> Run YOUR Cross-Encoder Reranker on the small chunks! <-
        ranked_small_chunks = reranker.rerank(relevance_query, small_chunks)
        
        print(f"📊 ML RERANKED CHUNKS:")
        for s, score in ranked_small_chunks[:5]:
            print(f"  ({score:.3f}): {s[:80].replace(chr(10), ' ')}...")

        # =========================
        # THE PIVOT: Swap top ML-ranked small chunks for Massive Blocks
        # =========================
        try:
            with open("parent_docs.json", "r", encoding="utf-8") as f:
                PARENT_STORE = json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load parent_docs.json: {e}")
            PARENT_STORE = {}

        allowed_blocks = []
        seen_parents = set()

        for chunk_text, ml_score in ranked_small_chunks:
 
                
            # Find the hidden Parent ID
            match = re.search(r'\[PARENT_ID:(parent_[a-f0-9]+)\]', chunk_text)
            if match:
                pid = match.group(1)
                if pid not in seen_parents:
                    seen_parents.add(pid)
                    # Fetch the massive 800-word block
                    big_text = PARENT_STORE.get(pid, chunk_text)
                    allowed_blocks.append(big_text)
            else:
                if chunk_text not in seen_parents:
                    seen_parents.add(chunk_text)
                    allowed_blocks.append(chunk_text)

            # We only need the top 3 massive blocks (that's 2400 words of perfect context)
            if len(allowed_blocks) >= 3:
                break

        print(f"✅ PARENT BLOCKS READY: {len(allowed_blocks)}")

        if not allowed_blocks:
            print("❌ NO ML-APPROVED BLOCKS - REFUSING")
            response_data = {"answer": "I don't have that information in my vault yet."}
            if sync_info:
                response_data["sync_performed"] = sync_info
            return response_data

        # =========================
        # SUFFICIENCY CHECK (Run your model on the final massive blocks)
        # =========================
        suff_score = None
        if intent == "continuation":
            suff_score = sufficiency_scorer.score(
                question=question,
                sentences=allowed_blocks, # Passing the big blocks to your scorer
                intent=intent
            )
            print(f"🧪 SUFFICIENCY SCORE: {suff_score:.4f} (threshold: {SUFFICIENCY_THRESHOLD})")
            if suff_score < SUFFICIENCY_THRESHOLD:
                print("🚫 INSUFFICIENT EVIDENCE — REFUSING")
                response_data = {
                    "answer": "I don't have enough information in my vault to answer that confidently.",
                    "metadata": {"intent": intent, "sentences_grounded": len(allowed_blocks), "sufficiency_score": suff_score}
                }
                if sync_info:
                    response_data["sync_performed"] = sync_info
                return response_data

        # Combine the massive blocks for the final LLM prompt
        allowed_text = "\n\n---\n\n".join(allowed_blocks)

  

        # 5. ANSWER GENERATION
        # Build context for continuation
        context_instruction = ""
        if intent == "continuation":
            previous_q = context_manager.get_previous_question()
            if previous_q:
                prev_lower = previous_q.lower()
                if prev_lower.startswith(("why", "what happens", "why is")):
                    context_instruction = (
                        "CONTEXT: This is a WHY follow-up.\n"
                        "Explain CONSEQUENCES, IMPACTS, or RISKS.\n"
                        "Do NOT restate the original fact.\n"
                    )
                elif prev_lower.startswith("how"):
                    context_instruction = (
                        "CONTEXT: This is a HOW follow-up.\n"
                        "Explain the MECHANISM or PROCESS.\n"
                    )

        prompt = f"""You are answering a question using ONLY the provided sentences.

RULES:
- Use ONLY the allowed sentences below
- You MAY rephrase and COMBINE them
- If the question asks "why", "why is that an issue", or "what happens if":
  → EXPLAIN CONSEQUENCES or IMPACTS implied by the sentences
  → Do NOT simply restate the sentences
- Do NOT add external facts
- Keep the answer concise and explanatory
- Answer ONLY what is asked
- Do NOT add solutions, alternatives, or extra context
- Stick to the specific question

{context_instruction}

ALLOWED SENTENCES:
{allowed_text}

QUESTION:
{question}

ANSWER:"""

        metadata = {
            "chunks_retrieved": len(chunks),
            "sentences_grounded": len(allowed_blocks),
            "intent": intent
        }

        def generate():
            full_answer = ""
            stream = ollama.generate(
                model="gemma2:2b-instruct-q4_K_M",
                prompt=prompt,
                stream=True,
                options={"temperature": 0.0, "top_p": 0.1, "num_predict": 150},
            )
            for chunk in stream:
                token = chunk.get("response", "")
                if token:
                    full_answer += token
                    print(token, end="", flush=True)
                    yield f"data: {json.dumps({'token': token})}\n\n"

            print()
            if full_answer.strip():
                context_manager.add_turn(question, full_answer.strip())

            yield f"data: {json.dumps({'done': True, 'metadata': metadata, 'sync_info': sync_info})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

        

    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()
        return {"answer": "My brain just lagged. Say that again?"}