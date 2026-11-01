# Brief server: Flask backend for "Say it like you"

## Goal
`server.py`: Flask app that holds the Sarvam key and is the ONLY thing talking to Sarvam. Implements every route in `API_CONTRACT.md` exactly (read it fully first; it has confirmed SDK signatures — do not guess others).

## Files you may touch
- server.py (only)

## Requirements
1. Config: `SARVAM_API_KEY` from env, `python-dotenv` loads `.env`. If missing, print a clear message and `sys.exit(1)`. Optional env: `DAILY_CAP` (150), `PAUSE=1` (every /api route except health returns 503 `paused` "Demo is paused"), `PUBLIC_ORIGIN`, `SESSION_SPEAK_LIMIT` (30, per session/hour), `IP_SPEAK_LIMIT` (60, per IP/hour), `PORT` (8000). `python server.py` runs `app.run(host="0.0.0.0", port, threaded=True)`.
2. Fallback for local dev only: if env key missing AND `~/.sarvam/credentials` has a line `api_key = ...`, use it (never print it).
3. `flask-cors` per contract. `MAX_CONTENT_LENGTH` 5 MB. Global error handlers (HTTPException, SarvamAI `ApiError` and any Exception) -> contract error shape; map Sarvam 401/403 -> `sarvam_auth`, 402/quota -> `sarvam_quota`, 429/5xx -> `sarvam_unavailable` (friendly text). No stack traces to the client; log only error class + short message server-side.
4. Sessions: dict token -> {voice_id, voice_created_at, created_at, last_used, counters, cache}. Token via `secrets.token_urlsafe(24)`. Idle expiry 2 h. Client never sends/receives voice_id. All state access under a lock.
5. Limits: sliding windows for per-session and per-IP (IP = `CF-Connecting-IP`, else first of `X-Forwarded-For`, else `remote_addr`), global daily counter with lock, resets at local midnight. Max text 200 chars. 429 includes `retry_after`. Plus a global Sarvam throttle: lock + deque allowing <= 8 clone-synth calls/minute; wait up to ~6 s for a slot else 429 `rate_limited`. Retry a Sarvam 429 once after 2 s.
6. Enroll: save upload to a temp dir; ffmpeg -> mono 24 kHz s16 WAV (`subprocess.run`, timeout 20 s, `ffmpeg_missing` if absent). Compute duration and RMS from the WAV with stdlib `wave` + `array` (no numpy). Reject <5 s `audio_too_short`, >20 s `audio_too_long`, RMS below ~-38 dBFS `audio_too_quiet`. Trim to first 15 s with ffmpeg `-t 15` for Sarvam. Delete old voice first. `create_voice(file=open(wav,'rb'), name="sily-"+token[:6], language=lang)`. Clean temp files in `finally`.
7. Speak: validate lang is one of the 12; cache hit returns instantly; otherwise `convert(...)` per contract (`output_audio_codec="wav"`, `speech_sample_rate=24000`, `pace`, `language_code`). Fill `romanized` via transliterate for supported langs (try/except -> null; also cached). Count cache misses only.
8. Attempt: ffmpeg -> 16 kHz mono WAV, `speech_to_text.transcribe(model="saaras:v4", mode="transcribe", language_code=target_lang)`, difflib per contract. Temp files in `finally`.
9. Translate: `sarvam-translate:v1`; romanize result when lang supports it.
10. Janitor daemon thread every 5 min: delete voices older than 2 h (call `delete_voice`, ignore errors), drop expired sessions + caches. Also `atexit` + SIGTERM handler: delete all live session voices.
11. GET `/` serves `frontend/index.html` via `send_from_directory` (path relative to server.py). If the file is missing return a short plain 404 message.
12. Never log key, audio bytes or request bodies. One readable file (~500 lines), short comments only where non-obvious.

## Done when
- [ ] `python -c "import ast;ast.parse(open('server.py').read())"` passes
- [ ] `python server.py` starts; `curl localhost:8000/api/health` and `/api/languages` return contract JSON
- [ ] `curl -X POST localhost:8000/api/speak` without token returns the contract error JSON (401 `no_session`)
- [ ] With a session token and no voice, `/api/speak` returns 409 `no_voice`

## Out of scope
- Frontend, tests, README, deploy. Do not edit other files. Spend few Sarvam credits: if you verify enroll/speak, do ONE enroll with a tiny `say`-generated clip and ONE short speak, then delete the voice.
