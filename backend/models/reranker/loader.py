from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, sentences: list[str]) -> list[tuple[str, float]]:
        if not sentences:
            return []
        pairs = [(query, s) for s in sentences]
        scores = self.model.predict(pairs)
        ranked = sorted(zip(sentences, scores), key=lambda x: x[1], reverse=True)
        return ranked