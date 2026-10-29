"""Validate every ```mermaid block in the repo's Markdown files.

Usage:
    python scripts/check_mermaid.py            # static checks only
    python scripts/check_mermaid.py --render   # also render each block with mmdc (mermaid-cli)

Static checks catch the common breakages (unknown diagram type, unbalanced brackets or
quotes, empty block). --render is what CI runs and is authoritative.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAGRAM_TYPES = ("flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram", "stateDiagram-v2",
                 "erDiagram", "journey", "gantt", "pie", "quadrantChart", "requirementDiagram", "gitGraph",
                 "mindmap", "timeline", "sankey-beta", "xychart-beta", "block-beta", "C4Context", "zenuml")
BLOCK_RE = re.compile(r"```mermaid[ \t]*\n(.*?)```", re.DOTALL)


def find_markdown():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "__pycache__")]
        for fn in filenames:
            if fn.lower().endswith(".md"):
                yield os.path.join(dirpath, fn)


def static_check(body):
    errors = []
    lines = [l for l in body.strip("\n").split("\n") if l.strip() and not l.strip().startswith("%%")]
    if not lines:
        return ["empty block"]
    first = lines[0].strip()
    if not any(first.startswith(t) for t in DIAGRAM_TYPES):
        errors.append(f"unknown diagram type: {first[:40]!r}")
    for ch_open, ch_close in (("[", "]"), ("(", ")"), ("{", "}")):
        # strip quoted strings before counting brackets
        stripped = re.sub(r'"[^"]*"', "", body)
        if stripped.count(ch_open) != stripped.count(ch_close):
            errors.append(f"unbalanced {ch_open}{ch_close}")
    if body.count('"') % 2:
        errors.append("odd number of double quotes")
    # parentheses inside an unquoted [...] node label are parsed as shape syntax by mermaid
    for m in re.finditer(r"\[([^\]\"]*)\]", body):
        if "(" in m.group(1) or ")" in m.group(1):
            errors.append(f"parentheses inside unquoted [] label: [{m.group(1)[:40]}] -> wrap the label in quotes")
            break
    return errors


def render_check(body, mmdc, puppeteer_cfg):
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "d.mmd")
        out = os.path.join(td, "d.svg")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(body)
        cmd = [mmdc, "-i", src, "-o", out, "-q"]
        if puppeteer_cfg:
            cmd += ["-p", puppeteer_cfg]
        r = subprocess.run(cmd, capture_output=True, text=True, shell=(os.name == "nt"))
        if r.returncode != 0 or not os.path.exists(out):
            msg = (r.stderr or r.stdout).strip()
            # keep the first lines, which carry the parse error, not the puppeteer stack
            return ["\n     ".join(msg.splitlines()[:6]) or "mmdc failed"]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()
    mmdc = shutil.which("mmdc") or shutil.which("mmdc.cmd")
    if args.render and not mmdc:
        sys.exit("--render requested but mmdc not found; npm i -g @mermaid-js/mermaid-cli")
    cfg = os.path.join(ROOT, ".github", "puppeteer-config.json")
    cfg = cfg if os.path.exists(cfg) else None

    total = failed = 0
    for md in find_markdown():
        text = open(md, encoding="utf-8").read()
        for i, m in enumerate(BLOCK_RE.finditer(text), 1):
            total += 1
            body = m.group(1)
            line = text[:m.start()].count("\n") + 1
            errs = static_check(body)
            if args.render and not errs:
                errs = render_check(body, mmdc, cfg)
            rel = os.path.relpath(md, ROOT)
            if errs:
                failed += 1
                print(f"FAIL {rel}:{line} (block {i})")
                for e in errs:
                    print(f"     {e}")
            else:
                print(f"ok   {rel}:{line} (block {i})")
    print(f"\n{total} mermaid blocks, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
