"""Retriever factory. Every variant is the same pipeline with different switches,
so the comparison and the ablation rerun with one command (evals/runners/rag_eval.py).

    get_retriever("v2_hybrid").retrieve(persona, job, spec, k=5) -> list[hit]

A hit is an evidence item plus "score". `spec` is the Job Analyst's JobSpec (dict).
"""
import importlib
import math
from dataclasses import dataclass
from functools import lru_cache

from rag.index.bm25 import BM25Index
from rag.index.graph import SkillGraph
from rag.index.vector import VectorIndex, make_embedder
from rag.ingest.loaders import chunk, load_persona
from rag.skills import VOCAB, extract_skills, tokenize

VARIANTS = ["v0_naive", "v1_decompose", "v2_hybrid", "v3_rerank", "v4_outcome", "v5_multivector", "v9_skill_graph", "v10_combined"]
OUTCOME_BOOST = {"won": 1.3, "replied": 1.15, "ignored": 0.5}


class Corpus:
    """All indexes for one persona. Rebuilt when the user adds work (incremental re-index)."""

    def __init__(self, persona: str, embed_backend: str = "lsa", embed_model: str = "nomic-embed-text"):
        self.items = load_persona(persona)
        self.by_id = {it["id"]: it for it in self.items}
        self.chunks = [c for it in self.items for c in chunk(it)]
        self.vector = VectorIndex(make_embedder(embed_backend, embed_model), self.chunks)
        self.bm25 = BM25Index(self.chunks)
        self.graph = SkillGraph(self.items)


@lru_cache(maxsize=8)
def get_corpus(persona: str, embed_backend: str = "lsa", embed_model: str = "nomic-embed-text") -> Corpus:
    return Corpus(persona, embed_backend, embed_model)


def reindex(persona: str):
    get_corpus.cache_clear()


def job_text(job: dict) -> str:
    return f"{job.get('title', '')}. {job.get('description', '')}"


def requirements(job: dict, spec: dict | None) -> list[str]:
    """One query per requirement. Falls back to the whole post when nothing was extracted."""
    spec = spec or {}
    reqs = [expand(s) for s in spec.get("required_skills", [])] + list(spec.get("deliverables", []))
    return reqs or [job_text(job)]


def expand(skill: str) -> str:
    """A skill name alone is a poor query, so add its aliases and the plain-language hint."""
    v = VOCAB.get(skill)
    return f"{skill} {' '.join(v['aliases'])} {v['hint']}" if v else skill


def lexical_rerank(query: str, docs: list[str]) -> list[float]:
    """CPU-only stand-in for a cross-encoder: skill overlap (alias-aware) + rare-token overlap."""
    q_skills, q_tokens = set(extract_skills(query)), set(tokenize(query))
    out = []
    for d in docs:
        d_skills, d_tokens = set(extract_skills(d)), set(tokenize(d))
        # cosine over skill sets: a document that lists every skill (CV, keyword-stuffed proposal) scores low
        skill = len(q_skills & d_skills) / math.sqrt(len(q_skills) * len(d_skills)) if q_skills and d_skills else 0.0
        token = len(q_tokens & d_tokens) / math.sqrt(len(q_tokens) * max(1, len(d_tokens))) if q_tokens else 0.0
        out.append(0.7 * skill + 0.3 * token)
    return out


@lru_cache(maxsize=1)
def _cross_encoder(model: str):
    from sentence_transformers import CrossEncoder
    return CrossEncoder(model)


def rerank_scores(query: str, docs: list[str], backend: str, model: str) -> list[float]:
    if backend == "cross_encoder":
        return [float(s) for s in _cross_encoder(model).predict([(query, d) for d in docs])]
    return lexical_rerank(query, docs)


@dataclass
class Pipeline:
    name: str
    decompose: bool = False
    hybrid: bool = False
    rerank: bool = False
    outcome: bool = False
    graph: bool = False
    collapse: bool = False  # multi-vector idea: many items about one project count as one result
    pool: int = 30  # candidates kept before reranking

    def retrieve(self, persona: str, job: dict, spec: dict | None = None, k: int = 5, cfg: dict | None = None) -> list[dict]:
        cfg = cfg or {}
        emb, rer = cfg.get("embeddings", {}), cfg.get("reranker", {})
        corpus = get_corpus(persona, emb.get("backend", "lsa"), emb.get("model", "nomic-embed-text"))
        if self.graph:
            skills = (spec or {}).get("required_skills") or extract_skills(job_text(job))
            return [{**it, "score": s} for it, s in corpus.graph.search(skills, job.get("industry", ""), k)]

        queries = requirements(job, spec) if self.decompose else [job_text(job)]
        fused: dict[str, float] = {}
        for q in queries:
            rankings = [corpus.vector.search(q, self.pool)]
            if self.hybrid:
                rankings.append(corpus.bm25.search(q, self.pool))
            if len(queries) == 1 and len(rankings) == 1:  # plain cosine top-k (V0)
                for c, s in rankings[0]:
                    fused[c["item_id"]] = max(fused.get(c["item_id"], -1.0), s)
                continue
            for ranking in rankings:  # reciprocal rank fusion over chunks -> items
                seen = set()
                for rank, (c, _) in enumerate(ranking):
                    if c["item_id"] not in seen:
                        seen.add(c["item_id"])
                        fused[c["item_id"]] = fused.get(c["item_id"], 0.0) + 1.0 / (60 + rank + 1)
        ranked = sorted(fused.items(), key=lambda x: -x[1])[: self.pool]
        if self.rerank and ranked:
            query = job_text(job) + " " + " ".join((spec or {}).get("required_skills", []))
            scores = rerank_scores(query, [corpus.by_id[i]["text"] for i, _ in ranked],
                                   rer.get("backend", "lexical"), rer.get("model", "BAAI/bge-reranker-v2-m3"))
            ranked = sorted(zip([i for i, _ in ranked], scores), key=lambda x: -x[1])
        if self.outcome:
            ranked = sorted(((i, s * OUTCOME_BOOST.get(corpus.by_id[i]["outcome"], 1.0)) for i, s in ranked), key=lambda x: -x[1])
        if self.collapse:
            seen, kept = set(), []
            for i, s in ranked:
                key = corpus.by_id[i]["project"] or i
                if key not in seen:
                    seen.add(key)
                    kept.append((i, s))
            ranked = kept
        return [{**corpus.by_id[i], "score": float(s)} for i, s in ranked[:k]]


def get_retriever(variant: str) -> Pipeline:
    """Each variant lives in rag/variants/<name>.py and exposes PIPELINE."""
    return importlib.import_module(f"rag.variants.{variant}").PIPELINE


def to_projects(hits: list[dict]) -> list[str]:
    """Collapse hits to distinct projects in rank order (the same project is described several ways)."""
    seen = []
    for h in hits:
        if h["project"] and h["project"] not in seen:
            seen.append(h["project"])
    return seen
