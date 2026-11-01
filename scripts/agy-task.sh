#!/usr/bin/env bash
# Run one brief with the Antigravity CLI (agy) in its own git worktree — same flow as codex-task.sh,
# so Codex and Antigravity can work in parallel and spread the usage limits across two pools.
#
# Usage:
#   scripts/agy-task.sh <task-id> [light|standard|heavy]   run briefs/<id>.md (default tier: standard)
#   scripts/agy-task.sh merge <task-id>                    merge branch agy/<id> into main, drop worktree
#
# Tiers (model):
#   light     gemini-3.8-flash-low     boilerplate, scaffolding, tests, docs, UI markup
#   standard  gemini-3.8-flash-high    most feature work
#   heavy     claude-sonnet-4-6 (high) hard logic / debugging
# Never uses opus. Never uses --dangerously-skip-permissions: edits are auto-accepted inside the
# worktree (--mode accept-edits) and shell commands are sandboxed (--sandbox).
#
# Output is short on purpose: final response + diffstat. Full transcript: logs/<id>.log
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGY="${AGY_BIN:-$HOME/.local/bin/agy}"

if [ "${1:-}" = "merge" ]; then
  ID="${2:?usage: agy-task.sh merge <task-id>}"
  git -C "$ROOT" merge --no-edit "agy/$ID"
  git -C "$ROOT" worktree remove --force "$ROOT/../hackathon-wt/$ID" 2>/dev/null || true
  git -C "$ROOT" branch -d "agy/$ID"
  exit 0
fi

ID="${1:?usage: agy-task.sh <task-id> [light|standard|heavy]}"
TIER="${2:-standard}"
EXTRA=()
case "$TIER" in
  light)    MODEL="gemini-3.8-flash-low" ;;
  standard) MODEL="gemini-3.8-flash-high" ;;
  heavy)    MODEL="claude-sonnet-4-6"; EXTRA=(--effort high) ;;
  *) echo "unknown tier: $TIER (light|standard|heavy)" >&2; exit 2 ;;
esac
MODEL="${AGY_MODEL:-$MODEL}"
case "$MODEL" in *opus*) echo "refusing to use opus" >&2; exit 2 ;; esac

BRIEF="$ROOT/briefs/$ID.md"
WT="$ROOT/../hackathon-wt/$ID"
[ -f "$BRIEF" ] || { echo "missing brief: $BRIEF" >&2; exit 1; }
mkdir -p "$ROOT/logs"

if [ ! -d "$WT" ]; then
  git -C "$ROOT" worktree add -q -b "agy/$ID" "$WT"
fi

# Headless mode cannot prompt, so pre-allow only the commands needed to run and check code.
# (Not --dangerously-skip-permissions. No git commit/push, no rm, no network tools.)
ALLOW='{"permissions":{"allow":["command(python3)","command(python)","command(node)","command(npm test)","command(npm run)","command(npx)","command(pytest)","command(ls)","command(cat)","command(git status)","command(git diff)"]}}'

cd "$WT"
set +e
"$AGY" --model "$MODEL" ${EXTRA[@]+"${EXTRA[@]}"} --settings "$ALLOW" \
  --mode accept-edits --sandbox --print-timeout "${AGY_TIMEOUT:-20m}" \
  -p "Read AGENTS.md and PLAN.md, then carry out the task in briefs/$ID.md. You are in a git worktree on branch agy/$ID. Do not run git commit; the manager commits. End with: files changed, how you verified, anything unfinished." \
  < /dev/null > "$ROOT/logs/$ID.log" 2>&1
RC=$?
set -e
cp "$ROOT/logs/$ID.log" "$ROOT/logs/$ID.last"

if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -q -m "agy($ID, $MODEL): $(head -1 "$BRIEF" | sed 's/^# *//')"
fi

echo "== $ID | agy $MODEL | exit=$RC =="
tail -25 "$ROOT/logs/$ID.last"
echo "-- diffstat vs main --"
git diff --stat main...HEAD | tail -15
