# Node file template

One file per skill or capstone node, at the path in the node's `file` field (convention: `nodes/<slug>.md`, slug = the part of the id after the colon).

## Skill node

```markdown
---
id: <tree_id>:<slug>
tree: <tree_id>
type: skill
gear: <tree_id>:<gear-slug>
est_hours: <number>
tags: [learning-tree/<tree_id>]
---
# <Node title>

**Why this matters:** <one sentence>
**You'll be able to:** <one sentence, observable outcome>

## Primary
- 🎥 [Title](url) — Creator · ~N min — why this one
- 📄 [Title](url) — Site · ~N min read — why this one

## Alternatives (optional)
- 🎥 [Title](url) — pick this if <a concrete reason: shorter / deeper / prefers text>
- 📄 [Title](url) — pick this if <...>

## Todos
- [ ] <an action that produces something>
- [ ] <...>
```

## Capstone node

```markdown
---
id: <tree_id>:<gear-slug>-capstone
tree: <tree_id>
type: capstone
gear: <tree_id>:<gear-slug>
est_hours: <number>
tags: [learning-tree/<tree_id>]
---
# Capstone: <name>

Pick one:
- **Build:** <a small project that uses the gear's skills, with a size bound>
- **Write:** <a summary, explainer or blog post in their own words, with a size bound>

## Acceptance criteria
- [ ] <checkable statement>
- [ ] <checkable statement>

## Output
- Link or path:
```

## Rules (and why)

- **Frontmatter `id` must equal the node id.** The validator compares them; a mismatch means the file was copied to the wrong node.
- **Resources are plain bullets, not checkboxes.** Only todos count toward progress, so progress measures doing, not browsing.
- **Primary = exactly one video and one article** (fewer if the topic genuinely has none). They are the recommended path.
- **Alternatives are optional and never block anything.** At most three. Each says *when to pick it* ("shorter", "more advanced", "prefers text", "hands-on"), so the person chooses by need, not guesswork. They differ from the primary along one axis only.
- **3-7 todos, each an action that produces something** ("explain X in three sentences without notes", "build Y", "fix Z"). Todos that start with watch/read/study trigger a validator warning, because finishing a video is not evidence of learning.
- **Mark extras with `(optional)`** inside the todo text if you want a stretch task that does not count.
- **Capstone:** two ways to prove the gear (build or write), 2-4 acceptance criteria, sized to 3-6 hours. The `Output` line is where the person records the link or path to what they made; it is not counted.
- **Keep it short.** A node file should fit on one screen. If it does not, the node is too big: split it.
- Durations and creators come from the page you actually opened. If you could not confirm a duration, omit it rather than guess.
