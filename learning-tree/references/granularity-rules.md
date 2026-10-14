# Granularity rules

The failure modes are a tree too vague to act on ("Learn the basics") and one too granular to finish (60 nodes on day one). These rules keep it between. `validate_tree.py` warns when a limit is crossed; the numbers live in `scripts/treelib.py` (`LIMITS`).

Contents: limits · designing gears · designing skill nodes · capstones · lazy expansion · re-planning

## Limits

| Thing | Aim | Why |
|---|---|---|
| Levels | exactly 3 (gear, skill, capstone) | Deeper trees hide the next action. |
| Gears per tree | 4-8 | Fits in working memory; a fresh learner can see the whole path. |
| Skill nodes per gear | 3-6 | Enough to be a real area, few enough to finish. |
| Hours per skill node | 1-10 | Under 1: merge into a neighbor. Over 10: split. |
| Hours per gear | roughly 10-25 | A few weeks at typical hobby pace. |
| Todos per node | 3-7 | A checklist you can hold in your head. |
| Alternatives per node | 0-3 | Choice is a cost; keep it small. |
| Capstones per gear | 1 | One clear proof of the gear. |

## Designing gears

A gear is a **capability you could name and demonstrate**, not a topic heading. "Write and run small programs" is a gear; "Syntax" is not. Test: can you complete the sentence "After this gear I can ___"?

- Order gears by dependency, and set `requires`. Parallel gears (same prerequisite) are fine: the person chooses.
- Avoid a catch-all last gear ("Advanced topics"). Name what the advanced capability actually is.
- Base gears on what several curricula or roadmaps agree on, not on one source (see `sources.md`).

## Designing skill nodes

A skill node is **one thing the person can demonstrate** after 1-10 hours: "borrow a value without copying it", not "memory management".

- Name nodes with a verb or a concrete noun phrase.
- If you cannot write 3 todos that produce something, the node is too vague. If you need more than 7, it is too big.
- If two nodes always get done together in one sitting, merge them.
- Chain nodes with `requires` only when order truly matters; unneeded chains make the tree feel like a corridor.

## Capstones

A capstone is the proof that the gear stuck. It must produce an artifact someone else could look at.

- Offer two routes: **Build** (small project) and **Write** (summary, explainer or blog post in their own words, ideally with their own diagram or example). Let the person choose.
- Bound the size ("under 200 lines", "one page", "at least 8 commits") so it cannot swallow a month.
- 2-4 acceptance criteria that a stranger could check.
- Tailor it to the person's goal from intake; a generic capstone is a worksheet.
- Skip capstones in `minimal` mode.

## Lazy expansion

Generate **all gears** up front but expand **only the active gear** into skill nodes. Reasons: links and best practice age, expanding everything burns research on content that may never be reached, and a short visible path motivates. Expand the next gear when the previous is done, or when the person asks. `progress.py` reports gears that are ready to expand. (`minimal` mode expands every gear because it costs no research; `full` mode expands everything on request.)

## Re-planning

| Situation | Action |
|---|---|
| Node too big | Replace it with two nodes (split hours); move any ticked todos to the node they belong to. |
| Nodes too small | Merge: combine todos, sum hours, update `requires` that pointed at the removed id. |
| Too easy | `"skipped": true`, or reduce to a quick check-todo. |
| Too hard | Insert a prerequisite skill node before it; do not lower the bar. |
| Not relevant to their goal | `"skipped": true`. |
| Goal changed | Add or reorder gears; keep finished work. |

Never delete a node that has ticked boxes; mark it skipped or keep it. After any structural change, run `validate_tree.py`.
