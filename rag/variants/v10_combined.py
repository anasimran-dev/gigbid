"""Combined pipeline: decomposition + hybrid + rerank + outcome boost + project collapse.
Ablated one switch at a time in evals/runners/ablation.py."""
from rag.retriever import Pipeline

PIPELINE = Pipeline("v10_combined", decompose=True, hybrid=True, rerank=True, outcome=True, collapse=True)
