#!/usr/bin/env python3
"""Export a learning tree as an Obsidian JSON Canvas file (tree.canvas).

Usage:
    python canvas_export.py <tree-folder> [-o tree.canvas] [--vault-prefix Learning/rust]

Layout: each gear is a group box. Gears are arranged in columns by prerequisite
depth (left to right); skill nodes and the capstone are stacked inside their
gear. Arrows show `requires` between gears and between skills of one gear.
Colors follow status (green done, yellow in progress, cyan available).

By default the cards are plain text. With --vault-prefix (the tree folder's path
inside the vault, e.g. "Learning/rust") each card also gets a wikilink to its
note, which Obsidian resolves from the vault root.

Obsidian's canvas format: https://jsoncanvas.org  Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from treelib import compute_progress, load_tree

ICON = {"done": "✅", "in_progress": "▶️", "available": "⭕", "locked": "🔒",
        "skipped": "⏭️", "not_expanded": "🌱"}
COLOR = {"done": "4", "in_progress": "3", "available": "5"}   # Obsidian palette

CARD_W, CARD_H = 280, 90
PAD, HEAD, GAP = 24, 24, 20
GROUP_W = CARD_W + 2 * PAD
COL_GAP, ROW_GAP = 160, 70


def _cid(*parts):
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _layers(gears):
    ids = {g["id"] for g in gears}
    req = {g["id"]: [r for r in g["requires"] if r in ids] for g in gears}
    memo, visiting = {}, set()

    def depth(i):
        if i in memo:
            return memo[i]
        if i in visiting:        # cycle: the validator reports it; do not loop
            return 0
        visiting.add(i)
        d = 1 + max((depth(r) for r in req[i]), default=-1)
        visiting.discard(i)
        memo[i] = d
        return d

    return {g["id"]: depth(g["id"]) for g in gears}


def build_canvas(tree, res, vault_prefix=None):
    nodes, edges = [], []
    layer = _layers(res["gears"])
    col_y = {}
    group_box = {}

    for g in res["gears"]:
        col = layer[g["id"]]
        n_cards = max(1, len(g["nodes"]))
        gh = HEAD + PAD + n_cards * CARD_H + (n_cards - 1) * GAP + PAD
        gx = col * (GROUP_W + COL_GAP)
        gy = col_y.get(col, 0)
        col_y[col] = gy + gh + ROW_GAP
        group_box[g["id"]] = (gx, gy, GROUP_W, gh)

        pct = "" if g["percent"] is None else f" ({g['percent']:.0f}%)"
        nodes.append({"id": _cid("group", g["id"]), "type": "group",
                      "x": gx, "y": gy, "width": GROUP_W, "height": gh,
                      "label": f"{ICON[g['status']]} {g['title']}{pct}"})

        if not g["nodes"]:
            nodes.append({"id": _cid("card", g["id"], "empty"), "type": "text",
                          "x": gx + PAD, "y": gy + HEAD + PAD, "width": CARD_W, "height": CARD_H,
                          "text": "🌱 *Not expanded yet*"})
            continue

        pos = {}
        for i, r in enumerate(g["nodes"]):
            x, y = gx + PAD, gy + HEAD + PAD + i * (CARD_H + GAP)
            pos[r["id"]] = (x, y)
            star = "★ " if r["type"] == "capstone" else ""
            hours = f" · ~{r['est_hours']}h" if r.get("est_hours") else ""
            text = f"**{ICON[r['status']]} {star}{r['title']}**\n{r['checked']}/{r['total']}{hours}"
            if vault_prefix and r.get("file"):
                target = f"{vault_prefix.strip('/')}/{r['file']}".replace(".md", "")
                text += f"\n[[{target}|open]]"
            card = {"id": _cid("card", r["id"]), "type": "text",
                    "x": x, "y": y, "width": CARD_W, "height": CARD_H, "text": text}
            if r["status"] in COLOR:
                card["color"] = COLOR[r["status"]]
            nodes.append(card)

        # arrows between skills of this gear (explicit requires only)
        in_gear = {r["id"] for r in g["nodes"]}
        tree_nodes = {n["id"]: n for n in tree["nodes"] if isinstance(n, dict) and "id" in n}
        order = {r["id"]: i for i, r in enumerate(g["nodes"])}
        for r in g["nodes"]:
            for dep in tree_nodes[r["id"]].get("requires", []):
                if dep in in_gear:
                    adjacent = order[r["id"]] - order[dep] == 1
                    edges.append({"id": _cid("edge", dep, r["id"]),
                                  "fromNode": _cid("card", dep),
                                  "fromSide": "bottom" if adjacent else "right",
                                  "toNode": _cid("card", r["id"]),
                                  "toSide": "top" if adjacent else "right"})

    # arrows between gears
    for g in res["gears"]:
        for req in g["requires"]:
            if req in group_box:
                edges.append({"id": _cid("edge", req, g["id"]),
                              "fromNode": _cid("group", req), "fromSide": "right",
                              "toNode": _cid("group", g["id"]), "toSide": "left"})
    # groups first so cards draw on top of them
    nodes.sort(key=lambda n: 0 if n["type"] == "group" else 1)
    return {"nodes": nodes, "edges": edges}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export a learning tree as an Obsidian canvas.")
    ap.add_argument("folder")
    ap.add_argument("-o", "--output", help="output path (default: <folder>/tree.canvas)")
    ap.add_argument("--vault-prefix", help="tree folder path inside the vault, for [[wikilinks]]")
    args = ap.parse_args(argv)
    try:
        tree, base = load_tree(args.folder)
    except (OSError, ValueError) as e:
        print(f"ERROR: cannot load tree: {e}", file=sys.stderr)
        return 1
    res = compute_progress(tree, base)
    canvas = build_canvas(tree, res, args.vault_prefix)
    out = Path(args.output) if args.output else base / "tree.canvas"
    out.write_text(json.dumps(canvas, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(canvas['nodes'])} nodes, {len(canvas['edges'])} edges)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
