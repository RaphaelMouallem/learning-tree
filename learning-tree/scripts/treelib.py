#!/usr/bin/env python3
"""Shared helpers for the learning-tree scripts. Standard library only.

Design rule: tree.json stores STRUCTURE. The node .md files store CONTENT and
the checkboxes. Progress is always computed from the checkboxes, never stored,
so the two cannot drift apart.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_VERSION = 1
NODE_TYPES = ("gear", "skill", "capstone")
MODES = ("minimal", "guided", "full")
RESOURCES = ("none", "one-per-node", "with-alternatives")
DEPTHS = ("gears-only", "gears+skills")

DEFAULT_CONFIG = {
    "mode": "guided",
    "resources": "with-alternatives",
    "capstones": True,
    "depth": "gears+skills",
}

# Presets applied under explicit config values (explicit keys always win).
MODE_PRESETS = {
    "minimal": {"resources": "none", "capstones": False},
    "guided": {},
    "full": {},
}

# Granularity limits. The validator reports violations as warnings.
LIMITS = {
    "gears": (4, 8),
    "skills_per_gear": (3, 6),
    "skill_hours": (1, 10),
    "todos": (3, 7),
    "alternatives_max": 3,
}

DEFAULT_WEIGHTS = {"skill": 1.0, "capstone": 2.0}
# An unexpanded gear has no nodes yet; assume it is about this big so the
# overall percentage does not jump to 100% when only the first gear exists.
PLACEHOLDER_GEAR_WEIGHT = 6.0

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*:[a-z0-9][a-z0-9_-]*$")
TREE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
CHECK_RE = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s*(.*)$")
TOP_BULLET_RE = re.compile(r"^[-*+]\s+\S")
FM_ID_RE = re.compile(r"^id:\s*[\"']?([^\"'\s]+)", re.MULTILINE)

# Only checkboxes under these headings count toward progress.
COUNTED_PREFIXES = ("todo", "acceptance criteria")


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_tree(path):
    """Load tree.json. `path` may be the file or the folder containing it."""
    p = Path(path)
    if p.is_dir():
        p = p / "tree.json"
    with open(p, encoding="utf-8-sig") as f:
        data = json.load(f)
    return data, p.parent


def get_config(tree):
    """Effective config: defaults < mode preset < explicit config keys."""
    raw = tree.get("config") if isinstance(tree.get("config"), dict) else {}
    mode = raw.get("mode", DEFAULT_CONFIG["mode"])
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(MODE_PRESETS.get(mode, {}))
    cfg.update({k: v for k, v in raw.items() if k != "mode"})
    cfg["mode"] = mode
    return cfg


# --------------------------------------------------------------------------
# Node file parsing
# --------------------------------------------------------------------------

def _norm_heading(text):
    """Lowercase and drop leading emoji/punctuation so '✅ Todos' == 'todos'."""
    return re.sub(r"^[^a-z0-9]+", "", text.lower()).strip()


def split_frontmatter(text):
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[1:i]), lines[i + 1:]
    return None, lines


def scan_node_lines(lines):
    """Walk the body lines of a node file with the single set of counting rules.

    Returns (items, headings, alternatives, primary) where items is a list of
    (line_index, done, label) for every counted checkbox and primary is the list
    of top-level bullet lines under a "Primary" heading. Both progress and the
    edit helpers use this, so what is displayed as "2/4" and what `tick` toggles
    can never disagree. Checkboxes marked "(optional)" and anything in code
    fences are ignored.
    """
    stack = []  # (level, normalized heading)
    items, headings, primary = [], [], []
    alternatives = 0
    in_fence = False

    for idx, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            level, h = len(m.group(1)), _norm_heading(m.group(2))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, h))
            headings.append(h)
            continue
        counted = any(h.startswith(COUNTED_PREFIXES) for _, h in stack)
        in_alt = any(h.startswith("alternatives") for _, h in stack)
        in_primary = any(h.startswith("primary") for _, h in stack)
        c = CHECK_RE.match(line)
        if c and counted:
            label = c.group(2).strip()
            if "(optional)" in label.lower():
                continue
            items.append((idx, c.group(1).lower() == "x", label))
        elif in_alt and TOP_BULLET_RE.match(line):
            alternatives += 1
        elif in_primary and TOP_BULLET_RE.match(line):
            primary.append(line)
    return items, headings, alternatives, primary


def parse_node_file(path):
    """Parse a node .md file.

    Returns a dict with:
      checked / total  - checkbox counts under Todos / Acceptance criteria
      items            - list of (done, text) for counted checkboxes
      headings         - normalized heading texts
      alternatives     - number of top-level bullets under 'Alternatives'
      primary          - the top-level bullet lines under 'Primary'
      frontmatter_id   - value of `id:` in the frontmatter (or None)
      has_frontmatter  - bool
    Checkboxes marked "(optional)" and anything in code fences are ignored.
    """
    text = Path(path).read_text(encoding="utf-8-sig")
    fm, body = split_frontmatter(text)
    raw_items, headings, alternatives, primary = scan_node_lines(body)
    items = [(done, label) for _, done, label in raw_items]

    fm_id = None
    if fm:
        m = FM_ID_RE.search(fm)
        fm_id = m.group(1) if m else None

    return {
        "checked": sum(1 for done, _ in items if done),
        "total": len(items),
        "items": items,
        "headings": headings,
        "alternatives": alternatives,
        "primary": primary,
        "frontmatter_id": fm_id,
        "has_frontmatter": fm is not None,
    }


# --------------------------------------------------------------------------
# Progress
# --------------------------------------------------------------------------

def leaf_weight(n):
    w = n.get("weight")
    if isinstance(w, (int, float)) and not isinstance(w, bool) and w > 0:
        return float(w)
    return DEFAULT_WEIGHTS.get(n.get("type"), 1.0)


def _leaf_counts(n, base_dir):
    """(checked, total, file_missing) for a skill/capstone node.

    A node with no checkable items (minimal mode, or no file yet) counts as a
    single unit that is complete only when `"done": true` is set in tree.json.
    """
    f = n.get("file")
    file_missing = False
    if f:
        p = Path(base_dir) / f
        if p.is_file():
            info = parse_node_file(p)
            if info["total"] > 0:
                return info["checked"], info["total"], False
        else:
            file_missing = True
    return (1 if n.get("done") else 0), 1, file_missing


def bar(percent, width=20):
    if percent is None:
        return "-" * width
    filled = int(round(width * percent / 100.0))
    return "█" * filled + "░" * (width - filled)


def compute_progress(tree, base_dir):
    """Compute node, gear and tree progress from the node files.

    Statuses: done, in_progress, available, locked, skipped, not_expanded.
    - Skipped nodes are excluded from every percentage (skipping never inflates).
    - Optional alternatives never count.
    - A node is `locked` until its `requires`, its gear's `requires` (and, for
      capstones, every sibling skill) are done or skipped. Work already ticked
      always shows as in_progress/done, even if the node is still locked.
    - Prerequisites in another tree (different id prefix) are reported but not
      checked.
    """
    nodes = [n for n in tree.get("nodes", []) if isinstance(n, dict) and "id" in n]
    by_id = {n["id"]: n for n in nodes}
    own_prefix = str(tree.get("tree_id", "")) + ":"

    kids = {}
    for n in nodes:
        if n.get("type") in ("skill", "capstone") and n.get("parent"):
            kids.setdefault(n["parent"], []).append(n)

    stats = {}
    for n in nodes:
        if n.get("type") in ("skill", "capstone"):
            c, t, missing = _leaf_counts(n, base_dir)
            stats[n["id"]] = {"checked": c, "total": t, "file_missing": missing}

    cache, visiting = {}, set()

    def status(i):
        if i in cache:
            return cache[i]
        if i in visiting:  # cycle; the validator reports it
            return "locked"
        visiting.add(i)
        try:
            s = _status(by_id[i])
        finally:
            visiting.discard(i)
        cache[i] = s
        return s

    def settled(i):
        return status(i) in ("done", "skipped")

    def unmet(n):
        return [r for r in n.get("requires", []) if r in by_id and not settled(r)]

    def _status(n):
        if n.get("skipped"):
            return "skipped"
        if n.get("type") == "gear":
            ch = kids.get(n["id"], [])
            if not ch:
                return "locked" if unmet(n) else "not_expanded"
            active = [c for c in ch if not c.get("skipped")]
            if not active:
                return "skipped"
            if all(status(c["id"]) == "done" for c in active):
                return "done"
            if any(stats[c["id"]]["checked"] > 0 for c in active):
                return "in_progress"
            return "locked" if unmet(n) else "available"
        st = stats[n["id"]]
        if st["checked"] >= st["total"]:
            return "done"
        if st["checked"] > 0:
            return "in_progress"
        blockers = unmet(n)
        gear = by_id.get(n.get("parent"))
        if gear:
            blockers += unmet(gear)
            if n.get("type") == "capstone":
                blockers += [c["id"] for c in kids.get(gear["id"], [])
                             if c.get("type") == "skill" and not settled(c["id"])]
        return "locked" if blockers else "available"

    gears_out, warnings = [], []
    sum_num = sum_den = 0.0
    expanded_dens = []
    pending_placeholders = []  # indexes of gears that need a placeholder weight

    for g in (n for n in nodes if n.get("type") == "gear"):
        ch = kids.get(g["id"], [])
        active = [c for c in ch if not c.get("skipped")]
        num = sum(leaf_weight(c) * stats[c["id"]]["checked"] / stats[c["id"]]["total"]
                  for c in active)
        den = sum(leaf_weight(c) for c in active)

        node_rows = []
        for c in ch:
            st = stats[c["id"]]
            if st["file_missing"]:
                warnings.append(f"{c['id']}: file '{c.get('file')}' not found; "
                                f"counted as a single unit")
            node_rows.append({
                "id": c["id"],
                "type": c["type"],
                "title": c.get("title", c["id"]),
                "status": status(c["id"]),
                "checked": st["checked"],
                "total": st["total"],
                "percent": round(100.0 * st["checked"] / st["total"], 1),
                "weight": leaf_weight(c),
                "est_hours": c.get("est_hours"),
                "file": c.get("file"),
                "file_missing": st["file_missing"],
                "skipped": bool(c.get("skipped")),
                "external_requires": [r for r in c.get("requires", [])
                                      if r not in by_id and not r.startswith(own_prefix)],
            })

        gstatus = status(g["id"])
        row = {
            "id": g["id"],
            "title": g.get("title", g["id"]),
            "status": gstatus,
            "expanded": bool(ch),
            "percent": round(100.0 * num / den, 1) if den else None,
            "requires": g.get("requires", []),
            "est_hours": g.get("est_hours"),
            "nodes": node_rows,
        }
        gears_out.append(row)

        if gstatus == "skipped":
            continue
        if ch:
            sum_num += num
            sum_den += den
            expanded_dens.append(den)
        else:
            pending_placeholders.append(row)

    placeholder = (sum(expanded_dens) / len(expanded_dens)) if expanded_dens else PLACEHOLDER_GEAR_WEIGHT
    sum_den += placeholder * len(pending_placeholders)

    leaves = [r for g in gears_out for r in g["nodes"] if not r["skipped"]]

    # What to do next: finish what is started, then take what is available.
    open_gears = {g["id"] for g in gears_out if g["status"] not in ("locked", "skipped")}
    ordered = [(g, r) for g in gears_out if g["id"] in open_gears for r in g["nodes"]]
    nxt = [r for g, r in ordered if r["status"] == "in_progress"]
    nxt += [r for g, r in ordered if r["status"] == "available"]
    next_up = [{"id": r["id"], "title": r["title"], "status": r["status"]} for r in nxt[:3]]

    return {
        "tree_id": tree.get("tree_id"),
        "title": tree.get("title"),
        "mode": get_config(tree)["mode"],
        "percent": round(100.0 * sum_num / sum_den, 1) if sum_den else None,
        "counts": {"done": sum(1 for r in leaves if r["status"] == "done"),
                   "total": len(leaves)},
        "gears": gears_out,
        "next": next_up,
        "needs_expansion": [g["id"] for g in gears_out if g["status"] == "not_expanded"],
        "warnings": warnings,
    }
