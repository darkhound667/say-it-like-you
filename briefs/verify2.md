# Brief verify2: fact-check and rate round-3 ideas

## Goal
Write `VERIFIED-2.md`: for every idea ID in `CLAUDE-IDEAS-2.md` give a feasibility verdict. NO changes to the product.

## Context
Read `CLAUDE-IDEAS-2.md`, `API_CONTRACT.md`, `server.py`, `frontend/index.html`. Check each idea against what the existing code and routes can actually do: do the DOM ids / functions it hooks into exist? Does it need new server routes? Does the browser feature work on mobile Safari/Chrome (decodeAudioData, download via blob anchor, MediaRecorder reuse, localStorage)? Count Sarvam calls against the throttle (<= 8 clone calls/min, 30/hour/session, 200 chars). Flag anything that would break privacy promises (voices live in Sarvam up to 2 h). No network calls, no Sarvam credits.

## Files you may touch
- VERIFIED-2.md (only)

## Requirements
A Markdown table: ID | Idea | Feasible with existing routes? | What must change (file + hook points) | Real minutes | Risk | Verdict (BUILD / MAYBE / SKIP). Then: a recommended batch of up to 4 BUILD ideas that can be built in parallel with ONLY ONE editor on `frontend/index.html` at a time (say which two or three should be done sequentially in one agent, and what can be a separate file such as a static `fallback/` asset), plus a list of wrong or risky claims. Under 80 lines.

## Done when
- [ ] VERIFIED-2.md has the table, the batch plan and the risky-claims list

## Out of scope
- Editing server.py, frontend, tests; network calls.
