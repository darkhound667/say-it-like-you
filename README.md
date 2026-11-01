# Say it like you

Hear any sentence in **your own voice**, in 12 Indian languages. Record 10 seconds of English, we clone your voice (Sarvam AI), then type anything — English or native script — and hear it spoken back *as you*. Perfect for pronunciation practice in a voice that already sounds like home.

## Quickstart

```bash
pip install -r requirements.txt && cp .env.example .env   # add your SARVAM_API_KEY
python server.py    # open http://localhost:8000 — or double-click frontend/index.html (server running)
```

## Environment variables

| Var | Default | Meaning |
|-----|---------|---------|
| `SARVAM_API_KEY` | — | Sarvam AI subscription key (required). |
| `DAILY_CAP` | `150` | Global cap on voice syntheses per day, server-wide. |
| `PAUSE` | `0` | `1` = Sarvam-backed routes return `503 paused` (maintenance switch). |
| `PUBLIC_ORIGIN` | — | Extra CORS origin for your deployed site, e.g. `https://sayit.example.com`. |
| `SESSION_SPEAK_LIMIT` | `30` | Voice syntheses allowed per session per hour. |
| `IP_SPEAK_LIMIT` | `60` | Requests allowed per IP per hour (speak + translate + attempt). |
| `PORT` | `8000` | Port the Flask server listens on. |

## How it works

- **Your API key never touches the browser.** The frontend only ever holds an opaque session token.
- A session token maps to a server-side Sarvam `voice_id`; the raw id is never returned to any client.
- Limits: 30 synths/hour/session, 60 reqs/hour/IP, 150/day global — 429s carry `retry_after`, and identical speak requests are served from cache (free).
- A janitor deletes cloned voices 2 hours after enrollment; they're also deleted on re-enroll or when you hit "Delete my voice".

**ffmpeg is required** on the server: browser recordings (webm/mp4/wav) are converted to 24 kHz mono WAV before cloning. Install with `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Debian/Ubuntu).

## Deploy

**Cloudflare quick tunnel (fastest demo):**

```bash
cloudflared tunnel --url http://localhost:8000
```

Share the printed https URL — done. (CORS already allows `file://` / `null` origins, so the single-file frontend works anywhere.)

**Render / Railway:** set the start command to `python server.py`, add the env vars above (at minimum `SARVAM_API_KEY`), and set `PUBLIC_ORIGIN` to the deployed URL.

## Privacy

Your recording is used only to create your voice clone, is never logged, and is removed from the server as soon as enrollment completes. The clone lives on Sarvam's servers under our key, expires after 2 hours, and can be deleted anytime with one button. No cookies, no accounts, no tracking.

## 60-second demo script

1. **0–10 s** — Open the app: "It speaks in *your* voice." Tick the consent box.
2. **10–25 s** — Record ~10 s of English ("I love filter coffee and long walks on the beach").
3. **25–35 s** — While the cloning animation runs: "Ten seconds of audio — that's the whole enrollment."
4. **35–50 s** — Pick **Tamil**, type "Where is the station?", hit Speak → your voice says it in Tamil.
5. **50–60 s** — Switch to **Hindi** (or Bengali) for one more line, hit **Delete my voice**, and close: "Pronunciation practice — in your own voice."

## Smoke tests

```bash
python tests/smoke.py [--base http://localhost:8000] [--live]
```

Offline checks verify the error contract for free; `--live` enrolls a synthesized reference clip and spends a few Sarvam credits.

## Troubleshooting

- **Microphone doesn't work on `file://`** — some browsers block mic access for `file://` pages; open the app at `http://localhost:8000` instead.
- **`ffmpeg_missing` error on enroll** — ffmpeg isn't installed (or isn't on the server's PATH); install it and restart the server.
- **429 errors** — `rate_limited`: you hit the per-session/per-IP limit, wait `retry_after` seconds. `daily_cap`: the server's daily synthesis budget is used up.
