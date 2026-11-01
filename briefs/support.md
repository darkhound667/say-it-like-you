# Brief support: tests, README, env files

## Goal
Supporting files for "Say it like you" (Flask + single-file frontend). Read `API_CONTRACT.md` fully first.

## Files you may touch
- tests/smoke.py
- README.md
- .env.example
- requirements.txt

## Requirements
1. `requirements.txt`: `flask>=3.0`, `flask-cors>=4.0`, `python-dotenv>=1.0`, `sarvamai>=0.1.37` (nothing else; stdlib `urllib`/`http.client` for tests — no `requests` dependency).
2. `.env.example`: `SARVAM_API_KEY=`, `DAILY_CAP=150`, `PAUSE=0`, `PUBLIC_ORIGIN=`, `SESSION_SPEAK_LIMIT=30`, `IP_SPEAK_LIMIT=60`, `PORT=8000`, each with a one-line comment.
3. `tests/smoke.py` — `python tests/smoke.py [--base http://localhost:8000] [--live]`. Stdlib only. Prints PASS/FAIL per check, exits non-zero on failure. Default (offline, no Sarvam credits): health shape; languages (12 items, fields code/native/english/romanize); session issues token; error shape `{"error":{"code","message"}}` for: unknown route (404 `not_found`), `/api/speak` with no token (401 `no_session`), bad token (401 `session_expired`), enroll without consent (400 `consent_required`), `/api/speak` with token but no voice (409 `no_voice`), `/api/translate` with text >200 chars (400 `text_too_long`), unsupported language; `GET /api/voice` -> `voice_ready:false`; `GET /` returns HTML containing "Say it like you"; CORS preflight from `Origin: null` allows `X-Session-Token`. `--live` (spends a few Sarvam credits, keep tiny): generate a ~10 s speech clip with macOS `say` + `ffmpeg` (skip with a message if unavailable), enroll with consent, check `voice_ready`, translate "Hello" to Hindi, speak one short Hindi sentence (check base64 decodes to RIFF/WAV), speak again to check `cached:true`, **session isolation**: a second session's `/api/speak` -> 409 `no_voice` and its `/api/voice` -> false, **rate limits**: fire speak calls with distinct short texts until a 429 with `retry_after` appears OR report "limit not reached within 12 calls" (do not exceed 12), then delete voice and confirm `voice_ready:false`. Always delete the voice in a `finally`.
4. `README.md`: what it is; 2-line quickstart (`pip install -r requirements.txt`, cp `.env.example .env`, `python server.py`, open http://localhost:8000 — or double-click `frontend/index.html` with the server running); env vars table; architecture (key never in browser, session token -> server-side voice_id, limits, janitor deletes voices after 2 h); ffmpeg requirement; deploy section (Cloudflare quick tunnel `cloudflared tunnel --url http://localhost:8000`, or Render/Railway with start command `python server.py` and env vars); privacy note; **"60-second demo script"** (numbered, timed: 0-10 s hook & consent, 10-25 s record 10 s of English, 25-35 s cloning animation & explain, 35-50 s pick Tamil, speak "Where is the station?" -> reveal, 50-60 s switch to Hindi/Bengali + Delete my voice + close line about pronunciation practice in your own voice); troubleshooting (mic on file://, ffmpeg missing, 429s). Keep it tight and friendly.

## Done when
- [ ] `python -c "import ast;ast.parse(open('tests/smoke.py').read())"` passes
- [ ] `python tests/smoke.py --help` prints usage
- [ ] README renders as valid Markdown with the demo script section present

## Out of scope
- server.py and frontend. Do not run the live tests yourself; the manager will.
