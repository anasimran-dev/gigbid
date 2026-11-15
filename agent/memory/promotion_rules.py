"""Explicit promotion rules (R7, C2). Nothing enters long-term memory except through these.

STYLE MEMORY  - learned from the user's edits to drafts.
  observe_edit() turns one edit (before/after) into small observations:
     remove_word:<w>       the user deleted a word the agent wrote
     cut_first_sentence    the user deleted the opening sentence
     shorter               the user cut the draft by more than 20%
  Each observation is counted in the "candidates" namespace. It is PROMOTED to the "style"
  namespace only when seen in memory.style_min_repeats different edits (default 2).

OUTCOME MEMORY - what won or got replies, per job category and proposal strategy.
  record_outcome() tallies a final outcome. A category is PROMOTED to the "outcomes" namespace
  only after memory.outcome_min_samples outcomes (default 3).

Raw tool output and raw drafts are never stored: only these derived, counted facts.
"""
import difflib
import re

from agent.config import cfg

STOP = set("a an the and or of to in on for with my i we it is was were be been have has had that this as at by from".split())


def diff_text(before: str, after: str) -> str:
    return "\n".join(difflib.unified_diff(before.split("\n"), after.split("\n"), "agent draft", "your edit", lineterm=""))


def observe_edit(before: str, after: str) -> list[str]:
    obs = []
    b_words, a_words = re.findall(r"[a-z']+", before.lower()), set(re.findall(r"[a-z']+", after.lower()))
    for w in dict.fromkeys(b_words):
        if w not in a_words and w not in STOP and len(w) > 3:
            obs.append(f"remove_word:{w}")
    first = re.split(r"(?<=[.!?])\s+", before.strip())[0]
    if first and first not in after:
        obs.append("cut_first_sentence")
    if len(after.split()) < 0.8 * len(before.split()):
        obs.append("shorter")
    return obs


def learn_from_edit(store, user: str, before: str, after: str) -> list[str]:
    """Count observations; promote those that repeat. Returns the rules promoted by this edit."""
    need, promoted = cfg()["memory"]["style_min_repeats"], []
    for ob in observe_edit(before, after):
        item = store.get(("candidates", user), ob)
        count = (item.value["count"] if item else 0) + 1
        store.put(("candidates", user), ob, {"count": count})
        if count >= need and store.get(("style", user), ob) is None:
            store.put(("style", user), ob, {"rule": describe(ob), "seen": count, "source": "your edits"})
            promoted.append(ob)
    return promoted


def describe(ob: str) -> str:
    if ob.startswith("remove_word:"):
        return f"Never use the word '{ob.split(':', 1)[1]}'"
    return {"cut_first_sentence": "Cut the opening sentence; start with the evidence", "shorter": "Keep drafts shorter"}.get(ob, ob)


def style_rules(store, user: str) -> dict:
    """What the Writer applies: banned words and structural rules."""
    keys = [i.key for i in store.search(("style", user))]
    return {"banned_words": [k.split(":", 1)[1] for k in keys if k.startswith("remove_word:")],
            "cut_first_sentence": "cut_first_sentence" in keys, "shorter": "shorter" in keys,
            "rules": [describe(k) for k in keys]}


def apply_style(text: str, rules: dict) -> str:
    for w in rules.get("banned_words", []):
        text = re.sub(rf"\b{re.escape(w)}\b\s?", "", text, flags=re.I)
    return re.sub(r" {2,}", " ", text).strip()


def record_outcome(store, user: str, category: str, strategy: str, stage: str) -> bool:
    """Tally one final outcome. Returns True when the category was promoted / refreshed."""
    key = category or "other"
    item = store.get(("candidates", user), f"outcome:{key}")
    tally = item.value if item else {"n": 0, "replied": 0, "hired": 0, "by_strategy": {}}
    tally["n"] += 1
    tally["replied"] += stage in ("replied", "interview", "hired")
    tally["hired"] += stage == "hired"
    s = tally["by_strategy"].setdefault(strategy, {"n": 0, "replied": 0})
    s["n"] += 1
    s["replied"] += stage in ("replied", "interview", "hired")
    store.put(("candidates", user), f"outcome:{key}", tally)
    if tally["n"] < cfg()["memory"]["outcome_min_samples"]:
        return False
    best = max(tally["by_strategy"], key=lambda k: tally["by_strategy"][k]["replied"] / tally["by_strategy"][k]["n"])
    store.put(("outcomes", user), key, {"n": tally["n"], "reply_rate": round(tally["replied"] / tally["n"], 2),
                                        "hire_rate": round(tally["hired"] / tally["n"], 2), "best_strategy": best})
    return True


def best_strategy(store, user: str, category: str) -> str | None:
    item = store.get(("outcomes", user), category or "other")
    return item.value["best_strategy"] if item else None
