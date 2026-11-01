# Ideas proposed by Claude subagents (UNVERIFIED — to be checked)

Product: "Say it like you" (see API_CONTRACT.md, server.py, frontend/index.html).

## Learners (L)
- L1 Grandma Mode: diaspora kid picks "Talk to Ajji/Paati/Nani", types a sentence, hears it in their voice in the grandparent's language with romanized text. Reuses translate/speak.
- L2 Gentle Mirror: after an attempt, replay only the missed words slowly (pace 0.7) in the user's voice, framed positively ("3 of 5 words already yours"). Cap 3 words (quota).
- L3 Say It Slow Then Fast: phrase at pace 0.6, 1.0, 1.4 with words highlighted in sync (even split over `duration`).
- L4 Cross-Script Rescue: show the Tamil phrase in Devanagari for Hindi speakers via transliterate ta-IN -> hi-IN (claimed small server change).
- L5 Streak Keepsake: daily best attempt scores in localStorage, "me 7 days ago vs now".
- L6 Voice Postcard: shareable page / QR playing the user's voice in 3 languages (privacy risk).

## Demo moments (D)
- D1 "Hand the mic to a judge" bigger UI skin. D2 "Play it in all 12" queue (only ~3 live). D3 Before/after A/B toggle: original recording vs generated speech. D4 Waveform comparison of original vs generated. D5 Live "Voice deletes in 1:59:42" header countdown. D6 "Say your name" preset phrase.

## Tech (T) — claims from docs, partially unverified
- T1 Streaming playback via `voice_cloning.convert_stream(...)` (mp3/wav/linear16/mulaw/alaw; max 1000 chars), Flask `Response(stream_with_context)`.
- T2 `convert(..., enable_qc=True)` for a "final take" button (adds ~0.5 s, single-chunk text only).
- T3 `client.chat.completions(model="sarvam-105b", reasoning_effort="low")` for coaching feedback in the learner's language and themed phrase packs.
- T4 `client.text.identify_language(input=...)` language-ID guard (11 languages).
- T5 Code-mixed output via `text.translate(model="mayura:v1", mode="code-mixed", speaker_gender=...)`.
- T6 STT `with_timestamps=True` karaoke highlighting (claimed chunk-level only for saaras:v4).
- Claimed NOT usable: pronunciation dictionary on voice cloning; `ref_text` with saved voice_id; `enable_vad` on clone endpoints.
- Claimed correction: clone rate limit is 60 req/min (PAYG), not 10/min; clone costs Rs 2 per 1,000 chars.

## Trust (S)
- S1 Spoken-consent enrollment: user reads a random phrase with digits; server transcribes via STT and rejects on mismatch; that clip is the clone reference. New `GET /api/voice/challenge`, error `challenge_failed`.
- S2 Privacy UX: live countdown, one-tap wipe, "nothing stored" panel (frontend only, uses `expires_at`).
- S3 Spoken "AI voice" tag + HMAC provenance + `/api/verify` + "AI-generated" badge.
- S4 Consent-gated 24 h share link `POST /api/share`, `GET /s/<id>`.
- S5 "I speak Tamil now" 1080x1080 canvas PNG share card (no audio).
- S6 India-friendly/abuse hardening: opus/webm 16 kHz uploads, per-IP enroll limit 3/day, 2 clones/session, honeypot.
