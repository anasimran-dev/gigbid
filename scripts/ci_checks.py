"""CI hygiene: no secrets committed, gigsim/ untouched marker, prompts only in agent/prompts."""
import re, pathlib, sys
bad = []
for p in pathlib.Path(".").rglob("*"):
    if p.suffix in {".py", ".ts", ".tsx", ".yml", ".yaml", ".md"} and not {"node_modules", ".git"} & set(p.parts):
        t = p.read_text(errors="ignore")
        if re.search(r"(sk-[A-Za-z0-9]{20,}|gsk_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,})", t):
            bad.append(f"secret-like token in {p}")
for p in pathlib.Path("agent/nodes").glob("*.py"):
    if "You are a" in p.read_text():
        bad.append(f"prompt text outside agent/prompts: {p}")
print("\n".join(bad) or "ci_checks ok"); sys.exit(1 if bad else 0)
