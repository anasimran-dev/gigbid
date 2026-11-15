"""Reranking: dense top-20 candidates reordered by the reranker (cross-encoder or lexical stand-in)."""
from rag.retriever import Pipeline

PIPELINE = Pipeline("v3_rerank", rerank=True)
