import faiss
from sentence_transformers import SentenceTransformer

class VectorStore:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.chunks = []

    def build(self, chunks: list[str]):
        if not chunks:
            return

        embeddings = self.model.encode(chunks, convert_to_numpy=True)

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)

        self.chunks = chunks

    def search(self, query: str, k: int = 3):
        if self.index is None:
            return []

        query_vec = self.model.encode([query], convert_to_numpy=True)
        distances, indices = self.index.search(query_vec, k)

        results = []
        for idx in indices[0]:
            if idx < len(self.chunks):
                results.append(self.chunks[idx])

        return results
