"""Outcome-aware ranking: boost proposals that won or got replies, demote ignored ones."""
from rag.retriever import Pipeline

PIPELINE = Pipeline("v4_outcome", outcome=True)
