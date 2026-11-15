"""Hybrid: BM25 + dense, fused with reciprocal rank fusion."""
from rag.retriever import Pipeline

PIPELINE = Pipeline("v2_hybrid", hybrid=True)
