# API_CONTRACT — "Say it like you"

Single source of truth for backend (`server.py`), frontend (`frontend/index.html`), tests. Code strictly to this.

## Confirmed Sarvam facts (tested live, SDK `sarvamai` 0.1.41)
- Client: `SarvamAI(api_subscription_key=KEY)`. Our key has voice cloning.
- **Clone**: `client.voice_cloning.create_voice(file=<file obj|bytes>, name=str, language="en-IN")` -> `resp.data.voice_id` (`svc-<uuid>`). ~2 s. Optional `style`, `gender` (skip). Ref audio: WAV best (mp3/flac/opus/aac ok), 10-15 s ideal, 16-24 kHz mono, <50 MB. Clean single speaker, no music.
- **Speak**: `client.voice_cloning.convert(voice_id=..., text=..., language_code="hi-IN", pace=1.0, output_audio_codec="wav", speech_sample_rate=24000)` -> `resp.audio_b64` (also `.audio`), `.request_id`, `.audio_duration`. ~3 s. `language_code` is required by the SDK. `text` <= 1000 chars (we cap at 200). `pace` supported 0.5-2.0 (never send with `max_audio_duration`). Cross-lingual verified (English reference -> Hindi output).
- **Delete**: `client.voice_cloning.delete_voice(voice_id)` -> None. **List**: `list_voices()` -> `resp.data.voices` (items: `.id .name .created_at`), `resp.data.total`. **Get**: `get_voice(voice_id)`.
- **Voice-clone languages = 12** (docs say 12, not 13; Urdu unsupported -> 400): `as-IN bn-IN en-IN gu-IN hi-IN kn-IN ml-IN mr-IN od-IN pa-IN ta-IN te-IN`. Used for the reference-clip language and for targets.
- **Sarvam limits**: `POST /voices/clone` is 10 req/min on Starter -> serialize synth globally (<= 8/min via a lock + sliding window; retry once on 429 after short backoff). 50-voice cap per org -> janitor + delete on re-enroll. Retry only 429/5xx. Auth failure = 403 on clone, 401 elsewhere.
- **Translate**: `client.text.translate(input=, source_language_code="en-IN", target_language_code="ta-IN", model="sarvam-translate:v1")` -> `.translated_text`. Source may be `"auto"`.
- **Transliterate** (romanize): `client.text.transliterate(input=native_text, source_language_code="ta-IN", target_language_code="en-IN")` -> `.transliterated_text`. Supported for `bn gu hi kn ml mr od pa ta te`; `as-IN` -> return `null`. Wrap in try/except -> `null` on any failure.
- **STT**: `client.speech_to_text.transcribe(file=<file obj>, model="saaras:v4", mode="transcribe", language_code="hi-IN")` -> `.transcript` (native script). Convert upload to 16 kHz mono WAV first. Sync limit ~30 s.
- **Audio conversion** (enroll): ffmpeg `-ac 1 -ar 24000 -sample_fmt s16 out.wav`. Browsers send webm/opus, mp4/aac or wav; ffmpeg handles all. Use `shutil.which("ffmpeg")`.

## Conventions
- Base URL: `""` when served by Flask; `http://localhost:8000` from `file://`.
- JSON in/out unless noted. Header `X-Session-Token: <token>` on every route except `/`, `/api/health`, `/api/languages`, `/api/session`.
- Errors (every one incl. 404/405/413/500/Sarvam failures; never a stack trace): `{"error":{"code":"<snake_case>","message":"<friendly text>"}}` + HTTP status. 429s add `error.retry_after` (seconds).
- Codes: `no_session` 401, `session_expired` 401, `consent_required` 400, `bad_request` 400, `audio_too_short` 400, `audio_too_long` 400, `audio_too_quiet` 400, `ffmpeg_missing` 500, `no_voice` 409, `text_too_long` 400, `unsupported_language` 400, `rate_limited` 429, `daily_cap` 429, `paused` 503, `sarvam_auth` 502, `sarvam_quota` 502, `sarvam_unavailable` 502, `payload_too_large` 413, `not_found` 404, `internal` 500.
- CORS: origins `null`, `http://localhost:8000`, `http://127.0.0.1:8000`, `PUBLIC_ORIGIN`; header `X-Session-Token`; no cookies.
- Never log the key, audio bytes or request bodies. Never return `voice_id` to the client.

## Routes

### GET `/`
Serves `frontend/index.html`.

### GET `/api/health`
200 `{"ok":true,"key_present":true,"version":"1.0.0","daily_remaining":150,"paused":false}`. No Sarvam call.

### GET `/api/languages`
200 `{"languages":[{"code":"hi-IN","native":"हिन्दी","english":"Hindi","romanize":true}, ...]}` (12 codes above; `romanize` = transliteration supported).
Native names: as অসমীয়া, bn বাংলা, en English, gu ગુજરાતી, hi हिन्दी, kn ಕನ್ನಡ, ml മലയാളം, mr मराठी, od ଓଡ଼ିଆ, pa ਪੰਜਾਬੀ, ta தமிழ், te తెలుగు.

### POST `/api/session`
No auth. 200 `{"token":"<urlsafe>","limits":{"speak_per_hour":30,"max_text_chars":200,"daily_cap":150,"enroll_min_seconds":5,"enroll_max_seconds":20},"expires_in":7200}`.

### POST `/api/voice/enroll`
`multipart/form-data`: `audio` (file), `language` (language the visitor spoke, e.g. `en-IN`), `consent` (must be `"true"`).
200 `{"voice_ready":true,"expires_at":1730000000}` (unix seconds).
Errors: `consent_required`, `audio_too_short` (<5 s), `audio_too_long` (>20 s), `audio_too_quiet` (RMS check; message says move closer / retry), `ffmpeg_missing`, `unsupported_language`, Sarvam errors. Replaces any existing voice (delete old first). Temp files removed in `finally`.

### GET `/api/voice`
200 `{"voice_ready":bool,"expires_at":int|null}`.

### DELETE `/api/voice`
200 `{"deleted":true}` (idempotent; also purges the session's audio cache).

### POST `/api/translate`
`{"text":"Where is the station?","source_lang":"en-IN","target_lang":"ta-IN"}`
200 `{"translated":"...","romanized":"..."|null}`. If `source_lang == target_lang` return text unchanged. `text` <= 200 chars. Counts toward IP limit, not the synth cap.

### POST `/api/speak`
`{"text":"வணக்கம்","target_lang":"ta-IN","pace":1.0}` (`pace` optional, clamp 0.5-1.5, default 1.0). Needs an enrolled voice (`no_voice` 409).
200 `{"audio_b64":"<base64 wav>","mime":"audio/wav","cached":false,"duration":2.4,"romanized":"vanakkam"|null}`.
Cache key = hash(token,text,lang,pace); cache hits don't count toward limits. Limits: 30 synth/hour/session, 60/hour/IP, `DAILY_CAP` global; 429 with `retry_after`.

### POST `/api/attempt`
`multipart`: `audio` (file), `target_text` (native script), `target_lang`.
200 `{"transcript":"...","words":[{"word":"नमस्ते","status":"match|miss|extra"}, ...],"score":0-100}`.
Normalize both sides (NFC, casefold, strip punctuation), split on whitespace, `difflib.SequenceMatcher` over word lists: matched target words -> `match`; unmatched target words -> `miss`; spoken words not in target -> `extra` (inserted at their position). `score = round(100*matched/len(target_words))`. No voice needed. Counts toward IP limit.

## Frontend flow
1. Load: `POST /api/session` (token in localStorage `sily_token`; reuse; on `session_expired`/`no_session` get a new one). `GET /api/languages`, `GET /api/voice`.
2. Consent + record (MediaRecorder, level meter, 10-15 s countdown) -> `POST /api/voice/enroll`.
3. Pick language; type English (-> `/api/translate`) or native text -> `POST /api/speak` -> play `data:` URL from `audio_b64`.
4. "Delete my voice" -> `DELETE /api/voice`.

## Additions (post-launch)

### POST `/api/speak` — optional `qc`
Body may include `"qc": true|false` (default false, must be boolean else `bad_request`). When true the server passes `enable_qc=True` to Sarvam (slower, quality-checked). `qc` is part of the cache key.

### POST `/api/extract`
`multipart/form-data`: `file` (`.txt`, `.md`, `.markdown`, `.docx`; max 1 MB). Header `X-Session-Token`.
200 `{"text":"...","chars":1234,"truncated":false,"name":"notes.docx"}` — plain text, whitespace-normalized, capped at 3000 chars (`truncated:true` if cut). No file is stored.
Errors: `unsupported_file` 400, `payload_too_large` 413, `bad_request` 400 (unreadable or empty file).
The frontend splits the text into <= 180-char chunks and reads at most 5 chunks per click via `/api/translate` (optional) + `/api/speak`, to respect the clone throttle.
