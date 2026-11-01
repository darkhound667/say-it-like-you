# Brief chorus: "One voice, many languages" feature

## Goal
In `frontend/index.html` add a **Chorus** card (use the empty `#slot-reel` section, make it visible once the voice is enrolled): the visitor types/keeps a short English phrase (default "Hello, I'm so happy to meet you."), taps "Play my chorus", and hears THEIR cloned voice say it in 4 languages back-to-back: Hindi, Tamil, Bengali, Telugu. Maximum build time 8 minutes. Keep everything else working.

## Context
Read `API_CONTRACT.md` (routes) and the existing `frontend/index.html` (single file, inline JS; has `request()` helper, `state`, mock mode via `?mock=1`, existing play/replay code). Do NOT add new backend routes; use `/api/translate` then `/api/speak` per language, strictly sequential (Sarvam allows ~10 clone calls/min), reusing cached clips.

## Files you may touch
- frontend/index.html (only)

## Requirements
1. Card UI: phrase input, "Play my chorus" button, a row of 4 language tiles (native script name + English name). The active tile glows/pulses while its clip plays; each tile shows the translated native text and romanized line (from `/api/speak` or `/api/translate` response) once ready, and a small replay button.
2. Flow: for each language in order: translate (skip if source==target), speak, add clip, then play it immediately (play inside the click handler chain; if the browser blocks autoplay show a big "Tap to play" on the tile). Prefetch: while clip N plays, request clip N+1.
3. Inline error handling: on 429/any error stop cleanly, show the contract `error.message` on the tile, keep finished clips replayable. Add a "Replay chorus" button that replays completed clips with no new requests.
4. Works in `?mock=1` mode. Match existing visual style. No console errors. Mobile-first.

## Done when
- [ ] `node -e "const fs=require('fs');const s=fs.readFileSync('frontend/index.html','utf8');new Function(s.match(/<script>([\s\S]*)<\/script>/)[1]);console.log('ok')"` prints ok
- [ ] Chorus works end to end in `?mock=1`

## Out of scope
- server.py, tests, README.
