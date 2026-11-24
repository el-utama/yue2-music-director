"""Native Studio recognition capture and unverified ASR disagreement review."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .mcp import Client, configured_endpoint, unpack
from .lyric_fidelity import compare_lyrics, _tokens
from .prosody import parse_lyrics

BUSY_KEYS = ("song_jobs", "covers_and_karaoke", "stems", "midi", "restore",
             "preparation", "training", "processing")


def _busy_keys(status, pending_processing=None):
    """Exempt only a successful terminal stem or an explicitly matched finished preview."""
    if not isinstance(status, dict) or not all(k in status for k in BUSY_KEYS):
        raise ValueError("Unrecognized Studio busy-state schema")
    if pending_processing is not None:
        if (not isinstance(pending_processing,dict)
                or not isinstance(pending_processing.get("id"),str)
                or not pending_processing["id"]
                or pending_processing.get("done") is not True
                or pending_processing.get("preview_ready") is not True
                or "error" not in pending_processing
                or pending_processing["error"] is not None
                or status["processing"] != pending_processing):
            raise ValueError("Expected completed processing preview no longer matches")
    busy = []
    for key in BUSY_KEYS:
        value = status[key]
        if key == "processing" and pending_processing is not None:
            continue
        if value is None or value == []:
            continue
        if (key == "stems" and isinstance(value, dict)
                and value.get("done") is True and "error" in value
                and value["error"] is None
                and type(value.get("progress")) in (int, float)
                and value["progress"] == 1.0
                and isinstance(value.get("song_id"), str)
                and value["song_id"]):
            continue
        busy.append(key)
    return busy


def _recognition(data):
    if not isinstance(data, dict) or data.get("provider") != "whisper":
        raise ValueError("Expected a native Whisper recognition response")
    if not isinstance(data.get("text"), str) or not _tokens(data["text"]):
        raise ValueError("Recognition has no usable words; cannot assess coverage")
    return data["text"]


def _sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def _write(path, obj):
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def recognition_preflight(client):
    """Read-only readiness checks, shared by combined workflows."""
    names = {t.get("name") for t in client.tools()}
    if not {"karaoke_settings_get","studio_status","lyrics_recognise"} <= names:
        raise ValueError("Missing native recognition capability")
    s = unpack(client.call("karaoke_settings_get", {"response_format":"concise"}))
    if (not isinstance(s, dict) or s.get("provider") != "whisper"
            or s.get("enabled") is not True or s.get("ready") is not True
            or "download" not in s or s["download"] is not None):
        raise ValueError("Local Whisper backend must be enabled, ready and not downloading")
    models = s.get("models", [])
    if not isinstance(models, list) or not any(
        isinstance(m, dict) and m.get("id") == "crisperwhisper-turbo"
        and m.get("installed") is True for m in models):
        raise ValueError("Installed CrisperWhisper Turbo not confirmed")
    return s


def capture(audio, out, url=None, *, confirm=False, language=None, pending_processing=None):
    """Explicit single inference; fresh output and immutable submission marker."""
    if not confirm:
        raise ValueError("Explicit --confirm-recognition required")
    audio, out = Path(audio).resolve(strict=True), Path(out)
    if not audio.is_file() or audio.suffix.lower() not in (".flac", ".wav"):
        raise ValueError("Expected a local FLAC/WAV file")
    if out.exists():
        raise ValueError("Recognition output already exists; never retry blindly")
    sha = _sha(audio)
    client = Client(configured_endpoint(url), timeout=600).connect()
    s = recognition_preflight(client)
    status = unpack(client.call("studio_status", {}))
    busy = _busy_keys(status, pending_processing)
    if busy:
        raise ValueError("Studio is not idle: " + ", ".join(busy))
    out.mkdir(parents=True, exist_ok=False)
    _write(out/"submission.json", {"state":"SUBMITTING", "audio_sha256":sha,
          "provider":"whisper", "runtime_configured":s.get("runtime"),
          "language_requested":language, "model_installed":"crisperwhisper-turbo"})
    args = {"path":str(audio)}
    if language:
        args["language"] = language
    # No retry, no global settings change. User must keep Studio idle.
    raw = unpack(client.call("lyrics_recognise", args))
    _write(out/"recognition.json", raw)
    _recognition(raw)
    if pending_processing is not None:
        after=unpack(client.call("studio_status", {}))
        if _busy_keys(after,pending_processing):
            raise ValueError("Studio activity changed during preview recognition")
    if _sha(audio) != sha:
        raise ValueError("Audio changed during recognition; response retained but invalid")
    _write(out/"receipt.json", {"state":"RESPONSE_RECEIVED",
                              "audio_sha256":sha, "human_verified":False})
    return {"report":str(out/"recognition.json"), "provider":"whisper",
            "human_verified":False, "audio_jobs_created":0,
            "recognition_calls":1}


def review(lyrics, a, b):
    """Map minimum-edit discrepancies to reference lines, not audio time."""
    lines = []
    word_to_line = {}
    index = 0
    for g in parse_lyrics(lyrics):
        for i, line in enumerate(g["lines"], 1):
            tokens = _tokens(line)
            row = {"section":f"{g['name']}#{g['occurrence']}",
                   "line_index":i, "reference_words":len(tokens),
                   "reference_text":line, "A":[], "B":[]}
            row_id = len(lines)
            lines.append(row)
            for _ in tokens:
                index += 1
                word_to_line[index] = row_id
    arms = {}
    boundary = {"A":[], "B":[]}
    for arm, data in (("A",a),("B",b)):
        metrics = compare_lyrics(lyrics, _recognition(data))
        metrics["asr_reference_disagreement_rate"] = metrics.pop("word_error_rate")
        for edit in metrics.pop("edits"):
            if edit["kind"] == "insertion":
                pos = edit["after_reference_index"]
                before, after = word_to_line.get(pos), word_to_line.get(pos+1)
                if before != after:
                    def identify(i):
                        return None if i is None else {
                            k:lines[i][k] for k in ("section","line_index")}
                    boundary[arm].append({**edit,"preceding_line":identify(before),
                                         "following_line":identify(after)})
                    continue
                target = before
            else:
                target = word_to_line[edit["reference_index"]]
            lines[target][arm].append(edit)
        metrics.pop("warnings", None)
        arms[arm] = metrics
    for line in lines:
        line["A_count"] = len(line["A"])
        line["B_count"] = len(line["B"])
    return {"schema":"native-asr-review-v1", "human_verified":False,
            "provider":"whisper", "arms":arms, "reference_lines":lines,
            "boundary_insertions":boundary, "quality_decision":"human_review_required",
            "audio_jobs_created":0, "recognition_calls":0,
            "warnings":["ASR hypotheses are not verified sung transcripts.",
                        "Inputs must cover the same intended full song; coverage and backend settings are not inferred.",
                        "Line localization is one minimum-edit alignment; repeated words may be ambiguous.",
                        "Boundary insertions are not assigned to either neighboring line.",
                        "No audio timestamps, confidence, or acoustic causality can be inferred.",
                        "Never rank musical quality or trigger correction using these counts alone."]}
