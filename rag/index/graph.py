"""Skill graph (V9): skills, projects, industries and outcomes as a NetworkX graph.

Answers questions like "have I done X for a client in Y industry?" by walking
skill -> project and industry -> project edges instead of comparing text.
"""
import math

import networkx as nx

from rag.skills import extract_skills


class SkillGraph:
    def __init__(self, items: list[dict]):
        self.g = nx.Graph()
        self.items_by_project: dict[str, list[dict]] = {}
        for it in items:
            if not it["project"]:
                continue
            p = ("project", it["project"])
            self.items_by_project.setdefault(it["project"], []).append(it)
            for s in set(it["skills"]) | set(extract_skills(it["text"])):
                self.g.add_edge(("skill", s), p)
            if it["industry"]:
                self.g.add_edge(("industry", it["industry"]), p)
            if it["outcome"] in ("won", "replied"):
                self.g.add_edge(("outcome", "positive"), p)
        n_projects = max(1, len(self.items_by_project))
        self.idf = {node[1]: math.log(1 + n_projects / self.g.degree(node))
                    for node in self.g if node[0] == "skill"}

    def search(self, skills: list[str], industry: str, k: int) -> list[tuple[dict, float]]:
        scores: dict[str, float] = {}
        for s in skills:
            node = ("skill", s)
            if node in self.g:
                for _, pid in self.g[node]:
                    scores[pid] = scores.get(pid, 0) + self.idf[s]
        for pid in list(scores):
            p = ("project", pid)
            if industry and self.g.has_edge(("industry", industry), p):
                scores[pid] += 0.5
            if self.g.has_edge(("outcome", "positive"), p):
                scores[pid] += 0.25
        order = ["case_study", "review", "proposal", "readme", "code"]
        hits = []
        for pid, score in sorted(scores.items(), key=lambda x: -x[1])[:k]:
            best = min(self.items_by_project[pid], key=lambda it: order.index(it["type"]) if it["type"] in order else 9)
            hits.append((best, score))
        return hits
