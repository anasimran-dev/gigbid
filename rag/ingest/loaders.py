"""Portfolio loaders: CV (PDF or Markdown), case studies, repo READMEs, code, reviews, past proposals.

Every loader returns evidence items with the same metadata:
  id, persona, type, project, title, text, skills, date, industry, outcome, source
"""
import json
import re
from pathlib import Path

from rag.skills import extract_skills

ROOT = Path(__file__).resolve().parents[2]
PERSONA_DIR = ROOT / "data" / "personas"
UPLOAD_DIR = ROOT / "data" / "processed" / "uploads"


def _item(persona, id, type, text, project=None, title="", skills=None, date="", industry="", outcome="", source=""):
    return {"id": id, "persona": persona, "type": type, "project": project, "title": title, "text": text.strip(),
            "skills": skills if skills is not None else extract_skills(text), "date": date,
            "industry": industry, "outcome": outcome, "source": source}


def _front_matter(raw: str) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
    if not m:
        return {}, raw
    meta = dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)
    return meta, m.group(2)


def load_cv(persona: str, base: Path) -> list[dict]:
    pdf, md = base / "cv.pdf", base / "cv.md"
    if pdf.exists():
        from pypdf import PdfReader
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf)).pages)
    elif md.exists():
        text = md.read_text(encoding="utf-8")
    else:
        return []
    return [_item(persona, f"{persona}-cv", "cv", text, title="CV", source=str(pdf if pdf.exists() else md))]


def load_case_studies(persona: str, base: Path) -> list[dict]:
    items = []
    for path in sorted((base / "case_studies").glob("*.md")):
        meta, body = _front_matter(path.read_text(encoding="utf-8"))
        title = (re.search(r"^# (.+)$", body, re.M) or [None, path.stem])[1]
        items.append(_item(persona, meta.get("id", f"{persona}-{path.stem}"), "case_study", body, meta.get("project"),
                           title, [s.strip() for s in meta.get("skills", "").split(",") if s.strip()] or None,
                           meta.get("date", ""), meta.get("industry", ""), source=str(path)))
    return items


def load_repos(persona: str, base: Path) -> list[dict]:
    """README and code are separate items but share one project id (multi-vector, V5 idea)."""
    items = []
    for repo in sorted((base / "repos").glob("*")):
        n = repo.name.split("-")[-1]
        project = f"{persona}-p{n}"
        for path in sorted(repo.iterdir()):
            kind = "readme" if path.name.lower().startswith("readme") else "code"
            items.append(_item(persona, f"{persona}-{kind}-{n}", kind, path.read_text(encoding="utf-8"), project,
                               f"{repo.name}/{path.name}", source=str(path)))
    return items


def load_json_items(persona: str, base: Path, name: str, type: str) -> list[dict]:
    path = base / name
    if not path.exists():
        return []
    return [_item(persona, r["id"], type, r["text"], r.get("project"), type.replace("_", " "), r.get("skills"),
                  r.get("date", ""), r.get("industry") or "", r.get("outcome", ""), str(path))
            for r in json.loads(path.read_text(encoding="utf-8"))]


def load_uploads(persona: str) -> list[dict]:
    """Items the user added in the UI (incremental re-indexing reads these)."""
    path = UPLOAD_DIR / f"{persona}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def add_upload(persona: str, title: str, text: str, type: str = "case_study") -> dict:
    items = load_uploads(persona)
    item = _item(persona, f"{persona}-upload-{len(items) + 1:03d}", type, text, f"{persona}-upload-{len(items) + 1:03d}",
                 title, source="uploaded in UI")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / f"{persona}.json").write_text(json.dumps(items + [item], indent=1), encoding="utf-8")
    return item


def load_persona(persona: str) -> list[dict]:
    base = PERSONA_DIR / persona
    return (load_cv(persona, base) + load_case_studies(persona, base) + load_repos(persona, base)
            + load_json_items(persona, base, "reviews.json", "review")
            + load_json_items(persona, base, "past_proposals.json", "proposal") + load_uploads(persona))


def chunk(item: dict, size: int = 60, overlap: int = 15) -> list[dict]:
    """Fixed-size word windows. Each chunk keeps its parent item id and metadata."""
    words = item["text"].split()
    out = []
    for start in range(0, max(1, len(words)), size - overlap):
        piece = " ".join(words[start:start + size])
        if piece:
            out.append({"chunk_id": f"{item['id']}#{len(out)}", "item_id": item["id"], "text": piece})
        if start + size >= len(words):
            break
    return out
