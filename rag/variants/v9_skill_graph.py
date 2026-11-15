"""Skill graph (GraphRAG): skills, projects, industries and outcomes as a graph."""
from rag.retriever import Pipeline

PIPELINE = Pipeline("v9_skill_graph", graph=True)
