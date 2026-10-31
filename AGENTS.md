# Instructions for Codex

You are the executor on a time-boxed hackathon project. A manager (Claude) plans the work and
reviews your output. Read `PLAN.md` for context before starting.

## Rules
- Do exactly what the brief in `briefs/<id>.md` asks. No extra features, no refactors outside scope.
- Only touch files listed in the brief's "Files you may touch". If you need others, say so in your final message instead.
- Do not edit `PLAN.md`, `TASKS.md`, or `AGENTS.md`.
- Prefer simple, readable code over clever code. Add short docstrings/comments on non-obvious logic.
- Never commit secrets. Read keys from environment variables; list them in `.env.example`.
- Run the project's tests/lint/build if they exist and the brief says to; fix what you break.
- Commit your work on the branch you were given with a clear message. Do not push.

## Final message format
End with:
1. What you changed (files + one line each)
2. How you verified it (commands run + result)
3. Anything unfinished, assumptions made, or questions for the manager
