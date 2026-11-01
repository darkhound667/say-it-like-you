"""Flask backend for Say it like you; Sarvam credentials stay on the server."""
import atexit
from array import array
from collections import deque
from datetime import date, datetime, time as day_time, timedelta
import difflib
from functools import wraps
import hashlib
import io
import math
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import re
import time
import unicodedata
import wave
import xml.etree.ElementTree as ET
import zipfile

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from sarvamai import SarvamAI
from sarvamai.core.api_error import ApiError
from werkzeug.exceptions import HTTPException

load_dotenv()
KEY = os.getenv("SARVAM_API_KEY", "").strip()
if not KEY:
    try:
        for line in (Path.home() / ".sarvam/credentials").read_text().splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "api_key":
                KEY = value.strip().strip("\"'")
                break
    except OSError:
        pass
if not KEY:
    print("Missing SARVAM_API_KEY. Set it in the environment or .env.", file=sys.stderr)
    sys.exit(1)

DAILY_CAP = int(os.getenv("DAILY_CAP", "150"))
SESSION_LIMIT = int(os.getenv("SESSION_SPEAK_LIMIT", "30"))
IP_LIMIT = int(os.getenv("IP_SPEAK_LIMIT", "60"))
PAUSED = os.getenv("PAUSE") == "1"
TTL = 7200
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
origins = ["null", "http://localhost:8000", "http://127.0.0.1:8000"]
if os.getenv("PUBLIC_ORIGIN"):
    origins.append(os.environ["PUBLIC_ORIGIN"])
CORS(app, origins=origins, allow_headers=["Content-Type", "X-Session-Token"],
     supports_credentials=False)
client = SarvamAI(api_subscription_key=KEY)
LANGUAGES = [
    ("as-IN", "অসমীয়া", "Assamese", False),
    ("bn-IN", "বাংলা", "Bengali", True),
    ("en-IN", "English", "English", False),
    ("gu-IN", "ગુજરાતી", "Gujarati", True),
    ("hi-IN", "हिन्दी", "Hindi", True),
    ("kn-IN", "ಕನ್ನಡ", "Kannada", True),
    ("ml-IN", "മലയാളം", "Malayalam", True),
    ("mr-IN", "मराठी", "Marathi", True),
    ("od-IN", "ଓଡ଼ିଆ", "Odia", True),
    ("pa-IN", "ਪੰਜਾਬੀ", "Punjabi", True),
    ("ta-IN", "தமிழ்", "Tamil", True),
    ("te-IN", "తెలుగు", "Telugu", True),
]
LANG_CODES = {row[0] for row in LANGUAGES}
ROMAN_CODES = {row[0] for row in LANGUAGES if row[3]}
# Mapping/global counters use state_lock; each session's fields use its own lock.
state_lock = threading.RLock()
sessions = {}
ip_windows = {}
synth_window = deque()
daily_date = date.today()
daily_count = 0
stopping = threading.Event()


class Problem(Exception):
    def __init__(self, code, message, status=400, retry_after=None):
        self.code, self.message, self.status = code, message, status
        self.retry_after = retry_after


@app.errorhandler(Problem)
def problem_response(exc):
    error = {"code": exc.code, "message": exc.message}
    if exc.status == 429:
        error["retry_after"] = max(1, math.ceil(exc.retry_after or 1))
    return jsonify(error=error), exc.status


def log_error(exc, message):
    # SDK exceptions may contain bodies, credentials, or audio: never stringify them.
    app.logger.warning("%s: %s", type(exc).__name__, message)


@app.errorhandler(ApiError)
def sarvam_error(exc):
    status = exc.status_code
    log_error(exc, "Sarvam request failed (HTTP %s)" % status)
    if status in (401, 403):
        code, message = "sarvam_auth", "Voice service authentication failed. Please contact the host."
    elif status == 402 or "quota" in str(exc.body).lower():
        code, message = "sarvam_quota", "The voice service quota is exhausted. Please contact the host."
    else:
        code, message = "sarvam_unavailable", "The voice service is temporarily unavailable. Please retry shortly."
    return problem_response(Problem(code, message, 502))


@app.errorhandler(HTTPException)
def http_error(exc):
    code = {404: "not_found", 413: "payload_too_large", 500: "internal"}.get(exc.code, "bad_request")
    message = {404: "Route not found.", 405: "Method not allowed.",
               413: "Upload must be smaller than 5 MB."}.get(exc.code, "Invalid request.")
    return problem_response(Problem(code, message, exc.code or 500))


@app.errorhandler(Exception)
def unexpected_error(exc):
    log_error(exc, "Request failed")
    return problem_response(Problem("internal", "Something went wrong. Please retry.", 500))


@app.before_request
def pause_guard():
    if PAUSED and (request.path == "/api" or request.path.startswith("/api/")) and request.path != "/api/health":
        raise Problem("paused", "Demo is paused", 503)


def sarvam_call(method, *args, synth=False, **kwargs):
    # Disable SDK retries so every synth attempt passes through our throttle.
    kwargs["request_options"] = {"max_retries": 0}
    audio = kwargs.get("file")
    position = audio.tell() if hasattr(audio, "tell") else None
    for attempt in range(2):
        try:
            return method(*args, **kwargs)
        except ApiError as exc:
            if exc.status_code != 429 or attempt:
                raise
            time.sleep(2)
            if position is not None:
                audio.seek(position)
            if synth:
                synth_slot()


def delete_voice(session, ignore_errors=False):
    voice = session["voice_id"]
    if voice:
        try:
            sarvam_call(client.voice_cloning.delete_voice, voice)
        except Exception as exc:
            if not ignore_errors:
                raise
            log_error(exc, "Voice cleanup failed")
            return
    session.update(voice_id=None, voice_created_at=None, cache={})


def authenticated(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        token = request.headers.get("X-Session-Token", "")
        with state_lock:
            session = sessions.get(token)
        if session is None:
            if token:
                raise Problem("session_expired", "Your session expired. Start a new session.", 401)
            raise Problem("no_session", "Start a new session first.", 401)
        with session["lock"]:
            with state_lock:
                present = sessions.get(token) is session
            if not present or time.time() - session["last_used"] >= TTL:
                delete_voice(session, ignore_errors=True)
                with state_lock:
                    sessions.pop(token, None)
                raise Problem("session_expired", "Your session expired. Start a new session.", 401)
            session["last_used"] = time.time()
            if session["voice_id"] and time.time() - session["voice_created_at"] >= TTL:
                delete_voice(session)
            g.session, g.token = session, token
            return handler(*args, **kwargs)
    return wrapped


def language(value, allow_auto=False):
    if not isinstance(value, str) or (value not in LANG_CODES and not (allow_auto and value == "auto")):
        raise Problem("unsupported_language", "Choose one of the supported languages.")
    return value


def text_value(value):
    if not isinstance(value, str) or not value.strip():
        raise Problem("bad_request", "Provide non-empty text.")
    if len(value) > 200:
        raise Problem("text_too_long", "Use at most 200 characters.")
    return value


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise Problem("bad_request", "Provide a JSON object.")
    return body


def trim_window(window, now, seconds=3600):
    while window and window[0] <= now - seconds:
        window.popleft()


def reset_day():
    global daily_date, daily_count
    if daily_date != date.today():
        daily_date, daily_count = date.today(), 0


def charge(synth=False):
    global daily_count
    now = time.time()
    ip = (request.headers.get("CF-Connecting-IP") or
          request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr)
    with state_lock:
        reset_day()
        windows = [(ip_windows.setdefault(ip, deque()), IP_LIMIT)]
        if synth:
            windows.append((g.session["counters"], SESSION_LIMIT))
        for window, limit in windows:
            trim_window(window, now)
            if len(window) >= limit:
                retry = window[0] + 3600 - now if window else 3600
                raise Problem("rate_limited", "Too many requests. Please try again later.", 429, retry)
        if synth and daily_count >= DAILY_CAP:
            midnight = datetime.combine(date.today() + timedelta(days=1), day_time.min)
            raise Problem("daily_cap", "Today's demo limit has been reached.", 429, midnight.timestamp() - now)
        for window, _ in windows:
            window.append(now)
        if synth:
            daily_count += 1


def synth_slot():
    deadline = time.monotonic() + 6
    while True:
        with state_lock:
            now = time.monotonic()
            trim_window(synth_window, now, 60)
            if len(synth_window) < 8:
                synth_window.append(now)
                return
            wait = max(0.01, synth_window[0] + 60 - now)
        remaining = deadline - time.monotonic()
        if wait > remaining:
            raise Problem("rate_limited", "The voice service is busy. Please retry shortly.", 429, wait)
        time.sleep(min(wait, remaining))


def romanize(text, lang):
    if lang not in ROMAN_CODES:
        return None
    try:
        return sarvam_call(client.text.transliterate, input=text,
                           source_language_code=lang, target_language_code="en-IN").transliterated_text
    except Exception as exc:
        log_error(exc, "Romanization unavailable")
        return None


def convert_upload(directory, rate):
    upload = request.files.get("audio")
    if upload is None:
        raise Problem("bad_request", "Provide an audio recording.")
    source, output = Path(directory) / "upload", Path(directory) / "converted.wav"
    upload.save(source)
    ffmpeg(source, output, rate)
    return output


def ffmpeg(source, output, rate, trim=False):
    executable = shutil.which("ffmpeg")
    if not executable:
        raise Problem("ffmpeg_missing", "Audio conversion is unavailable: ffmpeg is not installed.", 500)
    command = [executable, "-nostdin", "-v", "error", "-y", "-i", str(source)]
    if trim:
        # Clone reference: drop low rumble, strip leading/trailing silence and room-noise tails,
        # level the voice, then keep at most 15 s of actual speech.
        trim_silence = "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB"
        command += ["-af", f"highpass=f=70,{trim_silence},areverse,{trim_silence},areverse,"
                           "loudnorm=I=-18:TP=-2:LRA=11", "-t", "15"]
    command += ["-vn", "-ac", "1", "-ar", str(rate), "-sample_fmt", "s16", "-c:a", "pcm_s16le", str(output)]
    try:
        subprocess.run(command, capture_output=True, check=True, timeout=20)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise Problem("bad_request", "Could not read the recording. Please record again.") from None


@app.get("/")
def index():
    directory = Path(__file__).resolve().parent / "frontend"
    if not (directory / "index.html").is_file():
        return "Frontend is not available yet.\n", 404, {"Content-Type": "text/plain; charset=utf-8"}
    return send_from_directory(directory, "index.html")


@app.get("/api/health")
def health():
    with state_lock:
        reset_day()
        remaining = max(0, DAILY_CAP - daily_count)
    return jsonify(ok=True, key_present=True, version="1.0.0", daily_remaining=remaining, paused=PAUSED)


@app.get("/api/languages")
def languages():
    return jsonify(languages=[dict(zip(("code", "native", "english", "romanize"), row)) for row in LANGUAGES])


@app.post("/api/session")
def new_session():
    now, token = time.time(), secrets.token_urlsafe(24)
    with state_lock:
        sessions[token] = dict(voice_id=None, voice_created_at=None, created_at=now,
                               last_used=now, counters=deque(), cache={}, lock=threading.RLock())
    return jsonify(token=token, limits=dict(speak_per_hour=SESSION_LIMIT, max_text_chars=200,
                   daily_cap=DAILY_CAP, enroll_min_seconds=5, enroll_max_seconds=20), expires_in=TTL)


@app.post("/api/voice/enroll")
@authenticated
def enroll():
    if request.form.get("consent") != "true":
        raise Problem("consent_required", "Consent is required to clone your voice.")
    lang = language(request.form.get("language"))
    with tempfile.TemporaryDirectory(prefix="sily-") as directory:
        wav = convert_upload(directory, 24000)
        with wave.open(str(wav), "rb") as recording:
            duration = recording.getnframes() / recording.getframerate()
            if duration < 5:
                raise Problem("audio_too_short", "Record at least 5 seconds of speech.")
            if duration > 20:
                raise Problem("audio_too_long", "Keep your recording under 20 seconds.")
            samples = array("h", recording.readframes(recording.getnframes()))
        if sys.byteorder != "little":
            samples.byteswap()
        rms = math.sqrt(sum(sample * sample for sample in samples) / max(1, len(samples))) / 32768
        if rms < 10 ** (-38 / 20):
            raise Problem("audio_too_quiet", "Move closer to the microphone and retry.")
        trimmed = Path(directory) / "reference.wav"
        ffmpeg(wav, trimmed, 24000, trim=True)
        delete_voice(g.session)
        with trimmed.open("rb") as audio:
            response = sarvam_call(client.voice_cloning.create_voice, file=audio,
                                   name="sily-" + g.token[:6], language=lang)
        g.session.update(voice_id=response.data.voice_id, voice_created_at=time.time())
    return jsonify(voice_ready=True, expires_at=int(g.session["voice_created_at"] + TTL))


@app.route("/api/voice", methods=["GET", "DELETE"])
@authenticated
def voice():
    if request.method == "DELETE":
        delete_voice(g.session)
        return jsonify(deleted=True)
    ready = bool(g.session["voice_id"])
    return jsonify(voice_ready=ready, expires_at=int(g.session["voice_created_at"] + TTL) if ready else None)


@app.post("/api/translate")
@authenticated
def translate():
    body = json_body()
    text = text_value(body.get("text"))
    source = language(body.get("source_lang"), allow_auto=True)
    target = language(body.get("target_lang"))
    charge()
    translated = text if source == target else sarvam_call(
        client.text.translate, input=text, source_language_code=source,
        target_language_code=target, model="sarvam-translate:v1").translated_text
    return jsonify(translated=translated, romanized=romanize(translated, target))


EXTRACT_MAX_CHARS = 3000
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def strip_markdown(text):
    text = re.sub(r"^\s*```.*$", "", text, flags=re.M)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*>+\s?", "", text, flags=re.M)
    text = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", text, flags=re.M)
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"\1", text)
    return re.sub(r"`([^`]*)`", r"\1", text)


def docx_text(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            with archive.open("word/document.xml") as member:
                xml = member.read(5_000_001)
        if len(xml) > 5_000_000:
            raise ValueError("too large")
        if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
            raise ValueError("unsafe xml")
        root = ET.fromstring(xml)
    except (zipfile.BadZipFile, KeyError, ValueError, ET.ParseError, RuntimeError, OSError):
        raise Problem("bad_request", "Could not read that Word file.")
    paragraphs = ("".join(node.text or "" for node in para.iter(WORD_NS + "t"))
                  for para in root.iter(WORD_NS + "p"))
    return "\n".join(paragraphs)


@app.post("/api/extract")
@authenticated
def extract():
    upload = request.files.get("file")
    filename = upload.filename if upload and upload.filename else ""
    extension = os.path.splitext(filename)[1].lower()
    if extension not in (".txt", ".md", ".markdown", ".docx"):
        raise Problem("unsupported_file", "Upload a .txt, .md or .docx file.", 400)
    data = upload.read(1_000_001)
    if len(data) > 1_000_000:
        raise Problem("payload_too_large", "That file is too large. Keep it under 1 MB.", 413)
    if extension == ".docx":
        text = docx_text(data)
    else:
        text = data.decode("utf-8", errors="replace")
        if extension != ".txt":
            text = strip_markdown(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = (re.sub(r"[ \t\f\v\u00a0]+", " ", line).strip() for line in text.split("\n"))
    text = "\n".join(line for line in lines if line).strip()
    if not text:
        raise Problem("bad_request", "No readable text found in that file.")
    truncated = len(text) > EXTRACT_MAX_CHARS
    if truncated:
        text = text[:EXTRACT_MAX_CHARS].rstrip()
    base = re.sub(r"[\x00-\x1f\x7f]", "", filename.replace("\\", "/").rsplit("/", 1)[-1]).strip()[:80]
    return jsonify(text=text, chars=len(text), truncated=truncated, name=base)


@app.post("/api/speak")
@authenticated
def speak():
    if not g.session["voice_id"]:
        raise Problem("no_voice", "Record your voice first.", 409)
    body = json_body()
    text, lang = text_value(body.get("text")), language(body.get("target_lang"))
    pace = body.get("pace", 1.0)
    if isinstance(pace, bool) or not isinstance(pace, (int, float)) or not math.isfinite(pace):
        raise Problem("bad_request", "Pace must be a finite number.")
    pace = max(0.5, min(1.5, float(pace)))
    qc = body.get("qc", False)
    if not isinstance(qc, bool):
        raise Problem("bad_request", "qc must be true or false.")
    cache_key = hashlib.sha256(repr((g.token, text, lang, pace, qc)).encode()).hexdigest()
    if cache_key in g.session["cache"]:
        return jsonify(**g.session["cache"][cache_key], cached=True)
    synth_slot()
    charge(synth=True)
    response = sarvam_call(client.voice_cloning.convert, synth=True, voice_id=g.session["voice_id"],
                          text=text, language_code=lang, pace=pace, enable_qc=qc,
                          output_audio_codec="wav", speech_sample_rate=24000)
    result = dict(audio_b64=response.audio_b64, mime="audio/wav", duration=response.audio_duration,
                  romanized=romanize(text, lang))
    g.session["cache"][cache_key] = result
    return jsonify(**result, cached=False)


def normalized_words(text):
    text = unicodedata.normalize("NFC", text).casefold()
    return "".join(c for c in text if not unicodedata.category(c).startswith("P")).split()


@app.post("/api/attempt")
@authenticated
def attempt():
    target = normalized_words(text_value(request.form.get("target_text")))
    lang = language(request.form.get("target_lang"))
    if not target:
        raise Problem("bad_request", "Provide target words to compare.")
    charge()
    with tempfile.TemporaryDirectory(prefix="sily-") as directory:
        wav = convert_upload(directory, 16000)
        with wav.open("rb") as audio:
            transcript = sarvam_call(client.speech_to_text.transcribe, file=audio,
                                     model="saaras:v4", mode="transcribe", language_code=lang).transcript
    spoken = normalized_words(transcript)
    words, matched = [], 0
    for tag, i, j, k, end in difflib.SequenceMatcher(None, target, spoken, autojunk=False).get_opcodes():
        if tag == "equal":
            matched += j - i
        words.extend({"word": word, "status": "match" if tag == "equal" else "miss"} for word in target[i:j])
        if tag in ("insert", "replace"):
            words.extend({"word": word, "status": "extra"} for word in spoken[k:end])
    return jsonify(transcript=transcript, words=words, score=round(100 * matched / len(target)))


def sweep(all_sessions=False):
    with state_lock:
        candidates = list(sessions.items())
    for token, session in candidates:
        if not session["lock"].acquire(blocking=all_sessions):
            continue
        try:
            expired = time.time() - session["last_used"] >= TTL
            if all_sessions or expired or (session["voice_id"] and time.time() - session["voice_created_at"] >= TTL):
                delete_voice(session, ignore_errors=True)
            if all_sessions or expired:
                with state_lock:
                    sessions.pop(token, None)
        finally:
            session["lock"].release()
    with state_lock:
        for ip in list(ip_windows):
            trim_window(ip_windows[ip], time.time())
            if not ip_windows[ip]:
                del ip_windows[ip]


def janitor():
    while not stopping.wait(300):
        sweep()


def shutdown():
    stopping.set()
    sweep(all_sessions=True)


def terminate(signum, frame):
    shutdown()
    raise SystemExit(0)


atexit.register(shutdown)
if threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGTERM, terminate)
threading.Thread(target=janitor, name="voice-janitor", daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), threaded=True)
