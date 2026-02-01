import faiss
import ollama
import numpy as np

class VectorStore:
    def __init__(self, model_name="bge-large:latest"):
        self.model_name = model_name
        self.index = None
        self.chunks = []
        # Most embedding models have context limits around 512-8192 tokens
        # We'll use a conservative character limit (roughly 400-500 tokens)
        self.max_chars = 2000

    def _truncate_text(self, text: str) -> str:
        """Truncate text to fit within embedding model's context window"""
        if len(text) <= self.max_chars:
            return text
        # Truncate and add indicator
        return text[:self.max_chars] + "..."

    def build(self, chunks: list[str]):
        if not chunks:
            return

        print(f"🔨 Building vector store with {len(chunks)} chunks...")
        
        embeddings = []
        valid_chunks = []
        
        for i, chunk in enumerate(chunks):
            try:
                # Truncate if needed
                processed_chunk = self._truncate_text(chunk)
                
                # Get embedding
                response = ollama.embeddings(model=self.model_name, prompt=processed_chunk)
                embeddings.append(response['embedding'])
                valid_chunks.append(chunk)  # Store original chunk
                
                # Progress indicator
                if (i + 1) % 50 == 0:
                    print(f"  ✅ Embedded {i + 1}/{len(chunks)} chunks")
                    
            except Exception as e:
                print(f"  ⚠️ Skipping chunk {i} due to error: {str(e)[:100]}")
                continue

        if not embeddings:
            print("❌ No embeddings created")
            return

        embeddings = np.array(embeddings, dtype='float32')

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)

        self.chunks = valid_chunks
        print(f"✅ Vector store built with {len(self.chunks)} embeddings")

    def search(self, query: str, k: int = 3):
        if self.index is None or not self.chunks:
            return []

        try:
            # Truncate query too
            processed_query = self._truncate_text(query)
            
            response = ollama.embeddings(model=self.model_name, prompt=processed_query)
            query_vec = [response['embedding']]
            
            query_vec = np.array(query_vec, dtype='float32')
            
            distances, indices = self.index.search(query_vec, k)

            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.chunks):
                    # Convert L2 distance to similarity score (lower distance = higher similarity)
                    # We use 1 / (1 + distance) to get a 0-1 score
                    similarity = 1 / (1 + float(distance))
                    results.append({
                        "chunk": self.chunks[idx],
                        "score": similarity
                    })

            return results
            
        except Exception as e:
            print(f"❌ Search error: {str(e)}")
            return []