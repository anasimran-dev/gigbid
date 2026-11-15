"""Small BM25 (Okapi) index. No external dependency."""
import math
from collections import Counter

from rag.skills import tokenize


class BM25Index:
    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.docs = [Counter(tokenize(c["text"])) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / max(1, len(self.docs))
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int) -> list[tuple[dict, float]]:
        terms = tokenize(query)
        scored = []
        for i, doc in enumerate(self.docs):
            s = 0.0
            for t in terms:
                f = doc.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg))
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        return [(self.chunks[i], s) for s, i in scored[:k]]
