"""Requirement decomposition: one dense retrieval per requirement, merged with RRF."""
from rag.retriever import Pipeline

PIPELINE = Pipeline("v1_decompose", decompose=True)
