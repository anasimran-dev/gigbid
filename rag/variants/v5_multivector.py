"""Multi-vector items: summary, README, code and proposals are indexed separately but returned as one project."""
from rag.retriever import Pipeline

PIPELINE = Pipeline("v5_multivector", collapse=True)
