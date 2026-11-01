# Brief verify: fact-check and rate the Claude-generated ideas

## Goal
Write `VERIFIED.md`: for every idea ID in `CLAUDE-IDEAS.md`, verify feasibility and give a verdict. NO code changes to the product.

## Context
Read `CLAUDE-IDEAS.md`, `API_CONTRACT.md`, `server.py`, `frontend/index.html`. The Python package `sarvamai` is installed: verify SDK claims OFFLINE by introspection (`python3 -c "import inspect; from sarvamai import SarvamAI; c=SarvamAI(api_subscription_key='x'); print(inspect.signature(c.voice_cloning.convert_stream))"`, `dir(c.text)`, `dir(c)`, `dir(c.chat)` etc.). Do NOT make network calls or spend Sarvam credits. For claims you cannot verify offline (pricing, rate limits, docs statements), mark UNVERIFIED.

## Files you may touch
- VERIFIED.md (only)

## Requirements
Output a Markdown table with columns: ID | Idea | Claim check (SDK method/params exist? yes/no/unverified) | Fits existing code? (what must change, files) | Real effort in minutes | Risk | Verdict (BUILD / MAYBE / SKIP). Then: the 5 best ideas to build in a 20-minute window as a combined plan that doesn't make two agents edit the same file at once (split by server.py vs frontend/index.html), and a list of any claim in CLAUDE-IDEAS.md that you found to be wrong. Under 100 lines.

## Done when
- [ ] VERIFIED.md has the table, the 5-idea plan and the wrong-claims list

## Out of scope
- Editing server.py, frontend, tests; network calls.
