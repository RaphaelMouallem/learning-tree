#!/usr/bin/env python3
"""Compute and print learning-tree progress from the node files' checkboxes.

Usage:
    python progress.py <tree-folder-or-tree.json> [--json]

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys

from treelib import bar, compute_progress, load_tree

LABELS = {
    "done": "done", "in_progress": "in progress", "available": "available",
    "locked": "locked", "skipped": "skipped", "not_expanded": "not expanded",
}


def pct(p):
    return "  -  " if p is None else f"{p:5.1f}%"


def render_text(res):
    out = []
    counts = res["counts"]
    out.append(f"# {res['title']}  [{res['mode']}]")
    out.append(f"Overall: {pct(res['percent']).strip()}  {bar(res['percent'])}  "
               f"({counts['done']}/{counts['total']} nodes done)")
    out.append("Unexpanded gears count as 0%; skipped nodes are excluded.")
    out.append("")
    for g in res["gears"]:
        head = f"## {g['title']} - {LABELS[g['status']]}"
        if g["percent"] is not None:
            head += f" - {pct(g['percent']).strip()}"
        out.append(head)
        if not g["nodes"]:
            out.append("   (not expanded yet)")
        for r in g["nodes"]:
            tag = "capstone" if r["type"] == "capstone" else "skill"
            detail = f"{r['checked']}/{r['total']}"
            out.append(f"   - [{LABELS[r['status']]:<11}] {r['title']} ({tag}, {detail})")
        out.append("")
    if res["next"]:
        out.append("Next up:")
        for r in res["next"]:
            out.append(f"   - {r['title']} ({LABELS[r['status']]})")
    if res["needs_expansion"]:
        out.append("Ready to expand: " + ", ".join(res["needs_expansion"]))
    for w in res["warnings"]:
        out.append(f"WARN: {w}")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Learning-tree progress report.")
    ap.add_argument("path", help="tree folder or tree.json")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    try:
        tree, base = load_tree(args.path)
    except (OSError, ValueError) as e:
        print(f"ERROR: cannot load tree: {e}", file=sys.stderr)
        return 1
    res = compute_progress(tree, base)
    print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else render_text(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
