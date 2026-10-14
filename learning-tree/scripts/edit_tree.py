#!/usr/bin/env python3
"""Edit a learning tree without hand-editing tree.json or counting checkboxes.

Usage:
    python edit_tree.py <folder> tick   <node-id> [selector ...]
    python edit_tree.py <folder> untick <node-id> [selector ...]
    python edit_tree.py <folder> skip   <node-id>
    python edit_tree.py <folder> unskip <node-id>
    python edit_tree.py <folder> add skill|capstone|gear <id> --title "..." [options]

Selectors for tick/untick (counted todos / acceptance criteria only):
    all        every counted item
    3          the 3rd counted item (the numbering progress.py shows as n/total)
    2-4        a range
    "branch"   text that matches exactly one item (case-insensitive substring)
With no selector, a node that has no checkable items (minimal mode) gets its
`done` flag set (tick) or cleared (untick).

add options:
    --parent <gear-id>     required for skill/capstone
    --requires a,b         comma-separated node ids
    --hours N              est_hours
    --after <node-id>      insert after this node (default: end of the gear)
    --scaffold             also write nodes/<slug>.md from the node template

Only tick what the learner said they did; completion is theirs to claim.
Every change is validated before it is written; on any error nothing changes.
Standard library only.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from treelib import (CHECK_RE, ID_RE, compute_progress, get_config, load_tree,
                     scan_node_lines, split_frontmatter)
from validate_tree import validate


class EditError(Exception):
    pass


# --------------------------------------------------------------------------
# tree.json writing (keeps one node per line so diffs stay readable)
# --------------------------------------------------------------------------

def dump_tree(tree):
    parts = []
    for key, val in tree.items():
        if key == "nodes":
            continue
        body = json.dumps(val, indent=2, ensure_ascii=False).replace("\n", "\n  ")
        parts.append(f'  {json.dumps(key)}: {body}')
    rows = []
    nodes = tree.get("nodes", [])
    for i, n in enumerate(nodes):
        # blank line between a gear's block and the next gear, but not between
        # consecutive (unexpanded) gears
        sep = "\n" if (n.get("type") == "gear" and i > 0 and nodes[i - 1].get("type") != "gear") else ""
        rows.append(sep + "    " + json.dumps(n, ensure_ascii=False))
    parts.append('  "nodes": [\n' + ",\n".join(rows) + "\n  ]")
    return "{\n" + ",\n".join(parts) + "\n}\n"


def atomic_write(path, text):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_text(path):
    # Keep the file's BOM state out of the way; we write plain UTF-8.
    return Path(path).read_text(encoding="utf-8-sig")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def find_node(tree, node_id):
    for n in tree["nodes"]:
        if isinstance(n, dict) and n.get("id") == node_id:
            return n
    ids = [n["id"] for n in tree["nodes"] if isinstance(n, dict) and "id" in n]
    near = [i for i in ids if node_id.split(":")[-1] in i][:5]
    hint = f" Did you mean: {', '.join(near)}?" if near else ""
    raise EditError(f"no node with id '{node_id}'.{hint}")


def parse_selectors(selectors, items):
    """Resolve selectors to a sorted list of 0-based positions in `items`."""
    n = len(items)
    chosen = set()
    for s in selectors:
        s = s.strip()
        if s.lower() == "all":
            chosen.update(range(n))
        elif re.fullmatch(r"\d+", s):
            k = int(s)
            if not 1 <= k <= n:
                raise EditError(f"item {k} out of range (this node has {n} counted items)")
            chosen.add(k - 1)
        elif re.fullmatch(r"\d+\s*-\s*\d+", s):
            a, b = (int(x) for x in re.split(r"\s*-\s*", s))
            if not 1 <= a <= b <= n:
                raise EditError(f"range {s} out of bounds (this node has {n} counted items)")
            chosen.update(range(a - 1, b))
        else:
            hits = [i for i, (_, _, label) in enumerate(items) if s.lower() in label.lower()]
            if not hits:
                raise EditError(f"no counted item contains '{s}'")
            if len(hits) > 1:
                raise EditError(f"'{s}' matches {len(hits)} items; use a number or longer text")
            chosen.add(hits[0])
    return sorted(chosen)


def node_progress_line(tree, base, node_id):
    res = compute_progress(tree, base)
    for g in res["gears"]:
        for r in g["nodes"]:
            if r["id"] == node_id:
                return (f"{r['title']}: {r['checked']}/{r['total']} ({r['percent']:.0f}%), "
                        f"status {r['status']}. Overall {res['percent']}%.")
    return ""


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_tick(tree, base, args, value):
    n = find_node(tree, args.node)
    if n.get("type") == "gear":
        raise EditError("gears are not ticked; tick their skill nodes")
    f = n.get("file")
    path = Path(base) / f if f else None
    items, lines, fm_len = [], [], 0
    if path and path.is_file():
        text = read_text(path)
        fm, body = split_frontmatter(text)
        lines = text.splitlines()
        fm_len = len(lines) - len(body)
        items = scan_node_lines(body)[0]

    if not items:
        if args.selectors:
            raise EditError(f"{n['id']} has no counted checkboxes to select; "
                            f"run without selectors to set its done flag")
        if value:
            n["done"] = True
        else:
            n.pop("done", None)
        return tree, None, f"{'Marked done' if value else 'Cleared done on'} {n['id']} (no checkboxes)."

    sel = parse_selectors(args.selectors or [], items) if args.selectors else None
    if sel is None:
        raise EditError("say which items: a number, a range like 2-4, text, or 'all'")

    changed = []
    for pos in sel:
        idx, done, label = items[pos]
        if done == value:
            continue
        line = lines[fm_len + idx]
        m = CHECK_RE.match(line)
        # swap only the mark between the brackets
        lines[fm_len + idx] = line[:m.start(1)] + ("x" if value else " ") + line[m.end(1):]
        changed.append(label)
    if not changed:
        return tree, None, f"Nothing to change in {n['id']} (already {'ticked' if value else 'unticked'})."
    new_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    verb = "Ticked" if value else "Unticked"
    return tree, (path, new_text), f"{verb} {len(changed)} item(s) in {n['id']}: " + "; ".join(
        c if len(c) <= 60 else c[:57] + "..." for c in changed)


def cmd_skip(tree, base, args, value):
    n = find_node(tree, args.node)
    if value:
        n["skipped"] = True
    else:
        n.pop("skipped", None)
    return tree, None, f"{'Skipped' if value else 'Un-skipped'} {n['id']}."


SKILL_SCAFFOLD = """---
id: {id}
tree: {tree_id}
type: skill
gear: {gear}
est_hours: {hours}
tags: [learning-tree/{tree_id}]
---
# {title}

**Why this matters:** <fill: one sentence>
**You'll be able to:** <fill: one sentence, observable outcome>

## Primary
- 🎥 <fill: title, link and reason; only from a real search or fetch>
- 📄 <fill: title, link and reason; only from a real search or fetch>

## Alternatives (optional)

## Todos
- [ ] <fill: an action that produces something>
- [ ] <fill: an action that produces something>
- [ ] <fill: an action that produces something>
"""

CAPSTONE_SCAFFOLD = """---
id: {id}
tree: {tree_id}
type: capstone
gear: {gear}
est_hours: {hours}
tags: [learning-tree/{tree_id}]
---
# {title}

Pick one:
- **Build:** <fill: a small project that uses the gear's skills, with a size bound>
- **Write:** <fill: a summary, explainer or blog post in their own words, with a size bound>

## Acceptance criteria
- [ ] <fill: checkable statement>
- [ ] <fill: checkable statement>

## Output
- Link or path:
"""


def cmd_add(tree, base, args):
    tid = tree["tree_id"]
    nid = args.id if ":" in args.id else f"{tid}:{args.id}"
    if not ID_RE.match(nid) or not nid.startswith(tid + ":"):
        raise EditError(f"id must look like '{tid}:<slug>' (lowercase letters, digits, - _)")
    if any(isinstance(n, dict) and n.get("id") == nid for n in tree["nodes"]):
        raise EditError(f"id '{nid}' already exists")

    node = {"id": nid, "type": args.type, "title": args.title, "parent": None, "requires": []}
    if args.requires:
        node["requires"] = [r if ":" in r else f"{tid}:{r}" for r in args.requires.split(",") if r.strip()]
    if args.hours is not None:
        node["est_hours"] = int(args.hours) if float(args.hours).is_integer() else args.hours

    insert_at = len(tree["nodes"])
    if args.type != "gear":
        if not args.parent:
            raise EditError("--parent <gear-id> is required for skill and capstone nodes")
        parent = args.parent if ":" in args.parent else f"{tid}:{args.parent}"
        g = find_node(tree, parent)
        if g.get("type") != "gear":
            raise EditError(f"'{parent}' is not a gear")
        node["parent"] = parent
        last = max((i for i, n in enumerate(tree["nodes"])
                    if n.get("id") == parent or n.get("parent") == parent), default=None)
        insert_at = last + 1
        slug = nid.split(":", 1)[1]
        mode = get_config(tree)["mode"]
        if mode != "minimal" or args.scaffold:
            node["file"] = args.file or f"nodes/{slug}.md"
    if args.after:
        after = args.after if ":" in args.after else f"{tid}:{args.after}"
        find_node(tree, after)
        insert_at = next(i for i, n in enumerate(tree["nodes"]) if n.get("id") == after) + 1
    tree["nodes"].insert(insert_at, node)

    write = None
    if node.get("file") and (args.scaffold or get_config(tree)["mode"] != "minimal"):
        path = Path(base) / node["file"]
        if path.exists():
            raise EditError(f"{node['file']} already exists; refusing to overwrite it")
        tpl = SKILL_SCAFFOLD if args.type == "skill" else CAPSTONE_SCAFFOLD
        text = tpl.format(id=nid, tree_id=tid, gear=node["parent"],
                          hours=node.get("est_hours", 3), title=args.title)
        write = (path, text)
    msg = f"Added {args.type} {nid}" + (f" and scaffolded {node['file']}" if write else "") + "."
    return tree, write, msg


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Edit a learning tree safely.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("Usage:")[1] if __doc__ else "")
    ap.add_argument("folder", help="tree folder (contains tree.json)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("tick", "untick"):
        p = sub.add_parser(name)
        p.add_argument("node")
        p.add_argument("selectors", nargs="*")
    for name in ("skip", "unskip"):
        sub.add_parser(name).add_argument("node")
    a = sub.add_parser("add")
    a.add_argument("type", choices=("skill", "capstone", "gear"))
    a.add_argument("id")
    a.add_argument("--title", required=True)
    a.add_argument("--parent")
    a.add_argument("--requires")
    a.add_argument("--hours", type=float)
    a.add_argument("--after")
    a.add_argument("--file")
    a.add_argument("--scaffold", action="store_true")
    args = ap.parse_args(argv)

    try:
        tree, base = load_tree(args.folder)
    except (OSError, ValueError) as e:
        print(f"ERROR: cannot load tree: {e}", file=sys.stderr)
        return 1

    before_errors, _ = validate(tree, base)
    if before_errors:
        print("ERROR: the tree already has errors; fix these first:", file=sys.stderr)
        for m in before_errors:
            print(f"  {m}", file=sys.stderr)
        return 1

    work = copy.deepcopy(tree)
    if getattr(args, "node", None) and ":" not in args.node:
        args.node = f"{tree['tree_id']}:{args.node}"
    try:
        if args.cmd in ("tick", "untick"):
            work, write, msg = cmd_tick(work, base, args, args.cmd == "tick")
        elif args.cmd in ("skip", "unskip"):
            work, write, msg = cmd_skip(work, base, args, args.cmd == "skip")
        else:
            work, write, msg = cmd_add(work, base, args)
    except EditError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # A scaffolded file must exist before validating the new tree.
    created = None
    if write and args.cmd == "add":
        path, text = write
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, text)
        created = path
    errors, _ = validate(work, base)
    if errors:
        if created:
            created.unlink(missing_ok=True)
        print("ERROR: that change would make the tree invalid; nothing was changed:", file=sys.stderr)
        for m in errors:
            print(f"  {m}", file=sys.stderr)
        return 1

    if write and args.cmd != "add":
        atomic_write(*write)
    tree_json_changed = work != tree
    if tree_json_changed:
        atomic_write(Path(base) / "tree.json", dump_tree(work))

    print(msg)
    nid = getattr(args, "node", None) or getattr(args, "id", None)
    if nid and ":" not in nid:
        nid = f"{work['tree_id']}:{nid}"
    line = node_progress_line(work, base, nid) if nid else ""
    if line and args.cmd != "add":
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
