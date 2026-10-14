#!/usr/bin/env bash
# Build learning-tree.skill (a zip of the learning-tree/ folder) at the repo root.
# Used locally and by the release workflow, so both produce the same package.
#   usage: bash dev/package.sh [output-file]
set -euo pipefail

cd "$(dirname "$0")/.."
OUT="${1:-learning-tree.skill}"

[ -f learning-tree/SKILL.md ] || { echo "error: learning-tree/SKILL.md not found" >&2; exit 1; }

rm -f "$OUT"
# -X drops extra file attributes, -D skips empty directory entries;
# the excludes keep test leftovers out of the package
zip -rqXD "$OUT" learning-tree -x "*/__pycache__/*" "*.pyc" "*/.DS_Store"

echo "Built $OUT:"
unzip -l "$OUT"