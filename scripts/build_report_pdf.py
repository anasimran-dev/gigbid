"""Build docs/REPORT.pdf from docs/REPORT.md (headings, paragraphs, bullet lists, tables).

  python scripts/build_report_pdf.py      (needs reportlab)
"""
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DOCS = Path(__file__).resolve().parent.parent / "docs"
ss = getSampleStyleSheet()
BODY = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=12.5, spaceAfter=5)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, spaceBefore=8, spaceAfter=4)
TITLE = ParagraphStyle("t", parent=ss["Title"], fontSize=18)
CELL = ParagraphStyle("c", parent=BODY, fontSize=8.5, leading=10.5, spaceAfter=0)


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', text)


def main():
    lines = (DOCS / "REPORT.md").read_text(encoding="utf-8").split("\n")
    meta = {}
    if lines[0] == "---":
        end = lines.index("---", 1)
        for ln in lines[1:end]:
            k, _, v = ln.partition(":")
            meta[k.strip()] = v.strip().strip('"')
        lines = lines[end + 1:]
    story = [Paragraph(inline(meta.get("title", "Report")), TITLE), Paragraph(inline(meta.get("author", "")), BODY), Spacer(1, 4)]
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("## "):
            story.append(Paragraph(inline(ln[3:]), H2))
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append([Paragraph(inline(c), CELL) for c in cells])
                i += 1
            t = Table(rows, repeatRows=1)
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story += [t, Spacer(1, 6)]
            continue
        elif ln.strip():
            story.append(Paragraph(inline(ln), BODY))
        i += 1
    SimpleDocTemplate(str(DOCS / "REPORT.pdf"), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=16 * mm, title=meta.get("title", "Report"), author="Anas Imran").build(story)


if __name__ == "__main__":
    main()
