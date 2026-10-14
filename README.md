# learning-tree

An agent skill that turns "I want to learn X" into a small, trackable learning tree. The tree is stored as plain JSON and Markdown files, so it opens in Obsidian or any editor, and your progress is always computed from the checkboxes you tick.

> **Status:** early (v0.2.0). The scripts are tested; real-world use with a live agent is still being validated. Expect rough edges.

## What it does

- **Builds a tree** from a short intake (goal, current level, hours per week): big capability areas ("gears"), the skills inside each, and a capstone project per gear.
- **Finds resources** with web search, one video and one article per skill, and checks that the links are alive.
- **Tracks progress** from checkboxes in the node files. Nothing is stored twice, so nothing drifts out of sync.
- **Resumes and exports.** Export a zip to carry your tree between sessions, or optionally an Obsidian canvas.

## Vocabulary

| Term | Meaning |
|---|---|
| Tree | One learning goal (e.g. "Learn Git") |
| Gear | A big capability area; 4-8 per tree |
| Skill node | One demonstrable thing inside a gear; 3-6 per gear |
| Capstone | A small project or write-up that proves the gear stuck; 1 per gear |

## Modes

| Mode | Produces |
|---|---|
| `minimal` | Gears and skill nodes only. No resources, todos or capstones. |
| `guided` (default) | Everything, expanding only the active gear. |
| `full` | Everything, all gears expanded up front. |

## Install

<!-- TODO: confirm these steps after the claude.ai upload test -->

1. Download `learning-tree.skill` from the [latest release](https://github.com/RaphaelMouallem/learning-tree/releases).
2. Upload it in your agent's skill settings. (A `.skill` file is a zip of the `learning-tree/` folder.)

The helper scripts are optional and need **Python 3.9+** with only the standard library. Without them, the skill falls back to counting checkboxes by hand.

## Try it

Once installed, ask for something like:

> I want to learn Rust. I know some Python and have about 5 hours a week.

To resume later, upload the zip from your last session and ask what to do next.

## Repository layout

```
learning-tree/   the skill itself (this folder is what gets packaged)
dev/             regression tests and trigger evals (not packaged)
```

## Development

Run the tests from the repository root:

```
python dev/test_learning_tree.py -v
```

`dev/trigger-evals.json` holds prompts that should and should not trigger the skill, for checking the description.

## License

MIT. See [`learning-tree/LICENSE`](learning-tree/LICENSE).