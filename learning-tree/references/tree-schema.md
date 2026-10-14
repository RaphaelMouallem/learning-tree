# tree.json schema

Contents: top-level fields · config · nodes · statuses · progress rules · sub-trees · minimal example

## Top-level fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | int | yes | Always `1`. |
| `tree_id` | string | yes | Lowercase letters, digits, `-`, `_`. Prefix of every node id. |
| `title` | string | yes | Shown in the overview. |
| `goal` | string | no | What the person wants to *do* with the topic. |
| `level` | string | no | e.g. `beginner`. |
| `hours_per_week` | number | no | Used to estimate calendar time. |
| `config` | object | no | See below. |
| `parent_tree` | string | no | Reserved for sub-trees (a node id in another tree). Validated, otherwise ignored. |
| `nodes` | array | yes | Flat list; order is display order. |

## config

| Key | Values | Default | Effect |
|---|---|---|---|
| `mode` | `minimal` / `guided` / `full` | `guided` | Chooses presets and expansion policy. |
| `resources` | `none` / `one-per-node` / `with-alternatives` | `with-alternatives` (`none` in minimal) | What node files contain; the validator checks it. |
| `capstones` | bool | `true` (`false` in minimal) | Whether expanded gears should have a capstone. |
| `depth` | `gears-only` / `gears+skills` | `gears+skills` | `gears-only` is the lightest possible tree. |

Explicit keys override the mode preset.

## nodes

Every node: `id`, `type`, `title`, `parent`, `requires`. Optional: `est_hours`, `file`, `weight`, `skipped`, `done`.

| Field | Rules |
|---|---|
| `id` | `<tree_id>:<slug>`, lowercase, unique. Example: `rust:ownership`. |
| `type` | `gear`, `skill`, or `capstone`. |
| `parent` | `null` for gears; the gear's id for skills and capstones. |
| `requires` | List of node ids that must be done or skipped first. May name a gear (= every node in it) or a node in another tree (reported, not enforced). |
| `est_hours` | Number >= 0. Skills: aim 1-10. |
| `file` | Relative path inside the tree folder, e.g. `nodes/ownership.md`. Skills/capstones only. Omit in minimal mode. |
| `weight` | Positive number. Defaults: skill 1, capstone 2. |
| `skipped` | `true` removes the node from every percentage. |
| `done` | `true` completes a node that has **no checkable todos** (minimal mode). Ignored when the node file has todos. |

Implicit prerequisites, so you do not have to write them: every node waits for its gear's own `requires`, and a capstone waits for every sibling skill to be done or skipped.

One gear can have at most one capstone. A gear with no child nodes is "not expanded".

## Statuses

`done` · `in_progress` · `available` · `locked` · `skipped` · `not_expanded` (gears only)

- A node is `done` when all its counted checkboxes are ticked; `in_progress` when some are. Work already ticked always shows as in progress/done, even if the node is still `locked`.
- Otherwise `locked` until prerequisites are done/skipped, else `available`.
- A gear is `done` when all its non-skipped nodes are done, `in_progress` when any has progress, `not_expanded` when it has no nodes and is unlocked.

## What counts toward progress

Only `- [ ]` / `- [x]` items under a heading starting with **Todos** (or **Todo**) or **Acceptance criteria**, including nested sub-headings. Ignored: checkboxes anywhere else, inside code fences, under `Alternatives`, and any item containing `(optional)`.

## Progress arithmetic (for doing it by hand)

- Node fraction = ticked / counted (a node with no counted items is 1 unit: 1 if `done: true`, else 0).
- Gear % = sum(weight x fraction) / sum(weight) over non-skipped nodes.
- Tree % = same sum across all gears, where every unexpanded, non-skipped gear counts as 0% at the average weight of the expanded gears (6 if none are expanded). This keeps finishing the first gear from reading as 100%.

## Sub-trees (reserved, not implemented)

IDs are namespaced so trees can be combined later. To go deeper on a node, create a new tree whose `parent_tree` is that node's id; cross-tree `requires` are allowed. Scripts do not merge trees yet.

## Minimal valid example

```json
{
  "schema_version": 1,
  "tree_id": "rust",
  "title": "Learn Rust",
  "config": {"mode": "minimal"},
  "nodes": [
    {"id": "rust:foundations", "type": "gear", "title": "Foundations", "parent": null, "requires": []},
    {"id": "rust:ownership", "type": "skill", "title": "Ownership and borrowing", "parent": "rust:foundations", "requires": [], "est_hours": 6}
  ]
}
```

A full, valid tree with node files is in `assets/example-tree/`.
