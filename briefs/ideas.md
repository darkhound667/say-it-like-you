# Brief ideas: creative upgrade ideas for "Say it like you"

## Goal
Write `IDEAS.md`: 5 ranked, concrete upgrade ideas that make this hackathon demo more creative and memorable. DO NOT implement anything.

## Context
Read `API_CONTRACT.md` and `server.py`. Product: visitor records ~10 s, Sarvam clones their voice, then it speaks any phrase in 12 Indian languages in THEIR voice. Routes already exist: session, voice enroll/delete, translate (+romanized), speak (pace), attempt (STT word-diff + score). Frontend is one HTML file. Constraints: ~15 minutes build time left in total, Sarvam clone endpoint 10 req/min, in-memory only, no DB/auth. Judges are at a Sarvam AI hackathon (IIT Bombay): favor ideas that showcase Sarvam's voice cloning across Indian languages.

## Files you may touch
- IDEAS.md (only)

## Requirements
For each idea: name, one-line pitch, the 10-second "wow" moment, effort (S/M/L), build time in minutes, which files change (server.py and/or frontend/index.html), and any new route with its JSON shape. Rank them; end with your single top pick and a 5-bullet implementation plan for it. Ideas should be inventive beyond the obvious (seeds: your voice in many languages at once; you vs corrected-you side by side with word highlighting; word-by-word slow shadowing; shareable clip link; streak/XP mechanic; a "tongue twister challenge" per language; "introduce yourself in 5 languages" reel; minimal-pair accent drills). Keep IDEAS.md under 80 lines.

## Done when
- [ ] IDEAS.md exists with 5 ranked ideas and a top pick

## Out of scope
- Any code changes.
