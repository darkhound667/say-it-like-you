#!/usr/bin/env python3
"""Smoke tests for the "Say it like you" API (stdlib only, no deps).

Offline checks exercise the error contract and read-only routes without
spending Sarvam credits. --live additionally enrolls a ~10 s reference clip
synthesized with macOS `say` + ffmpeg, then exercises translate/speak,
session isolation, rate limits and voice deletion — it spends a few credits.

Usage:
    python tests/smoke.py [--base http://localhost:8000] [--live]
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid

DEFAULT_BASE = "http://localhost:8000"
TIMEOUT = 30
SPEAK_TEXT = "नमस्ते, आज मैं बहुत अच्छा महसूस कर रहा हूँ।"
REFERENCE_TEXT = (
    "Hello, this is a reference recording of my voice. "
    "I am reading a few calm sentences so the clone can learn how I sound. "
    "Today the weather is lovely and I feel great."
)


class CheckFail(Exception):
    """Raised by expect() when a check does not hold."""


def expect(cond, msg):
    if not cond:
        raise CheckFail(msg)


class Runner:
    """Collects PASS/FAIL/SKIP lines and tracks failures."""

    def __init__(self):
        self.failures = 0

    def check(self, name, fn):
        try:
            note = fn()
        except CheckFail as err:
            self.failures += 1
            print(f"FAIL  {name} — {err}")
        except Exception as err:  # report and keep going
            self.failures += 1
            print(f"FAIL  {name} — unexpected {type(err).__name__}: {err}")
        else:
            print(f"PASS  {name}" + (f" — {note}" if note else ""))

    def skip(self, name, reason):
        print(f"SKIP  {name} — {reason}")


def http(base, method, path, token=None, json_body=None, data=None,
         content_type=None, extra_headers=None):
    """One HTTP round trip. Returns (status, {lowercase-header: value}, body bytes)."""
    url = base.rstrip("/") + path
    hdrs = dict(extra_headers or {})
    if token:
        hdrs["X-Session-Token"] = token
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        content_type = "application/json"
    if data is not None and content_type:
        hdrs["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status, raw, body = resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as err:
        status, raw, body = err.code, err.headers, err.read()
    except (urllib.error.URLError, OSError) as err:
        raise CheckFail(f"cannot reach {url}: {err}")
    flat = {k.lower(): v for k, v in raw.items()}
    return status, flat, body


def json_of(body):
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as err:
        raise CheckFail(f"body is not JSON: {err}; head={body[:120]!r}")


def multipart(fields=None, files=None):
    """Encode fields {name: str} + files {name: (filename, bytes, ctype)} as multipart/form-data."""
    boundary = "sily" + uuid.uuid4().hex
    out = bytearray()
    for name, value in (fields or {}).items():
        out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                f"{value}\r\n").encode("utf-8")
    for name, (filename, blob, ctype) in (files or {}).items():
        out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; "
                f"filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n").encode("utf-8")
        out += blob + b"\r\n"
    out += f"--{boundary}--\r\n".encode("utf-8")
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def expect_envelope(status, body, want_status, want_code):
    """Assert the standard error envelope {"error":{"code","message"}}."""
    expect(status == want_status,
           f"expected HTTP {want_status}, got {status} (body={body[:160]!r})")
    data = json_of(body)
    err = data.get("error") if isinstance(data, dict) else None
    expect(isinstance(err, dict), f"expected an error envelope, got {data!r}")
    expect(err.get("code") == want_code,
           f"expected code {want_code!r}, got {err.get('code')!r}")
    expect(isinstance(err.get("message"), str) and err["message"],
           "error.message missing or empty")


def new_session(base):
    st, _, body = http(base, "POST", "/api/session")
    expect(st == 200, f"POST /api/session -> {st}")
    data = json_of(body)
    expect(isinstance(data.get("token"), str) and data["token"],
           f"no token in session response: {data!r}")
    return data["token"]


def voice_status(base, token, want_ready):
    st, _, body = http(base, "GET", "/api/voice", token=token)
    expect(st == 200, f"expected HTTP 200, got {st}")
    data = json_of(body)
    expect(data.get("voice_ready") is want_ready,
           f"expected voice_ready {want_ready}, got {data.get('voice_ready')!r}")


# ---------------------------------------------------------------- offline

def offline_checks(runner, base):
    state = {}

    def health():
        st, _, body = http(base, "GET", "/api/health")
        expect(st == 200, f"expected HTTP 200, got {st}")
        data = json_of(body)
        expect(data.get("ok") is True, f"ok is {data.get('ok')!r}")
        for field in ("key_present", "version", "daily_remaining", "paused"):
            expect(field in data, f"missing field {field!r}")

    def languages():
        st, _, body = http(base, "GET", "/api/languages")
        expect(st == 200, f"expected HTTP 200, got {st}")
        data = json_of(body)
        langs = data.get("languages")
        expect(isinstance(langs, list) and len(langs) == 12,
               f"expected 12 languages, got "
               f"{len(langs) if isinstance(langs, list) else type(langs).__name__}")
        for lang in langs:
            for field in ("code", "native", "english", "romanize"):
                expect(field in lang, f"{lang.get('code')!r}: missing field {field!r}")

    def session():
        state["token"] = new_session(base)

    def unknown_route():
        st, _, body = http(base, "GET", "/api/does-not-exist")
        expect_envelope(st, body, 404, "not_found")

    def speak_no_token():
        st, _, body = http(base, "POST", "/api/speak",
                           json_body={"text": "hello", "target_lang": "hi-IN"})
        expect_envelope(st, body, 401, "no_session")

    def speak_bad_token():
        st, _, body = http(base, "POST", "/api/speak", token="smoke-invalid-token",
                           json_body={"text": "hello", "target_lang": "hi-IN"})
        expect_envelope(st, body, 401, "session_expired")

    def enroll_no_consent():
        expect(state.get("token"), "no session token — earlier session check failed")
        payload, ctype = multipart(
            fields={"language": "en-IN", "consent": "false"},
            files={"audio": ("clip.wav", b"\x00" * 64, "audio/wav")})
        st, _, body = http(base, "POST", "/api/voice/enroll", token=state["token"],
                           data=payload, content_type=ctype)
        expect_envelope(st, body, 400, "consent_required")

    def speak_no_voice():
        token = new_session(base)  # fresh session, never enrolled
        st, _, body = http(base, "POST", "/api/speak", token=token,
                           json_body={"text": "hello", "target_lang": "hi-IN"})
        expect_envelope(st, body, 409, "no_voice")

    def translate_too_long():
        expect(state.get("token"), "no session token — earlier session check failed")
        st, _, body = http(base, "POST", "/api/translate", token=state["token"],
                           json_body={"text": "x" * 201, "source_lang": "en-IN",
                                      "target_lang": "ta-IN"})
        expect_envelope(st, body, 400, "text_too_long")

    def unsupported_language():
        expect(state.get("token"), "no session token — earlier session check failed")
        st, _, body = http(base, "POST", "/api/translate", token=state["token"],
                           json_body={"text": "hello", "source_lang": "en-IN",
                                      "target_lang": "xx-XX"})
        expect_envelope(st, body, 400, "unsupported_language")

    def voice_not_ready():
        expect(state.get("token"), "no session token — earlier session check failed")
        voice_status(base, state["token"], False)

    def root_html():
        st, _, body = http(base, "GET", "/")
        expect(st == 200, f"expected HTTP 200, got {st}")
        html = body.decode("utf-8", "replace")
        expect("Say it like you" in html, "HTML does not contain 'Say it like you'")

    def cors_preflight():
        st, hdrs, _ = http(base, "OPTIONS", "/api/speak", extra_headers={
            "Origin": "null",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-session-token",
        })
        expect(st in (200, 204), f"preflight returned {st}")
        origin = hdrs.get("access-control-allow-origin")
        expect(bool(origin), "no Access-Control-Allow-Origin header")
        expect("null" in origin or "*" in origin,
               f"Origin: null not allowed (got {origin!r})")
        allowed = hdrs.get("access-control-allow-headers", "").lower()
        expect("x-session-token" in allowed,
               f"X-Session-Token not in Access-Control-Allow-Headers ({allowed!r})")

    runner.check("GET /api/health shape", health)
    runner.check("GET /api/languages -> 12 items with code/native/english/romanize", languages)
    runner.check("POST /api/session issues token", session)
    runner.check("unknown route -> 404 not_found", unknown_route)
    runner.check("POST /api/speak with no token -> 401 no_session", speak_no_token)
    runner.check("POST /api/speak with bad token -> 401 session_expired", speak_bad_token)
    runner.check("enroll without consent -> 400 consent_required", enroll_no_consent)
    runner.check("POST /api/speak with token but no voice -> 409 no_voice", speak_no_voice)
    runner.check("POST /api/translate text >200 chars -> 400 text_too_long", translate_too_long)
    runner.check("unsupported language -> 400 unsupported_language", unsupported_language)
    runner.check("GET /api/voice -> voice_ready false", voice_not_ready)
    runner.check("GET / returns HTML containing 'Say it like you'", root_html)
    runner.check("CORS preflight from Origin: null allows X-Session-Token", cors_preflight)


# ------------------------------------------------------------------- live

def make_reference_clip(workdir):
    """~10 s English reference clip via macOS `say` + ffmpeg (24 kHz mono WAV)."""
    aiff_path = os.path.join(workdir, "ref.aiff")
    wav_path = os.path.join(workdir, "ref.wav")
    subprocess.run(["say", "-o", aiff_path, REFERENCE_TEXT],
                   check=True, capture_output=True, timeout=120)
    subprocess.run(["ffmpeg", "-y", "-i", aiff_path, "-ac", "1", "-ar", "24000",
                    "-sample_fmt", "s16", wav_path],
                   check=True, capture_output=True, timeout=120)
    with open(wav_path, "rb") as fh:
        return fh.read()


def enroll_check(base, token, clip):
    payload, ctype = multipart(
        fields={"language": "en-IN", "consent": "true"},
        files={"audio": ("reference.wav", clip, "audio/wav")})
    st, _, body = http(base, "POST", "/api/voice/enroll", token=token,
                       data=payload, content_type=ctype)
    expect(st == 200, f"expected HTTP 200, got {st} (body={body[:200]!r})")
    data = json_of(body)
    expect(data.get("voice_ready") is True, f"voice_ready not true: {data!r}")


def translate_hello_check(base, token):
    st, _, body = http(base, "POST", "/api/translate", token=token,
                       json_body={"text": "Hello", "source_lang": "en-IN",
                                  "target_lang": "hi-IN"})
    expect(st == 200, f"expected HTTP 200, got {st} (body={body[:160]!r})")
    data = json_of(body)
    expect(bool(data.get("translated")), f"no translated text: {data!r}")
    return f"-> {data.get('translated')!r}"


def speak_check(base, token):
    st, _, body = http(base, "POST", "/api/speak", token=token,
                       json_body={"text": SPEAK_TEXT, "target_lang": "hi-IN"})
    expect(st == 200, f"expected HTTP 200, got {st} (body={body[:200]!r})")
    data = json_of(body)
    b64 = data.get("audio_b64")
    expect(isinstance(b64, str) and b64, "audio_b64 missing")
    audio = base64.b64decode(b64)
    expect(audio[:4] == b"RIFF" and audio[8:12] == b"WAVE",
           f"audio is not RIFF/WAV (head={audio[:12]!r})")
    return f"{len(audio)} bytes of wav"


def speak_cached_check(base, token):
    st, _, body = http(base, "POST", "/api/speak", token=token,
                       json_body={"text": SPEAK_TEXT, "target_lang": "hi-IN"})
    expect(st == 200, f"expected HTTP 200, got {st} (body={body[:160]!r})")
    data = json_of(body)
    expect(data.get("cached") is True,
           f"expected cached true, got {data.get('cached')!r}")


def isolation_check(base):
    token = new_session(base)  # a second session must not see the first voice
    st, _, body = http(base, "POST", "/api/speak", token=token,
                       json_body={"text": SPEAK_TEXT, "target_lang": "hi-IN"})
    expect_envelope(st, body, 409, "no_voice")
    voice_status(base, token, False)


def rate_limit_check(base, token):
    """Speak with distinct texts until a 429 appears (max 12 calls)."""
    for i in range(1, 13):
        st, _, body = http(base, "POST", "/api/speak", token=token,
                           json_body={"text": f"परीक्षण संख्या {i}", "target_lang": "hi-IN"})
        if st == 429:
            err = json_of(body).get("error", {})
            expect(isinstance(err, dict) and "retry_after" in err,
                   f"429 without retry_after: {err!r}")
            return f"429 after {i} calls (code={err.get('code')!r}, retry_after={err.get('retry_after')!r})"
        expect(st == 200, f"call {i}: expected 200 or 429, got {st} (body={body[:160]!r})")
    return "limit not reached within 12 calls"


def delete_voice_check(base, token):
    st, _, body = http(base, "DELETE", "/api/voice", token=token)
    expect(st == 200, f"DELETE /api/voice -> {st} (body={body[:160]!r})")
    data = json_of(body)
    expect(data.get("deleted") is True, f"expected deleted true, got {data!r}")
    voice_status(base, token, False)


def live_checks(runner, base):
    have_tools = bool(shutil.which("say") and shutil.which("ffmpeg"))
    state = {}

    def token():
        if "token" not in state:
            state["token"] = new_session(base)
        return state["token"]

    if not have_tools:
        runner.skip("live: enroll + speak chain",
                    "macOS `say` and/or `ffmpeg` not found (needed to synthesize a "
                    "reference clip); running the translate-only live check")

    with tempfile.TemporaryDirectory(prefix="sily-smoke-") as workdir:
        clip = None
        if have_tools:
            try:
                clip = make_reference_clip(workdir)
            except Exception as err:
                runner.skip("live: enroll + speak chain",
                            f"could not generate reference clip: {err}")
        try:
            if clip is not None:
                runner.check("live: enroll ~10 s `say` clip with consent",
                             lambda: enroll_check(base, token(), clip))
                runner.check("live: GET /api/voice -> voice_ready true",
                             lambda: voice_status(base, token(), True))
            runner.check("live: translate 'Hello' -> Hindi",
                         lambda: translate_hello_check(base, token()))
            if clip is not None:
                runner.check("live: speak short Hindi sentence returns RIFF/WAV",
                             lambda: speak_check(base, token()))
                runner.check("live: repeat speak -> cached true",
                             lambda: speak_cached_check(base, token()))
                runner.check("live: session isolation (second session -> no voice)",
                             lambda: isolation_check(base))
                runner.check("live: session rate limit",
                             lambda: rate_limit_check(base, token()))
        finally:
            # Always clean up the enrolled voice, even if a check above failed.
            if clip is not None:
                runner.check("live: delete voice -> voice_ready false",
                             lambda: delete_voice_check(base, token()))


# ------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(
        description="Smoke tests for the 'Say it like you' API.",
        epilog="Offline checks spend no Sarvam credits. --live enrolls a synthesized "
               "reference clip and spends a few credits (needs macOS `say` + ffmpeg).")
    parser.add_argument("--base", default=DEFAULT_BASE,
                        help=f"server base URL (default: {DEFAULT_BASE})")
    parser.add_argument("--live", action="store_true",
                        help="also run the Sarvam-backed live checks (spends credits)")
    args = parser.parse_args()

    runner = Runner()
    print(f"== offline checks against {args.base} ==")
    offline_checks(runner, args.base)
    if args.live:
        print("== live checks (spends Sarvam credits) ==")
        live_checks(runner, args.base)

    print(f"\n{runner.failures} failure(s)")
    return 1 if runner.failures else 0


if __name__ == "__main__":
    sys.exit(main())
