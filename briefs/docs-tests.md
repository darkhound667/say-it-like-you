# Brief docs-tests: extend smoke tests and README for the new features

## Goal
Bring `tests/smoke.py` and `README.md` up to date with features added since they were written.

## Context
Read `API_CONTRACT.md` (see the "Additions" section at the bottom), `server.py`, `frontend/index.html`. New since the originals: `POST /api/speak` accepts optional boolean `qc` (invalid type -> 400 `bad_request`; checked after the voice check, so offline tests with no voice get 409 `no_voice`), `POST /api/extract` (multipart `file`; `.txt .md .markdown .docx`; returns `{text,chars,truncated,name}`; errors `unsupported_file` 400, `payload_too_large` 413, `bad_request` 400), the UI features: Chorus (4 languages), Grandma Mode, High-quality take, real-vs-generated A/B, Say my name, expiry countdown, Demo mode, Gentle Mirror (after an attempt, replay up to 3 missed words slowly), and document upload read-aloud (reads at most 5 parts of <=180 chars per click). Also: voice-clone reference is cleaned server-side (silence trimmed, loudness normalised), mic requested with echo cancellation and auto-gain off.

## Files you may touch
- tests/smoke.py
- README.md

## Requirements
1. tests/smoke.py offline checks (no Sarvam credits): `/api/extract` with a tiny in-memory `.txt` (200 + text), `.md` (markdown stripped: no `#` or `**` in output), and a `.docx` built with `zipfile` containing `word/document.xml` with two `w:p` paragraphs (200, both paragraphs present); a `.pdf` name -> 400 `unsupported_file`; no token -> 401 `no_session`; `/api/speak` with `"qc":"yes"` and a session but no voice still returns the envelope (409 `no_voice`). Use stdlib multipart building (`email.mime` or hand-built boundary). Keep existing checks working.
2. README.md: add a "Features" section listing the new features in one line each; add the extract route and `qc` to the API summary; extend the 60-second demo script with a short beat for Grandma Mode and one for Gentle Mirror while keeping it at 60-90 seconds total; add troubleshooting for "voice sounds different" (quiet room, 12-15 s natural speech, cross-language drift is normal) and "document too long" (5 parts per click, 3000-char cap).
3. Do not claim anything not implemented; if unsure whether a feature exists, grep `frontend/index.html`.

## Done when
- [ ] `python3 -c "import ast;ast.parse(open('tests/smoke.py').read())"` passes
- [ ] `python3 tests/smoke.py --base http://localhost:8000` passes if the server is running (it is expected to be)
- [ ] README has Features, extract/qc in API summary, and the extended demo script

## Out of scope
- server.py, frontend, API_CONTRACT.md. Do not run `--live`.
