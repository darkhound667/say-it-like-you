# Brief ui2: the entire frontend as one HTML file (backup build, includes attempt mode)

## Goal
`frontend/index.html`: ONE self-contained file (inline CSS + JS, no build, no framework, no CDN; optional Google Font with system fallback) for "Say it like you" — a pronunciation coach that clones the visitor's voice, then speaks new phrases in Indian languages in THEIR voice. Mobile-first (most visitors are on phones). Must work opened from disk (`file://`) AND served by Flask at `/`. Read `API_CONTRACT.md` fully and code strictly to it. The backend may not exist yet: implement `?mock=1` (query param) that fakes every route locally (fake token, 1.5 s delays, `/api/speak` returns a generated 1-second sine-blip WAV base64, `/api/translate` returns "[ta] " + text) so the UI is fully demoable offline.

## Files you may touch
- frontend/index.html (only)

## Product identity (make it feel like a real product)
- Name: **Say it like you**. Tagline: "Hear yourself speak it right." Sub: "Record 10 seconds. We clone your voice. Then you hear *yourself* say anything, in any Indian language."
- Visual identity: warm and modern. Off-white/cream background, deep ink text, one saturated accent (saffron-coral) plus a secondary teal. Rounded 20px cards, big friendly type, generous spacing, soft shadows, a waveform motif. Light + dark via `prefers-color-scheme`.
- Delight: (1) while the voice is cloning (~3 s) show an animated waveform that morphs from a flat line into a lively wave plus rotating witty status lines ("Listening closely…", "Learning your vowels…", "Borrowing your voice (we'll give it back)…"). (2) First time a phrase plays in the visitor's voice: a playful reveal — card flips/pulses, confetti-lite burst (CSS/canvas, <1 s), text "That's you. In Tamil." with the language name filled in. (3) Subtle micro-interactions on buttons.
- The headline moment must work in 10 seconds: record English -> pick Tamil -> type or pick a sample phrase -> hear yourself.

## Requirements
1. At top of the script: `const API_BASE = location.protocol === "file:" ? "http://localhost:8000" : "";` Show it in a small footer ("Server: …", plus a green/red dot from `/api/health`) and a link to Delete my voice.
2. Steps (single page, progressive, one card active at a time with a stepper): 1) Consent checkbox ("I'm recording my own voice and agree to it being cloned temporarily. It's deleted after 2 hours or when I tap Delete.") 2) Record: `getUserMedia` + `MediaRecorder`, live level meter (AnalyserNode), visible countdown, auto-stop at 15 s, manual stop allowed after 8 s, re-record option, shows suggested script to read ("Read this aloud: …") in English. Upload the blob as-is (backend converts via ffmpeg; webm/mp4/wav all fine) with `language=en-IN` (add a small selector for "I'm recording in: English/Hindi/…" defaulting to en-IN). 3) Practice: language picker (chips, from `/api/languages`, native name + English), a textarea (placeholder: type English or the target language), button "Translate" (calls `/api/translate`, fills editable result and shows romanized line), preset phrase chips (Hello, how are you? / Where is the station? / Thank you very much / How much does this cost?), big "Speak it in my voice" button -> `/api/speak`, audio player with explicit Play/Replay button (autoplay is often blocked: never rely on autoplay; call `.play()` inside the click handler and fall back to showing a big play button), a pace toggle (Normal / Slow = 0.75), history list of last 5 clips with replay buttons, "Delete my voice" button (confirm, calls DELETE, returns to step 1).
4. Token: `localStorage.sily_token` (wrap in try/catch); get via `POST /api/session`; send `X-Session-Token` on every request; on 401 `session_expired|no_session` fetch a new session and retry once, and send user back to step 1 with a friendly message.
5. Mic failure (common on `file://`, or permission denied): friendly banner "Your browser blocks the mic on local files. Open http://localhost:8000 instead." with a button that opens that URL; also handle denied permission and no-mic cases with separate messages.
6. Backend unreachable: friendly "Backend not reachable" panel with the command `python server.py` in a copy button and a Retry button. NEVER show raw errors, stack traces or JSON. Every API error shows `error.message` from the contract in a toast; map network failures to friendly text.
7. If the browser's MediaRecorder mime isn't something ffmpeg can read (it can read all), just send it; no client WAV encode needed. Pick `audio/webm;codecs=opus`, else `audio/mp4`, else default.
8. Accessibility: buttons are real `<button>`s, focus rings, aria-live region for status, 44px+ touch targets, respects `prefers-reduced-motion`.
9. Keep JS organized in small functions and one `state` object so more features (attempt recording, multi-language reel) can be added later. Leave an empty `<section id="slot-attempt" hidden>` and `<section id="slot-reel" hidden>` placeholder below practice for later upgrades.

## Done when
- [ ] Open `frontend/index.html?mock=1` in a browser: full flow works end to end with fake backend; no console errors
- [ ] Layout is clean at 375px width and at desktop width (check with a headless/screenshot tool if available)
- [ ] No Sarvam key or `api.sarvam.ai` anywhere in the file (`grep -i sarvam frontend/index.html` shows only branding text, never URLs)

## Out of scope
- server.py, tests, README. Do not edit other files.

## ADDED (important, time is short: ~12 minutes total, ship a working file FAST, polish after)
10. Fill `#slot-attempt` (visible once a phrase has been spoken): "Your turn" card. Button "Record my attempt" (reuse mic code, 4 s max auto-stop, level meter) -> `POST /api/attempt` (multipart: audio, target_text = the native-script text last spoken, target_lang). Show the spoken text word by word with `match` words green, `miss` red, `extra` listed as grey chips, a big score ring (0-100) that animates, and a side-by-side "You, but correct" Play button vs "Your attempt" Play button (play the recorded blob). Mock mode returns a fake result.
11. Slow word-by-word playback: a "Word by word" toggle that splits the target text on spaces, calls `/api/speak` per word with pace 0.75 (sequentially, max 6 words, reuse cache), highlights each word as it plays.
12. Priority order if time runs short: steps 1-3 core flow first, commit-ready file early; attempt mode second; word-by-word last.
