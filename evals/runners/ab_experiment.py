"""Signature extension X2: two proposal strategies as an A/B test in GigSim, with a significance test.

  python -m evals.runners.ab_experiment   -> evals/results/ab_experiment.json

A = evidence_first, B = question_first, on the same fixed job set (paired by job).
Test: two-proportion z-test on reply rate (two-sided).
"""
import math

from agent.config import cfg
from evals.common import save
from evals.runners.gigsim_outcomes import run_variant


def z_test(x1: int, n1: int, x2: int, n2: int) -> dict:
    p1, p2, pool = x1 / n1, x2 / n2, (x1 + x2) / (n1 + n2)
    se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se else 0.0
    return {"z": round(z, 3), "p_value": round(math.erfc(abs(z) / math.sqrt(2)), 4)}


if __name__ == "__main__":
    variant = cfg()["rag"]["variant"]
    a, b = run_variant(variant, 60, "evidence_first"), run_variant(variant, 60, "question_first")
    test = z_test(a["replied"], a["n_jobs"], b["replied"], b["n_jobs"])
    save("ab_experiment", {"rag_variant": variant, "A_evidence_first": a, "B_question_first": b, "two_proportion_z_test": test,
                           "significant_at_0.05": test["p_value"] < 0.05})
    print(a["reply_rate"], b["reply_rate"], test)
