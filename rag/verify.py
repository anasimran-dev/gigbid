"""B3 claim verification: split a draft into claims and check each against evidence.

A claim is a sentence that asserts experience or a result ("I built...", "it cut costs by 40%").
Labels: supported, partly_supported, unsupported. Unsupported claims are removed before
the Critic sees the draft; the before/after rate is reported by the evals.

The rule-based checker below needs no model. With an LLM profile the verifier node
(agent/nodes/verifier.py) asks the model first and uses this as the fallback.
"""
import re

from rag.skills import extract_skills, tokenize

STOP = set("a an the and or of to in on for with my i we it is was were be been have has had that this as at by from "
           "your you our can will would could should also about into over more than very".split())
NOT_A_CLAIM = re.compile(r"^(i can|i could|i would|i will|i'd|i'll|happy to|let me|would |could |can we|please|thanks|thank you|looking forward)", re.I)
FIRST_PERSON = re.compile(r"\b(i|my|we|our)\b", re.I)
NUMBER = re.compile(r"\d[\d,.]*%?")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if s.strip()]


def is_claim(sentence: str) -> bool:
    """Sentences about the client ("You need...") and offers ("I can...") are not claims."""
    if sentence.endswith("?") or NOT_A_CLAIM.match(sentence) or re.match(r"^(you|your)\b", sentence, re.I):
        return False
    if NUMBER.search(sentence) or extract_skills(sentence):
        return True
    return bool(FIRST_PERSON.search(sentence)) and bool(
        re.search(r"\b(built|delivered|led|designed|deployed|experience|worked|used|improved|reduced|cut|raised)\b", sentence, re.I))


def check_claim(claim: str, evidence: list[dict]) -> dict:
    """Compare the claim's facts (skills, numbers) with each evidence item; keep the best match."""
    skills, numbers = set(extract_skills(claim)), set(NUMBER.findall(claim))
    words = {t for t in tokenize(claim) if t not in STOP and len(t) > 2}
    best = {"label": "unsupported", "evidence_ids": [], "missing": sorted(skills | numbers), "score": 0.0}
    for ev in evidence:
        text = ev.get("text") or ev.get("snippet", "")
        ev_skills = set(ev.get("skills", [])) | set(extract_skills(text))
        facts = len(skills) + len(numbers)
        if facts:
            ok_skills, ok_numbers = skills & ev_skills, {n for n in numbers if n in text}
            score = (len(ok_skills) + len(ok_numbers)) / facts
            missing = sorted((skills - ok_skills) | (numbers - ok_numbers))
        else:  # no hard facts: fall back to content-word overlap
            ev_words = set(tokenize(text))
            score = len(words & ev_words) / len(words) if words else 0.0
            missing = []
            score = 1.0 if score >= 0.6 else score
        if score > best["score"]:
            label = "supported" if score >= 0.999 else "partly_supported" if score >= 0.5 else "unsupported"
            best = {"label": label, "evidence_ids": [ev["id"]] if label != "unsupported" else [], "missing": missing, "score": round(score, 3)}
    return {"claim": claim, **best}


def verify_claims(draft: str, evidence: list[dict]) -> list[dict]:
    return [check_claim(s, evidence) for s in split_sentences(draft) if is_claim(s)]


def remove_unsupported(draft: str, checks: list[dict]) -> str:
    """Drop unsupported sentences; keep paragraph breaks."""
    bad = {c["claim"] for c in checks if c["label"] == "unsupported"}
    paragraphs = []
    for para in draft.split("\n\n"):
        kept = [s for s in split_sentences(para) if s not in bad]
        if kept:
            paragraphs.append(" ".join(kept))
    return "\n\n".join(paragraphs)


def unsupported_rate(checks: list[dict]) -> float:
    return sum(c["label"] == "unsupported" for c in checks) / len(checks) if checks else 0.0
