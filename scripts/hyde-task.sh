#!/usr/bin/env bash
# Run one brief with OpenCode on the Hyde AI inference models, in its own git worktree.
# Same flow as codex-task.sh / agy-task.sh, so all three executors can run in parallel.
#
# Usage:
#   scripts/hyde-task.sh <task-id> [light|standard|heavy]   run briefs/<id>.md (default: standard)
#   scripts/hyde-task.sh merge <task-id>                    merge branch hyde/<id> into main, drop worktree
#
# Tiers (OpenCode provider hyde-inference):
#   light     hyde/glm-5.3-flash   boilerplate, scaffolding, tests, docs
#   standard  hyde/kimi-k3         most feature work
#   heavy     hyde/kimi-k3 --variant high   hard logic / debugging
#
# Uses the separate OpenCode profile in ~/.hyde-opencode (what the `opencode-hyde` alias does).
# Key comes from $HYDE_INFERENCE_API_KEY in the environment; it is never written to the repo.
# Never uses --auto (auto-approve everything). Headless runs can't prompt, so permissions are
# pre-set: edits allowed, a short allow-list of shell commands, everything else denied.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OC="${OPENCODE_BIN:-$HOME/.opencode/bin/opencode}"

if [ "${1:-}" = "merge" ]; then
  ID="${2:?usage: hyde-task.sh merge <task-id>}"
  git -C "$ROOT" merge --no-edit "hyde/$ID"
  git -C "$ROOT" worktree remove --force "$ROOT/../hackathon-wt/$ID" 2>/dev/null || true
  git -C "$ROOT" branch -d "hyde/$ID"
  exit 0
fi

ID="${1:?usage: hyde-task.sh <task-id> [light|standard|heavy]}"
TIER="${2:-standard}"
EXTRA=()
case "$TIER" in
  light)    MODEL="hyde-inference/hyde/glm-5.3-flash" ;;
  standard) MODEL="hyde-inference/hyde/kimi-k3" ;;
  heavy)    MODEL="hyde-inference/hyde/kimi-k3"; EXTRA=(--variant high) ;;
  *) echo "unknown tier: $TIER (light|standard|heavy)" >&2; exit 2 ;;
esac
MODEL="${HYDE_MODEL:-$MODEL}"
: "${HYDE_INFERENCE_API_KEY:?HYDE_INFERENCE_API_KEY is not set in this shell}"

BRIEF="$ROOT/briefs/$ID.md"
WT="$ROOT/../hackathon-wt/$ID"
[ -f "$BRIEF" ] || { echo "missing brief: $BRIEF" >&2; exit 1; }
mkdir -p "$ROOT/logs"

if [ ! -d "$WT" ]; then
  git -C "$ROOT" worktree add -q -b "hyde/$ID" "$WT"
fi

# Edits allowed; shell limited to running/checking code; everything else denied.
export OPENCODE_CONFIG_CONTENT='{"permission":{"edit":"allow","bash":{"*":"deny","python3 *":"allow","python *":"allow","node *":"allow","npm test*":"allow","npm run *":"allow","pytest*":"allow","ls*":"allow","cat *":"allow","git status*":"allow","git diff*":"allow"}}}'
export XDG_CONFIG_HOME="$HOME/.hyde-opencode/config" XDG_DATA_HOME="$HOME/.hyde-opencode/data"

cd "$WT"
set +e
"$OC" run -m "$MODEL" ${EXTRA[@]+"${EXTRA[@]}"} \
  "Read AGENTS.md and PLAN.md, then carry out the task in briefs/$ID.md. You are in a git worktree on branch hyde/$ID. Do not run git commit; the manager commits. End with: files changed, how you verified, anything unfinished." \
  < /dev/null > "$ROOT/logs/$ID.log" 2>&1
RC=$?
set -e
sed -E 's/\x1b\[[0-9;]*m//g' "$ROOT/logs/$ID.log" > "$ROOT/logs/$ID.last"

if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -q -m "hyde($ID, ${MODEL##*/}): $(head -1 "$BRIEF" | sed 's/^# *//')"
fi

echo "== $ID | opencode ${MODEL#hyde-inference/} | exit=$RC =="
tail -25 "$ROOT/logs/$ID.last"
echo "-- diffstat vs main --"
git diff --stat main...HEAD | tail -15
