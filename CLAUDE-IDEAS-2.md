# Round-3 ideas from Claude subagents (UNVERIFIED)

Product: "Say it like you" (API_CONTRACT.md, server.py, frontend/index.html). Already built: clone, speak+pace, translate+romanized, attempt diff/score, word-by-word, Chorus, qc take, Grandma Mode, A/B reveal, Say my name, expiry countdown, Demo mode, Gentle Mirror.

## Judge-wow / polish (W)
- W1 Voice Morph Reveal: after clone, animated waveform morph from the stored enrollment blob's peaks (decodeAudioData) into the generated clip's peaks, play "before" then "after". Frontend only.
- W2 Native-Script Karaoke Ticker: `#ticker` under the player; word spans in native script + romanized, highlighted proportionally via `audio.ontimeupdate` (approximate, not true alignment).
- W3 Presenter Keys + Cheat-Sheet: keydown handler (1-4 language, Space speak, C chorus, G grandma, D demo mode, ? overlay with script and a 3-minute timer); ignore keys when typing.
- W4 Safety-Net Fallback: pre-recorded `fallback/*.wav` clips, a "Safety net" button (key F), auto-trigger on fetch failure or a request >6 s; reuse the mock branch. Needs clips recorded beforehand (demo-clips/ exists but may have no audio).
- W5 Demo Progress Timeline: sticky stepper Record, Clone, Speak, Score, Chorus, Reveal with ticks/confetti, aria-live.

## Emotional / accessibility (E)
- E1 Say It Slowly: large word chips, "my voice, slow" using pace + word-by-word, per-word replay, dyslexia-friendly font toggle, positive "closer" feedback only.
- E2 Roots Postcard: 5 emotional starter lines ("I'm sorry I never learned Telugu") in the heritage language + romanized + repeat-after-me ladder; elder-check note.
- E3 Voice Letter: type "I love you, thatha"; recipient chips (amma, thatha, ajji); translate + speak; preview then Save/download the WAV (decode base64 to a Blob, anchor download).
- E4 Ek Sher: festival greeting tiles (Diwali, Pongal, Eid, Onam) and proverbs from a prewritten list, spoken in your voice, one-tap language swap, copy text.
- E5 Tap & Listen: icon-first low-literacy flow with audio instructions; pregenerated instruction clips.

## Games (G)
- G1 Duel Pass: two people on one phone each clone a voice, a random phrase is spoken in both, each attempts live, word-diff winner banner (needs two sessions/voices: session limits and 8/min throttle).
- G2 Blind Lingo: your clone speaks a phrase in a secret language, pick the language from 4 chips, streak flame, prefetch next round.
- G3 Voice Passport: 12-language stamp grid, earn a stamp with attempt score >= 70 in a language, stamp animation, localStorage.
- G4 Daily Drop: date-seeded phrase + language, 3 tries, Wordle-style emoji result grid to copy, streak in localStorage.
- G5 Proverb Ladder: 8 proverbs rising in difficulty, 80% attempt score to climb, boss rungs at slower pace.
