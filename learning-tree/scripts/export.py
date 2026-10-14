#!/usr/bin/env python3
"""Bundle a learning tree into a zip with a readable overview.md.

Usage:
    python export.py <tree-folder> [-o output.zip] [--no-zip] [--canvas [--vault-prefix P]]
                     [--no-node-links]

Steps: validate -> compute progress -> write <tree-folder>/overview.md ->
zip the folder (tree.json, nodes/, overview.md, ...). overview.md is always
regenerated, so never edit it by hand. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
import zipfile
from pathlib import Path

from treelib import bar, compute_progress, get_config, load_tree
from validate_tree import validate

ICON = {"done": "✅", "in_progress": "▶️", "available": "⭕", "locked": "🔒",
        "skipped": "⏭️", "not_expanded": "🌱"}
LABEL = {"done": "done", "in_progress": "in progress", "available": "available",
         "locked": "locked", "skipped": "skipped", "not_expanded": "not expanded yet"}
EXCLUDE_DIRS = {".obsidian", "__pycache__", ".git"}
EXCLUDE_NAMES = {".DS_Store"}


def _pct(p):
    return "-" if p is None else f"{p:.0f}%"


def _mid(prefix, ident):
    return prefix + re.sub(r"[^A-Za-z0-9]", "_", ident)


def _label(text):
    return text.replace('"', "'")


def mermaid(res):
    lines = ["flowchart LR"]
    gear_ids = {g["id"] for g in res["gears"]}
    for g in res["gears"]:
        gid = _mid("g_", g["id"])
        suffix = f" ({_pct(g['percent'])})" if g["percent"] is not None else ""
        lines.append(f'  subgraph {gid}["{_label(g["title"])}{suffix}"]')
        lines.append("    direction TB")
        if not g["nodes"]:
            lines.append(f'    {gid}_x["not expanded yet"]:::not_expanded')
        for r in g["nodes"]:
            mark = "★ " if r["type"] == "capstone" else ""
            lines.append(f'    {_mid("n_", r["id"])}["{mark}{_label(r["title"])}"]:::{r["status"]}')
        lines.append("  end")
    for g in res["gears"]:
        for req in g["requires"]:
            if req in gear_ids:
                lines.append(f'  {_mid("g_", req)} --> {_mid("g_", g["id"])}')
    lines += [
        "  classDef done fill:#d4edda,stroke:#2e7d32,color:#1b3d1f",
        "  classDef in_progress fill:#fff3cd,stroke:#b8860b,color:#3d2f00",
        "  classDef available fill:#e3f2fd,stroke:#1565c0,color:#0d2a4a",
        "  classDef locked fill:#eceff1,stroke:#90a4ae,color:#455a64",
        "  classDef skipped fill:#f5f5f5,stroke:#bdbdbd,color:#9e9e9e,stroke-dasharray:4",
        "  classDef not_expanded fill:#f1f8e9,stroke:#9ccc65,color:#33691e,stroke-dasharray:4",
    ]
    return "\n".join(lines)


def render_overview(tree, res, warnings):
    cfg = get_config(tree)
    today = dt.date.today().isoformat()
    out = [f"# {res['title']}", ""]
    meta = []
    if tree.get("goal"):
        meta.append(f"**Goal:** {tree['goal']}")
    if tree.get("level"):
        meta.append(f"**Level:** {tree['level']}")
    if tree.get("hours_per_week"):
        meta.append(f"**Time:** {tree['hours_per_week']} h/week")
    meta.append(f"**Mode:** {cfg['mode']}")
    out += [" · ".join(meta), ""]
    out += [f"**Overall progress: {_pct(res['percent'])}** `{bar(res['percent'])}` "
            f"({res['counts']['done']}/{res['counts']['total']} nodes done)", "",
            f"*Generated {today}. This file is regenerated on every export; "
            f"tick boxes in the node files, not here.*", ""]

    out += ["## Gears", "", "| # | Gear | Status | Progress |", "|---|------|--------|----------|"]
    for i, g in enumerate(res["gears"], 1):
        out.append(f"| {i} | {g['title']} | {ICON[g['status']]} {LABEL[g['status']]} | {_pct(g['percent'])} |")
    out.append("")

    out += ["## Map", "", "```mermaid", mermaid(res), "```", ""]

    if res["next"]:
        out += ["## Next up", ""]
        by_id = {r["id"]: r for g in res["gears"] for r in g["nodes"]}
        for n in res["next"]:
            r = by_id[n["id"]]
            link = f"[{r['title']}]({r['file']})" if r.get("file") else r["title"]
            out.append(f"- {ICON[r['status']]} {link}")
        out.append("")
    if res["needs_expansion"]:
        titles = {g["id"]: g["title"] for g in res["gears"]}
        out += ["## Ready to expand", ""]
        out += [f"- 🌱 {titles[i]}" for i in res["needs_expansion"]]
        out.append("")

    out += ["## Details", ""]
    for i, g in enumerate(res["gears"], 1):
        out.append(f"### {i}. {g['title']} - {ICON[g['status']]} {LABEL[g['status']]} ({_pct(g['percent'])})")
        out.append("")
        if not g["nodes"]:
            out += ["*Not expanded yet.*", ""]
            continue
        for r in g["nodes"]:
            title = f"[{r['title']}]({r['file']})" if r.get("file") and not r["file_missing"] else r["title"]
            kind = " ★ capstone" if r["type"] == "capstone" else ""
            hours = f" · ~{r['est_hours']}h" if r.get("est_hours") else ""
            prog = f" · {r['checked']}/{r['total']}" if r["status"] != "skipped" else ""
            out.append(f"- {ICON[r['status']]} {title}{kind}{hours}{prog}")
        out.append("")

    if warnings:
        out += ["## Validation notes", ""] + [f"- {w}" for w in warnings] + [""]

    out += [
        "## Resume this tree", "",
        "Upload this zip (or open this folder) in an agent that has the **learning-tree** skill and say "
        "*\"resume my learning tree\"*. Progress is read from the checkboxes in `nodes/*.md`, "
        "so ticking boxes (in Obsidian or any editor) is all you need to do.", "",
    ]
    return "\n".join(out)


LINKS_START = "<!-- learning-tree:links:start (generated by export.py; edit outside these markers) -->"
LINKS_END = "<!-- learning-tree:links:end -->"
LINKS_RE = re.compile(re.escape(LINKS_START.split(" (")[0]) + r".*?" + re.escape(LINKS_END),
                      re.DOTALL)


def _rel(from_file, to_file):
    return Path(os.path.relpath(to_file, Path(from_file).parent)).as_posix()


def node_link_blocks(tree, base):
    """{node_id: markdown block} with Part of / Requires / Unlocks link lines.

    Real links between the notes are what make Obsidian's graph view show the
    tree's structure instead of a pile of unconnected files. Edges: explicit
    `requires`, plus every skill a capstone implicitly waits for. A requirement
    on a whole gear points at that gear's capstone (or its skills if none).
    """
    nodes = [n for n in tree["nodes"] if isinstance(n, dict) and "id" in n]
    by_id = {n["id"]: n for n in nodes}
    files = {n["id"]: n["file"] for n in nodes
             if n.get("file") and n.get("type") in ("skill", "capstone")
             and (Path(base) / n["file"]).is_file()}
    kids = {}
    for n in nodes:
        if n.get("type") in ("skill", "capstone") and n.get("parent"):
            kids.setdefault(n["parent"], []).append(n)

    def targets(ref):
        """Leaf node ids that a `requires` entry stands for."""
        r = by_id.get(ref)
        if r is None:
            return []
        if r["type"] != "gear":
            return [ref]
        caps = [c["id"] for c in kids.get(ref, []) if c["type"] == "capstone"]
        return caps or [c["id"] for c in kids.get(ref, [])]

    needs = {i: [] for i in files}        # node -> leaf ids it waits for
    external = {i: [] for i in files}
    for i in files:
        n = by_id[i]
        for ref in n.get("requires", []):
            if ref in by_id:
                needs[i] += [t for t in targets(ref) if t != i]
            else:
                external[i].append(ref)
        if n["type"] == "capstone":
            needs[i] += [c["id"] for c in kids.get(n.get("parent"), []) if c["type"] == "skill"]
    needs = {i: [t for k, t in enumerate(v) if t not in v[:k]] for i, v in needs.items()}
    unlocks = {i: [] for i in files}
    for i, deps in needs.items():
        for d in deps:
            if d in unlocks:
                unlocks[d].append(i)

    def link(src, dst):
        title = by_id[dst].get("title", dst).replace("[", "(").replace("]", ")")
        return f"[{title}]({_rel(files[src], files[dst])})"

    blocks = {}
    for i in files:
        n = by_id[i]
        gear = by_id.get(n.get("parent"))
        lines = ["## Position in tree"]
        if gear:
            lines.append(f"- Part of: [{gear.get('title', gear['id'])}]({_rel(files[i], 'overview.md')})")
        req = [link(i, d) for d in needs[i] if d in files] + [f"`{e}`" for e in external[i]]
        if req:
            lines.append("- Requires: " + ", ".join(req))
        out = [link(i, u) for u in unlocks[i]]
        if out:
            lines.append("- Unlocks: " + ", ".join(out))
        blocks[i] = LINKS_START + "\n" + "\n".join(lines) + "\n" + LINKS_END
    return blocks, files


def sync_node_links(tree, base):
    """Write/refresh the generated link block in each node file. Returns #files changed."""
    blocks, files = node_link_blocks(tree, base)
    changed = 0
    for nid, block in blocks.items():
        path = Path(base) / files[nid]
        text = path.read_text(encoding="utf-8-sig")
        if LINKS_RE.search(text):
            new = LINKS_RE.sub(lambda m: block, text, count=1)
        else:
            new = text.rstrip("\n") + "\n\n" + block + "\n"
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
    return changed


def build_zip(folder, out_path, root=None):
    folder = Path(folder).resolve()
    root = root or folder.name
    out_path = Path(out_path).resolve()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob("*")):
            rel = p.relative_to(folder)
            if p.is_dir() or p.is_symlink() or p == out_path:
                continue   # symlinks could pull files from outside the tree into the zip
            if set(rel.parts) & EXCLUDE_DIRS or p.name in EXCLUDE_NAMES or p.suffix == ".zip":
                continue
            z.write(p, Path(root) / rel)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export a learning tree as overview.md + zip.")
    ap.add_argument("folder", help="tree folder (contains tree.json)")
    ap.add_argument("-o", "--output", help="zip path (default: ./<tree_id>-learningtree-<date>.zip)")
    ap.add_argument("--no-zip", action="store_true", help="only (re)write overview.md")
    ap.add_argument("--no-node-links", action="store_true",
                    help="do not add/refresh the 'Position in tree' link block in node files")
    ap.add_argument("--canvas", action="store_true", help="also write tree.canvas (Obsidian JSON Canvas)")
    ap.add_argument("--vault-prefix", help="with --canvas: tree folder path inside the vault, for [[wikilinks]]")
    args = ap.parse_args(argv)

    try:
        tree, base = load_tree(args.folder)
    except (OSError, ValueError) as e:
        print(f"ERROR: cannot load tree: {e}", file=sys.stderr)
        return 1

    errors, warnings = validate(tree, base)
    if errors:
        for m in errors:
            print(f"ERROR: {m}", file=sys.stderr)
        print("Fix the errors above before exporting.", file=sys.stderr)
        return 1

    if not args.no_node_links:
        n = sync_node_links(tree, base)
        if n:
            print(f"Updated link block in {n} node file(s)")
    res = compute_progress(tree, base)
    (base / "overview.md").write_text(render_overview(tree, res, warnings), encoding="utf-8")
    print(f"Wrote {base / 'overview.md'}")
    if args.canvas:
        from canvas_export import build_canvas
        import json
        canvas = build_canvas(tree, res, args.vault_prefix)
        (base / "tree.canvas").write_text(json.dumps(canvas, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
        print(f"Wrote {base / 'tree.canvas'}")
    if args.no_zip:
        return 0

    default = f"{tree['tree_id']}-learningtree-{dt.date.today().isoformat()}.zip"
    out = build_zip(base, args.output or default, root=tree['tree_id'])
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
