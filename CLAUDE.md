# Hackathon — Claude is manager, Codex does the heavy lifting

Hackathon runs 2pm–5pm IST. Goal: spend Codex's tokens, not Claude's, so Claude's session lasts.
Claude keeps the context; Codex gets a short self-contained brief instead of re-explaining the project.

## Rules
1. **Every coding task goes to Codex.** Do not write feature code yourself.
   Write `briefs/<id>.md` (copy `briefs/TEMPLATE.md`; be terse and exact), then run
   `scripts/codex-task.sh <id> <tier>`.
2. **Pick the cheapest tier that fits:**
   - `light`    gpt-6-luna / low    — boilerplate, scaffolding, tests, docs, config, simple CRUD
   - `standard` gpt-6.1-sol / medium — normal feature work (default)
   - `heavy`    gpt-6.1-sol / high   — hard logic, tricky debugging, only when needed
   **Never use gpt-6-astra** (burns limits). The script refuses it.
3. **Big job = split it.** Break it into independent briefs touching different files and run them
   in parallel (`&` + `wait`), each at `light` where possible. Max 3 at once. Each runs in its own
   worktree `../hackathon-wt/<id>` on branch `codex/<id>`.
4. **Review cheaply.** The script prints only Codex's final report + diffstat. Read the actual diff
   (`git diff main...codex/<id>`) only for the files that matter; run the brief's "Done when" commands.
   - Minor fix (a few lines): do it yourself in the worktree and commit.
   - Real problem: write a short corrective brief and send it back to Codex.
5. **Merge:** `scripts/codex-task.sh merge <id>`. Then update the board with
   `PYTHONPATH=tools python3 -m taskboard set <id> --status done`.
6. **Save Claude tokens:** don't paste large files into chat, don't re-read files you just wrote,
   keep replies short, keep `PLAN.md` the single source of context (update it when scope changes).
7. **Two executors, two separate limit pools — use both.**
   - Codex (`scripts/codex-task.sh <id> <tier>`): primary. Backend, logic, algorithms, debugging.
   - Antigravity `agy` (`scripts/agy-task.sh <id> <tier>`): second pool. Frontend/UI, docs, tests,
     boilerplate, and overflow when running tasks in parallel. Same brief format, same worktree flow
     (branch `agy/<id>`; merge with `scripts/agy-task.sh merge <id>`).
     agy tiers: light = gemini-3.8-flash-low, standard = gemini-3.8-flash-high,
     heavy = claude-sonnet-4-6. Never opus, never `--dangerously-skip-permissions`.
   - When splitting a big job into parallel briefs, spread them across both tools.
   - If one tool hits its limit (quota/rate-limit error in its output), reroute to the other.
     Only when BOTH are exhausted, tell the user before doing the coding yourself.
   - agy headless mode auto-denies any shell command not in the runner's allow-list; if a report
     says "auto-denied", add a `command(<prefix>)` rule to `ALLOW` in `scripts/agy-task.sh`.
8. No pushing, deploying or sending anything outside this machine without the user's go-ahead.

## Files
- `PLAN.md` project context · `TASKS.md` board (CLI: `tools/taskboard`) · `AGENTS.md` Codex's rules
- `briefs/` task briefs · `logs/<id>.log` full Codex transcript, `logs/<id>.last` final report
