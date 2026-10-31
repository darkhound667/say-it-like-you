#!/usr/bin/env bash
# Run one Codex task in its own git worktree so parallel tasks never collide.
#
# Usage:
#   scripts/codex-task.sh <task-id> [light|standard|heavy]   run briefs/<id>.md (default tier: standard)
#   scripts/codex-task.sh merge <task-id>                    fast-forward/merge codex/<id> into main, drop worktree
#
# Tiers (model / reasoning effort) — chosen to protect Codex limits, never uses gpt-6-astra:
#   light     gpt-6-luna    low      boilerplate, scaffolding, tests, docs, parallel helper workers
#   standard  gpt-6.1-sol   medium   most feature work
#   heavy     gpt-6.1-sol   high     hard logic, tricky debugging
#
# Output is kept short on purpose (saves the manager's tokens): only Codex's final message
# and a diffstat are printed. Full transcript: logs/<id>.log
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODEX="${CODEX_BIN:-/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex}"

if [ "${1:-}" = "merge" ]; then
  ID="${2:?usage: codex-task.sh merge <task-id>}"
  git -C "$ROOT" merge --no-edit "codex/$ID"
  git -C "$ROOT" worktree remove --force "$ROOT/../hackathon-wt/$ID" 2>/dev/null || true
  git -C "$ROOT" branch -d "codex/$ID"
  exit 0
fi

ID="${1:?usage: codex-task.sh <task-id> [light|standard|heavy]}"
TIER="${2:-standard}"
case "$TIER" in
  light)    MODEL="gpt-6-luna";  EFFORT="low" ;;
  standard) MODEL="gpt-6.1-sol"; EFFORT="medium" ;;
  heavy)    MODEL="gpt-6.1-sol"; EFFORT="high" ;;
  *) echo "unknown tier: $TIER (light|standard|heavy)" >&2; exit 2 ;;
esac
# Optional override for a one-off, but astra is never allowed (burns limits too fast).
MODEL="${CODEX_MODEL:-$MODEL}"
case "$MODEL" in *astra*) echo "refusing to use astra" >&2; exit 2 ;; esac

BRIEF="$ROOT/briefs/$ID.md"
WT="$ROOT/../hackathon-wt/$ID"
[ -f "$BRIEF" ] || { echo "missing brief: $BRIEF" >&2; exit 1; }
mkdir -p "$ROOT/logs"

if [ ! -d "$WT" ]; then
  git -C "$ROOT" worktree add -q -b "codex/$ID" "$WT"
fi

cd "$WT"
set +e
"$CODEX" exec \
  --model "$MODEL" \
  -c "model_reasoning_effort=\"$EFFORT\"" \
  --sandbox workspace-write \
  --output-last-message "$ROOT/logs/$ID.last" \
  "Read AGENTS.md and PLAN.md, then carry out the task in briefs/$ID.md. You are on branch codex/$ID. Leave changes uncommitted; the manager commits." \
  > "$ROOT/logs/$ID.log" 2>&1
RC=$?
set -e

# Codex's sandbox cannot write worktree git metadata, so commit here on its behalf.
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -q -m "codex($ID, $MODEL/$EFFORT): $(head -1 "$BRIEF" | sed 's/^# *//')"
fi

echo "== $ID | $MODEL/$EFFORT | codex exit=$RC =="
cat "$ROOT/logs/$ID.last" 2>/dev/null || tail -20 "$ROOT/logs/$ID.log"
echo "-- diffstat vs main --"
git diff --stat main...HEAD | tail -15
