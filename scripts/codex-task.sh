#!/usr/bin/env bash
# Run one Codex task in its own git worktree so parallel tasks never collide.
# Usage: scripts/codex-task.sh <task-id>
#   Reads  briefs/<task-id>.md
#   Makes  ../hackathon-wt/<task-id> on branch codex/<task-id>
#   Writes logs/<task-id>.log (full output) and logs/<task-id>.last (final message)
set -euo pipefail

ID="${1:?usage: codex-task.sh <task-id>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRIEF="$ROOT/briefs/$ID.md"
WT="$ROOT/../hackathon-wt/$ID"
CODEX="${CODEX_BIN:-/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex}"

[ -f "$BRIEF" ] || { echo "missing brief: $BRIEF" >&2; exit 1; }
mkdir -p "$ROOT/logs"

if [ ! -d "$WT" ]; then
  git -C "$ROOT" worktree add -q -b "codex/$ID" "$WT"
fi

cd "$WT"
"$CODEX" exec \
  --sandbox workspace-write \
  --output-last-message "$ROOT/logs/$ID.last" \
  "Read AGENTS.md and PLAN.md, then carry out the task in briefs/$ID.md. You are on branch codex/$ID; commit your work there if git allows it; if not, leave changes uncommitted and say so." \
  2>&1 | tee "$ROOT/logs/$ID.log"
