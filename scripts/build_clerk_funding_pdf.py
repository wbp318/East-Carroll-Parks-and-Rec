"""Build docs/CLERK_FUNDING_OPTIONS.pdf from docs/CLERK_FUNDING_OPTIONS.md.

The Markdown file is the single source. This script handles the subset of Markdown that file uses
(headings, paragraphs, bullet and numbered lists, pipe tables, bold, code, links, rules) and renders
each ```mermaid block to PNG with mermaid-cli (mmdc) so the diagrams appear in the PDF.

    python scripts/build_clerk_funding_pdf.py
    python scripts/build_clerk_funding_pdf.py --by "Your Name"   # fills the "Prepared by" line
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs", "CLERK_FUNDING_OPTIONS.md")
OUT = os.path.join(ROOT, "docs", "CLERK_FUNDING_OPTIONS.pdf")
FOOTER = "East Carroll Parish Clerk of Court  |  Funding Options  |  November 2026"

NAVY = colors.HexColor("#1f3f73")
TAN = colors.HexColor("#c0905a")
GREY = colors.HexColor("#555555")
LIGHT = colors.HexColor("#f4efe6")
RULE = colors.HexColor("#d8cdbb")

PAGE_W, PAGE_H = letter
MARGIN = 0.7 * inch
FRAME_W = PAGE_W - 2 * MARGIN


def register_fonts():
    """Use Segoe UI on Windows for proper dashes and quotes; fall back to Helvetica elsewhere."""
    fdir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    faces = {
        "Body": "segoeui.ttf",
        "Body-Bold": "segoeuib.ttf",
        "Body-Italic": "segoeuii.ttf",
        "Body-BoldItalic": "segoeuiz.ttf",
    }
    if all(os.path.exists(os.path.join(fdir, f)) for f in faces.values()):
        for name, f in faces.items():
            pdfmetrics.registerFont(TTFont(name, os.path.join(fdir, f)))
        pdfmetrics.registerFontFamily(
            "Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-BoldItalic"
        )
        return "Body", "Body-Bold"
    return "Helvetica", "Helvetica-Bold"


BODY_FONT, BOLD_FONT = register_fonts()

TITLE = ParagraphStyle("title", fontName=BOLD_FONT, fontSize=20, leading=24, textColor=colors.white)
SUBTITLE = ParagraphStyle("subtitle", fontName=BODY_FONT, fontSize=10, leading=13, textColor=colors.white)
H2 = ParagraphStyle("h2", fontName=BOLD_FONT, fontSize=14, leading=17, textColor=NAVY, spaceBefore=10, spaceAfter=5)
H3 = ParagraphStyle("h3", fontName=BOLD_FONT, fontSize=11, leading=14, textColor=NAVY, spaceBefore=8, spaceAfter=3)
BODY = ParagraphStyle("body", fontName=BODY_FONT, fontSize=9.5, leading=12.5, spaceAfter=5)
BUL = ParagraphStyle("bul", parent=BODY, leftIndent=14, bulletIndent=4, spaceAfter=2)
BUL2 = ParagraphStyle("bul2", parent=BODY, leftIndent=28, bulletIndent=18, spaceAfter=2)
CELL = ParagraphStyle("cell", fontName=BODY_FONT, fontSize=8, leading=10)
HEAD = ParagraphStyle("head", fontName=BOLD_FONT, fontSize=8, leading=10, textColor=colors.white)
SMALL = ParagraphStyle("small", fontName=BODY_FONT, fontSize=7.5, leading=9.5, textColor=GREY)

MERMAID_CFG = {
    "theme": "base",
    "themeVariables": {
        "fontFamily": "Segoe UI, Arial, sans-serif",
        "fontSize": "15px",
        "primaryColor": "#e6ecf7",
        "primaryBorderColor": "#1f3f73",
        "primaryTextColor": "#14284a",
        "lineColor": "#55607a",
        "clusterBkg": "#faf7f1",
        "clusterBorder": "#c0905a",
        "pie1": "#1f3f73",
        "pie2": "#c0905a",
        "pie3": "#2e7d32",
        "pie4": "#6a3d7d",
        "pie5": "#b07d10",
        "pie6": "#4f86c6",
        "pie7": "#9aa3b5",
        "pieTitleTextSize": "18px",
        "pieSectionTextSize": "13px",
        "pieLegendTextSize": "14px",
    },
    "gantt": {"barHeight": 22, "fontSize": 13, "sectionFontSize": 14, "leftPadding": 90},
}


def inline(text):
    """Convert the inline Markdown this document uses to ReportLab paragraph markup."""
    links = []

    def stash(m):
        links.append((m.group(1), m.group(2)))
        return f"\x00{len(links) - 1}\x00"

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", stash, text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8.5">\1</font>', text)
    text = text.replace("[verify]", '<font color="#b07d10"><b>[verify]</b></font>')

    def unstash(m):
        label, url = links[int(m.group(1))]
        label = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        label = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", label)
        url = url.replace("&", "&amp;")
        return f'<link href="{url}" color="#1f3f73"><u>{label}</u></link>'

    return re.sub(r"\x00(\d+)\x00", unstash, text)


def render_mermaid(body, workdir, idx):
    mmdc = shutil.which("mmdc") or shutil.which("mmdc.cmd")
    if not mmdc:
        sys.exit("mmdc not found; install with: npm install -g @mermaid-js/mermaid-cli")
    src = os.path.join(workdir, f"d{idx}.mmd")
    out = os.path.join(workdir, f"d{idx}.png")
    cfg = os.path.join(workdir, "config.json")
    with open(cfg, "w", encoding="utf-8") as fh:
        json.dump(MERMAID_CFG, fh)
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(body)
    width = "1500" if body.lstrip().startswith("gantt") else "1200"
    cmd = [mmdc, "-i", src, "-o", out, "-b", "white", "-s", "3", "-w", width, "-c", cfg, "-q"]
    pcfg = os.path.join(ROOT, ".github", "puppeteer-config.json")
    if os.path.exists(pcfg):
        cmd += ["-p", pcfg]
    r = subprocess.run(cmd, capture_output=True, text=True, shell=(os.name == "nt"))
    if r.returncode != 0 or not os.path.exists(out):
        sys.exit(f"mermaid block {idx} failed to render:\n{(r.stderr or r.stdout)[:800]}")
    return out


def diagram(path, max_h=8.2 * inch):
    iw, ih = ImageReader(path).getSize()
    w = FRAME_W
    h = w * ih / iw
    if h > max_h:
        h = max_h
        w = h * iw / ih
    img = Image(path, width=w, height=h)
    img.hAlign = "CENTER"
    return img


def table(rows):
    ncol = len(rows[0])
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    # column widths in proportion to text length, clamped so no column collapses
    lens = []
    for c in range(ncol):
        longest = max(len(re.sub(r"\]\([^)]*\)", "]", r[c])) for r in rows)
        avg = sum(len(r[c]) for r in rows) / len(rows)
        lens.append(max(8, min(70, 0.5 * longest + 0.5 * avg)))
    # each column at least as wide as its longest word, so figures like $330,421 never break
    char_w = 4.6  # points per character at 8 pt
    mins = []
    for c in range(ncol):
        words = [w for r in rows for w in re.sub(r"\]\([^)]*\)", "]", r[c]).split()]
        mins.append(max((len(w) for w in words), default=1) * char_w + 10)
    total = sum(lens)
    widths = [FRAME_W * n / total for n in lens]
    for _ in range(3):
        short = [c for c in range(ncol) if widths[c] < mins[c]]
        if not short:
            break
        deficit = sum(mins[c] - widths[c] for c in short)
        for c in short:
            widths[c] = mins[c]
        rest = [c for c in range(ncol) if c not in short]
        pool = sum(widths[c] for c in rest)
        for c in rest:
            widths[c] -= deficit * widths[c] / pool
    data = [[Paragraph(inline(t), HEAD) for t in rows[0]]]
    data += [[Paragraph(inline(t), CELL) for t in r] for r in rows[1:]]
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(style))
    return t


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def title_block(title, sub, by):
    by_line = f"Prepared by: {by}" if by else "Prepared by: ______________________________"
    inner = Table(
        [[Paragraph(inline(title), TITLE)], [Paragraph(inline(sub), SUBTITLE)], [Paragraph(by_line, SUBTITLE)]],
        colWidths=[FRAME_W - 24],
    )
    inner.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    box = Table([[inner]], colWidths=[FRAME_W])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LINEBELOW", (0, 0), (-1, -1), 4, TAN),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return [box, Spacer(1, 10)]


def build(by):
    lines = open(SRC, encoding="utf-8").read().splitlines()
    story = []
    para = []
    workdir = tempfile.mkdtemp(prefix="clerk_pdf_")
    n_diagrams = 0
    held = []  # a heading (or a "Label:" line) plus the short text after it, kept with the next block

    def release():
        if held:
            story.append(KeepTogether(list(held)))
            held.clear()

    def add(flow, block=False):
        """Text joins the held group; a table or diagram closes it so the group stays with it."""
        if held:
            held.append(flow)
            # a "Label:" line only needs its first item beside it; a heading keeps a little more
            limit = 2 if held[0].style is BODY else 8
            if block or len(held) >= limit:
                release()
        else:
            story.append(flow)

    def hold(flow):
        if len(held) > 2:
            release()
        held.append(flow)

    def flush():
        if para:
            text = " ".join(para)
            p = Paragraph(inline(text), BODY)
            if text.endswith(":") or text.endswith(":**"):
                hold(p)
            else:
                add(p)
            para.clear()

    i = 0
    title = sub = None
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("# ") and title is None:
            title = s[2:]
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            sub = lines[i].strip()
            story += title_block(title, sub, by)
            i += 1
            continue
        if s.startswith("```mermaid"):
            flush()
            body = []
            i += 1
            while not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            n_diagrams += 1
            add(diagram(render_mermaid("\n".join(body) + "\n", workdir, n_diagrams)), block=True)
            story.append(Spacer(1, 6))
            i += 1
            continue
        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i].strip()):
                    rows.append(split_row(lines[i]))
                i += 1
            add(table(rows), block=True)
            story.append(Spacer(1, 6))
            continue
        if s.startswith("## "):
            flush()
            release()
            story.append(CondPageBreak(2.2 * inch))
            hold(Paragraph(inline(s[3:]), H2))
        elif s.startswith("### "):
            flush()
            release()
            story.append(CondPageBreak(1.6 * inch))
            hold(Paragraph(inline(s[4:]), H3))
        elif s == "---":
            flush()
            release()
            story.append(HRFlowable(width="100%", thickness=0.6, color=RULE, spaceBefore=4, spaceAfter=4))
        elif re.match(r"^\s{2,}- ", line):
            flush()
            add(Paragraph(inline(s[2:]), BUL2, bulletText="\u2013"))
        elif s.startswith("- "):
            flush()
            add(Paragraph(inline(s[2:]), BUL, bulletText="\u2022"))
        elif re.match(r"^\d+\. ", s):
            flush()
            num, rest = s.split(". ", 1)
            add(Paragraph(inline(rest), BUL, bulletText=f"{num}."))
        elif re.match(r"^\s{2,}\S", line) and story and not para:
            # continuation paragraph indented under a list item
            add(Paragraph(inline(s), BUL2))
        elif not s:
            flush()
        else:
            para.append(s)
        i += 1
    flush()
    release()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(BODY_FONT, 7.5)
        canvas.setFillColor(GREY)
        canvas.drawString(MARGIN, 0.45 * inch, FOOTER)
        canvas.drawRightString(PAGE_W - MARGIN, 0.45 * inch, f"Page {doc.page}")
        canvas.setStrokeColor(TAN)
        canvas.setLineWidth(1.2)
        canvas.line(MARGIN, 0.6 * inch, PAGE_W - MARGIN, 0.6 * inch)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        OUT,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=0.6 * inch,
        bottomMargin=0.8 * inch,
        title=title,
        author=by or "East Carroll Parish funding research",
        subject="Funding options for the East Carroll Parish Clerk of Court",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    shutil.rmtree(workdir, ignore_errors=True)
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({n_diagrams} diagrams)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--by", default="", help="name for the 'Prepared by' line; blank leaves a line to sign")
    build(ap.parse_args().by)
