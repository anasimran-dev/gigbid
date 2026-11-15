"""Naive dense baseline: fixed chunks, top-k cosine on the whole job post."""
from rag.retriever import Pipeline

PIPELINE = Pipeline("v0_naive")
