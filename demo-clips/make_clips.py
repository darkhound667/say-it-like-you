#!/usr/bin/env python3
"""Generate fallback demo clips via the running backend (6 speak calls total)."""
import base64
import json
import os
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://localhost:8000"
HERE = os.path.dirname(os.path.abspath(__file__))
PHRASES = ["Hello, I'm so happy to meet you.", "Where is the railway station?"]
LANGS = ["hi-IN", "ta-IN", "bn-IN"]


def call(method, path, token=None, body=None, headers=None):
    h = dict(headers or {})
    if token:
        h["X-Session-Token"] = token
    data = None
    if isinstance(body, dict):
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    elif body is not None:
        data = body
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"_http": e.code, **json.loads(e.read() or b"{}")}


def multipart(fields, fname, fbytes):
    b = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(
        (f'--{b}\r\nContent-Disposition: form-data; name="audio"; filename="{fname}"\r\n'
         f'Content-Type: audio/wav\r\n\r\n').encode() + fbytes + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    return b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={b}"}


def speak_once(token, text, lang):
    for attempt in range(2):
        r = call("POST", "/api/speak", token, {"text": text, "target_lang": lang})
        if "audio_b64" in r:
            return r
        print("speak error:", r)
        if attempt == 0:
            time.sleep(10)
    return None


def main():
    token = call("POST", "/api/session")["token"]
    manifest, errors = {}, []
    try:
        ref = open(os.path.join(HERE, "ref.wav"), "rb").read()
        body, hdr = multipart({"language": "en-IN", "consent": "true"}, "ref.wav", ref)
        r = call("POST", "/api/voice/enroll", token, body, hdr)
        print("enroll:", r)
        if not r.get("voice_ready"):
            raise SystemExit("enroll failed")
        first = True
        for lang in LANGS:
            for n, phrase in enumerate(PHRASES, 1):
                t = call("POST", "/api/translate", token,
                         {"text": phrase, "source_lang": "en-IN", "target_lang": lang})
                if "translated" not in t:
                    errors.append((lang, n, "translate", t))
                    continue
                if not first:
                    time.sleep(8)
                first = False
                s = speak_once(token, t["translated"], lang)
                if not s:
                    errors.append((lang, n, "speak"))
                    continue
                fn = f"{lang.split('-')[0]}_{n}.wav"
                with open(os.path.join(HERE, fn), "wb") as f:
                    f.write(base64.b64decode(s["audio_b64"]))
                manifest[fn] = {"language": lang, "english": phrase,
                                "translated": t["translated"],
                                "romanized": s.get("romanized") or t.get("romanized")}
                print("wrote", fn)
    finally:
        print("delete voice:", call("DELETE", "/api/voice", token))
        with open(os.path.join(HERE, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        if errors:
            print("errors:", errors)


if __name__ == "__main__":
    main()
