# Brief ideate-b: technical depth round — Sarvam capability stacking

## Goal
Write `IDEAS-B.md`: 8 ideas that use MORE of Sarvam's stack (and the cloned voice) in clever ways to make "Say it like you" technically impressive. IDEAS ONLY, no code changes.

## Context
Read `API_CONTRACT.md`, `server.py`, `frontend/index.html`, `IDEAS.md` (earlier round: do not repeat). We currently use: voice cloning (create_voice, convert with pace), translate (sarvam-translate:v1), transliterate, STT (saaras:v4). Sarvam also offers (verify in docs via the sarvam-docs MCP `searchDocs` tool if available, otherwise say "unverified"): bulbul TTS with pronunciation dictionaries, STT translate/translit/codemix/verbatim modes, word-level timestamps, language identification, the sarvam-105b LLM (chat, structured output), document vision, dubbing with voice cloning, streaming TTS/WebSocket, voice cloning streaming (`convert_stream`), `enable_qc`, `ref_text`. Examples to go beyond: LLM-generated personalised phrase packs and tongue twisters per language, LLM coaching feedback in the learner's language, timestamp-aligned karaoke highlighting, streaming playback for latency, pronunciation-dictionary fixes for tricky words, dub-a-video-in-my-voice, phone-OCR a sign/menu then say it in my voice, code-mixed Hinglish handling.

## Files you may touch
- IDEAS-B.md (only)

## Requirements
For each idea: name, pitch, 10-second wow, the exact Sarvam calls (SDK method + key params, mark verified/unverified), new route JSON shape, effort in minutes, latency/rate-limit risk (clone endpoint is 10 req/min). End with a ranked top 3 and a 6-bullet build plan for #1 that fits in 15 minutes. Under 120 lines.

## Done when
- [ ] IDEAS-B.md exists with 8 ideas, ranked top 3, and the build plan

## Out of scope
- Any code changes, any Sarvam API calls that spend credits.
