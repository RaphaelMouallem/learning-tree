#!/usr/bin/env python3
"""Validate a learning tree: structure (errors) and size/quality rules (warnings).

Usage:
    python validate_tree.py <tree-folder-or-tree.json> [--strict]

Exit code 0 = no errors (and no warnings with --strict), 1 otherwise.
Standard library only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path, PurePosixPath

from treelib import (DEPTHS, ID_RE, LIMITS, MODES, NODE_TYPES, RESOURCES,
                     SCHEMA_VERSION, TREE_ID_RE, get_config, load_tree,
                     parse_node_file)

VAGUE_VERBS = ("watch", "read", "study", "review", "skim")


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate(tree, base_dir):
    errors, warnings = [], []
    err, warn = errors.append, warnings.append

    if not isinstance(tree, dict):
        return ["tree.json must contain a JSON object"], []

    if tree.get("schema_version") != SCHEMA_VERSION:
        err(f"schema_version must be {SCHEMA_VERSION}")
    tid = tree.get("tree_id")
    if not isinstance(tid, str) or not TREE_ID_RE.match(tid):
        err("tree_id must be lowercase letters/digits/hyphens/underscores")
        tid = tid if isinstance(tid, str) else ""
    if not isinstance(tree.get("title"), str) or not tree["title"].strip():
        err("title must be a non-empty string")
    if "parent_tree" in tree and not isinstance(tree["parent_tree"], str):
        err("parent_tree must be a node id string (reserved for sub-trees)")

    raw_cfg = tree.get("config", {})
    if not isinstance(raw_cfg, dict):
        err("config must be an object")
        raw_cfg = {}
    for key, allowed in (("mode", MODES), ("resources", RESOURCES), ("depth", DEPTHS)):
        if key in raw_cfg and raw_cfg[key] not in allowed:
            err(f"config.{key} must be one of {list(allowed)}")
    if "capstones" in raw_cfg and not isinstance(raw_cfg["capstones"], bool):
        err("config.capstones must be true or false")
    cfg = get_config(tree)

    nodes = tree.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        err("nodes must be a non-empty list")
        return errors, warnings

    # ---- pass 1: per-node fields -----------------------------------------
    by_id = {}
    for idx, n in enumerate(nodes):
        if not isinstance(n, dict):
            err(f"nodes[{idx}] must be an object")
            continue
        nid = n.get("id")
        if not isinstance(nid, str) or not ID_RE.match(nid):
            err(f"nodes[{idx}]: id must look like '<tree_id>:<slug>' (lowercase)")
            continue
        if nid in by_id:
            err(f"{nid}: duplicate id")
            continue
        by_id[nid] = n
        if tid and not nid.startswith(tid + ":"):
            err(f"{nid}: id must start with '{tid}:'")
        if n.get("type") not in NODE_TYPES:
            err(f"{nid}: type must be one of {list(NODE_TYPES)}")
        if not isinstance(n.get("title"), str) or not n["title"].strip():
            err(f"{nid}: title must be a non-empty string")
        if not isinstance(n.get("requires", []), list) or not all(
                isinstance(r, str) and ID_RE.match(r) for r in n.get("requires", [])):
            err(f"{nid}: requires must be a list of node ids")
        if "est_hours" in n and (not _is_num(n["est_hours"]) or n["est_hours"] < 0):
            err(f"{nid}: est_hours must be a non-negative number")
        if "weight" in n and (not _is_num(n["weight"]) or n["weight"] <= 0):
            err(f"{nid}: weight must be a positive number")
        for flag in ("skipped", "done"):
            if flag in n and not isinstance(n[flag], bool):
                err(f"{nid}: {flag} must be true or false")
        f = n.get("file")
        if f is not None:
            if not isinstance(f, str) or not f:
                err(f"{nid}: file must be a relative path string or null")
            else:
                pp = PurePosixPath(f)
                if pp.is_absolute() or ".." in pp.parts:
                    err(f"{nid}: file must be a relative path inside the tree folder")
            if n.get("type") == "gear":
                warn(f"{nid}: gears do not use files; '{f}' will be ignored")

    # ---- pass 2: relationships --------------------------------------------
    kids = {}
    for nid, n in by_id.items():
        t = n.get("type")
        parent = n.get("parent")
        if t == "gear":
            if parent is not None:
                err(f"{nid}: a gear must have parent null")
        elif t in ("skill", "capstone"):
            if parent not in by_id or by_id[parent].get("type") != "gear":
                err(f"{nid}: parent must be the id of a gear in this tree")
            else:
                kids.setdefault(parent, []).append(n)
        for r in n.get("requires", []) if isinstance(n.get("requires", []), list) else []:
            if r == nid:
                err(f"{nid}: cannot require itself")
            elif r not in by_id and tid and r.startswith(tid + ":"):
                err(f"{nid}: requires unknown node '{r}'")

    # ---- cycles (explicit requires plus implicit gear/capstone edges) -----
    edges = {}
    for nid, n in by_id.items():
        deps = [r for r in n.get("requires", []) if r in by_id] \
            if isinstance(n.get("requires", []), list) else []
        if n.get("type") == "gear":
            deps += [c["id"] for c in kids.get(nid, [])]
        else:
            g = by_id.get(n.get("parent"))
            if g:
                deps += [r for r in g.get("requires", []) if r in by_id]
            if n.get("type") == "capstone" and g:
                deps += [c["id"] for c in kids.get(g["id"], []) if c.get("type") == "skill"]
        edges[nid] = deps

    state = {}          # 1 = on the current DFS stack, 2 = finished
    seen_cycles = []    # node sets already reported

    def dfs(u, path):
        state[u] = 1
        for v in edges.get(u, []):
            if state.get(v) == 1:  # back edge: v is on the stack, so path holds it
                cyc = path[path.index(v):]
                key = frozenset(cyc)
                if key not in seen_cycles:
                    seen_cycles.append(key)
                    if len(seen_cycles) <= 3:
                        err("prerequisite cycle: " + " -> ".join(cyc + [v]))
            elif v not in state:
                dfs(v, path + [v])
        state[u] = 2

    for nid in by_id:
        if nid not in state:
            dfs(nid, [nid])
    if len(seen_cycles) > 3:
        err(f"... and {len(seen_cycles) - 3} more prerequisite cycle(s)")

    # ---- granularity ------------------------------------------------------
    gears = [n for n in by_id.values() if n.get("type") == "gear"]
    lo, hi = LIMITS["gears"]
    if not lo <= len(gears) <= hi:
        warn(f"{len(gears)} gears; aim for {lo}-{hi} so the tree stays readable")

    for g in gears:
        ch = kids.get(g["id"], [])
        skills = [c for c in ch if c.get("type") == "skill"]
        caps = [c for c in ch if c.get("type") == "capstone"]
        if len(caps) > 1:
            err(f"{g['id']}: has {len(caps)} capstones; allowed at most 1")
        if cfg["mode"] == "full" and not ch:
            warn(f"{g['id']}: mode is 'full' but this gear is not expanded")
        if skills:
            lo, hi = LIMITS["skills_per_gear"]
            if not lo <= len(skills) <= hi:
                warn(f"{g['id']}: {len(skills)} skill nodes; aim for {lo}-{hi}")
            if cfg["capstones"] and not caps:
                warn(f"{g['id']}: no capstone (config.capstones is true)")
        elif caps:
            warn(f"{g['id']}: capstone without skill nodes")
        for s in skills:
            h = s.get("est_hours")
            lo, hi = LIMITS["skill_hours"]
            if h is None:
                if cfg["mode"] != "minimal":
                    warn(f"{s['id']}: no est_hours")
            elif _is_num(h) and h < lo:
                warn(f"{s['id']}: {h}h is tiny; consider merging into a neighbor")
            elif _is_num(h) and h > hi:
                warn(f"{s['id']}: {h}h is big; consider splitting (aim <= {hi}h)")

    # ---- node files -------------------------------------------------------
    for nid, n in by_id.items():
        t, f = n.get("type"), n.get("file")
        if t not in ("skill", "capstone"):
            continue
        if not f or not isinstance(f, str):
            if cfg["resources"] != "none" and cfg["mode"] != "minimal" \
                    and by_id.get(n.get("parent"), {}).get("type") == "gear":
                warn(f"{nid}: no file; write one from references/node-template.md")
            continue
        path = Path(base_dir) / f
        if not path.is_file():
            err(f"{nid}: file not found: {f}")
            continue
        try:
            info = parse_node_file(path)
        except (OSError, UnicodeDecodeError) as e:
            err(f"{nid}: cannot read {f}: {e}")
            continue

        if not info["has_frontmatter"] or info["frontmatter_id"] is None:
            warn(f"{nid}: {f} has no frontmatter 'id:' (needed for drift checks and Obsidian)")
        elif info["frontmatter_id"] != nid:
            err(f"{nid}: {f} frontmatter id is '{info['frontmatter_id']}' (mismatch)")

        lo, hi = LIMITS["todos"]
        if t == "skill":
            if cfg["resources"] != "none":
                prim = info["primary"]
                if not any(h.startswith("primary") for h in info["headings"]):
                    warn(f"{nid}: no '## Primary' section")
                elif not prim:
                    warn(f"{nid}: '## Primary' has no resources (say so in the message if the topic is thin)")
                elif len(prim) > 2:
                    warn(f"{nid}: {len(prim)} primary resources; expected one video and one article")
                elif any("http" not in line for line in prim):
                    warn(f"{nid}: a primary resource has no link")
            if info["total"] == 0:
                warn(f"{nid}: no todos under '## Todos'; progress falls back to the done flag")
            elif not lo <= info["total"] <= hi:
                warn(f"{nid}: {info['total']} todos; aim for {lo}-{hi}")
        else:
            if info["total"] < 2:
                warn(f"{nid}: capstone needs at least 2 acceptance criteria")

        if "<fill:" in path.read_text(encoding="utf-8-sig"):
            warn(f"{nid}: {f} still has '<fill: ...>' placeholders from a scaffold; "
                 f"replace them before delivering")

        vague = [txt for _, txt in info["items"] if txt.lower().startswith(VAGUE_VERBS)]
        if vague:
            warn(f"{nid}: {len(vague)} todo(s) start with watch/read/study; "
                 f"prefer actions that produce something")
        if info["alternatives"] > LIMITS["alternatives_max"]:
            warn(f"{nid}: {info['alternatives']} alternatives; keep at most {LIMITS['alternatives_max']}")
        if cfg["resources"] == "one-per-node" and info["alternatives"] > 0:
            warn(f"{nid}: has alternatives but config.resources is 'one-per-node'")

    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate a learning tree.")
    ap.add_argument("path", help="tree folder or tree.json")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args(argv)

    try:
        tree, base = load_tree(args.path)
    except (OSError, ValueError) as e:
        print(f"ERROR: cannot load tree: {e}")
        return 1

    errors, warnings = validate(tree, base)
    for m in errors:
        print(f"ERROR: {m}")
    for m in warnings:
        print(f"WARN:  {m}")
    if errors or (args.strict and warnings):
        print(f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
