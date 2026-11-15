"""Dense index: embeddings + cosine similarity in NumPy.

Embedding backends (set in agent/config.yaml -> embeddings.backend):
  ollama : an open embedding model served by Ollama (nomic-embed-text by default)
  lsa    : TF-IDF + truncated SVD fitted on the corpus. No download, runs anywhere.
           Used for tests, CI and the offline evaluation. It is a weak "dense" stand-in.
"""
import json
import os
import urllib.request

import numpy as np


class LsaEmbedder:
    def __init__(self, dims: int = 128):
        self.dims = dims
        self.fitted = False

    def fit(self, texts: list[str]):
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.tfidf = TfidfVectorizer(sublinear_tf=True, stop_words="english", ngram_range=(1, 2), min_df=1)
        matrix = self.tfidf.fit_transform(texts)
        self.svd = TruncatedSVD(n_components=max(2, min(self.dims, matrix.shape[1] - 1, len(texts) - 1)), random_state=0)
        self.svd.fit(matrix)
        self.fitted = True

    def embed(self, texts: list[str]) -> np.ndarray:
        return _normalise(self.svd.transform(self.tfidf.transform(texts)))


class OllamaEmbedder:
    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model
        self.url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/embed"
        self.fitted = True

    def fit(self, texts):  # nothing to fit
        pass

    def embed(self, texts: list[str]) -> np.ndarray:
        req = urllib.request.Request(self.url, json.dumps({"model": self.model, "input": texts}).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as res:
            return _normalise(np.array(json.loads(res.read())["embeddings"], dtype=float))


def _normalise(m: np.ndarray) -> np.ndarray:
    return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)


def make_embedder(backend: str = "lsa", model: str = "nomic-embed-text"):
    return OllamaEmbedder(model) if backend == "ollama" else LsaEmbedder()


class VectorIndex:
    def __init__(self, embedder, chunks: list[dict]):
        self.embedder, self.chunks = embedder, chunks
        texts = [c["text"] for c in chunks]
        embedder.fit(texts)
        self.matrix = embedder.embed(texts)

    def search(self, query: str, k: int) -> list[tuple[dict, float]]:
        scores = self.matrix @ self.embedder.embed([query])[0]
        order = np.argsort(-scores)[:k]
        return [(self.chunks[i], float(scores[i])) for i in order]
