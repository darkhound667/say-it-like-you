# Hackathon Plan — "Say it like you"

> Owner: Claude (manager). Executors: Codex (server), agy (UI), Hyde (tests/docs).

## Problem (Sarvam AI, IIT Bombay)
Clone a learner's voice, then generate correct pronunciation of new vocabulary/phrases in their own voice, across Indian languages.

## Product
Website, no install/login. Visitor records ~10 s -> Sarvam voice clone -> types/translates a phrase -> hears it in THEIR voice in the target language. API contract: `API_CONTRACT.md` (confirmed SDK facts, 12 clone languages).

## Architecture
`server.py` (Flask, holds key, sessions token->voice_id, limits, janitor) + `frontend/index.html` (single file, works from file:// and served at /).

## Decisions log
- Voice-clone languages are 12 (docs), not 13 as the brief said.
- Sarvam clone endpoint is 10 req/min on Starter -> server-side throttle + caching.
- No cloudflared/ngrok installed locally -> ask user for deploy choice at Phase 1.5.
