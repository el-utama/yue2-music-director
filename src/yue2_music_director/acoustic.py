"""Offline whole-mix A/B measurements using explicitly installed FFmpeg tools."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

FORMATS = {".flac": "flac", ".wav": "wav"}
FILTER = "loudnorm=I=-23:TP=-2:LRA=7:print_format=json"


def _run(args, timeout=120):
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              check=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("FFmpeg measurement timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError("FFmpeg/ffprobe failed; inspect audio and tool installation") from exc


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _number(value):
    try:
        n = float(value)
    except (ValueError, TypeError):
        return None
    return n if math.isfinite(n) else None


def _parse_loudness(stderr):
    # loudnorm emits its input and output stats as a flat JSON object.
    for candidate in reversed(re.findall(r"\{[^{}]*\}", stderr, re.S)):
        try:
            data = json.loads(candidate)
        except ValueError:
            continue
        if all(k in data for k in ("input_i", "input_tp", "input_lra")):
            return {"integrated_lufs": _number(data["input_i"]),
                    "true_peak_dbtp": _number(data["input_tp"]),
                    "loudness_range_lu": _number(data["input_lra"])}
    raise ValueError("No loudnorm measurement found")


def _measure(path, ffmpeg, ffprobe):
    path = Path(path).resolve(strict=True)
    fmt = FORMATS.get(path.suffix.lower())
    if not path.is_file() or fmt is None:
        raise ValueError("Only local FLAC and WAV files are supported")
    sha = _hash(path)
    options = ["-f", fmt, "-protocol_whitelist", "file"]
    info = _run([ffprobe, "-v", "error", *options, "-select_streams", "a",
                 "-show_entries", "stream=codec_name,sample_rate,channels,duration,bits_per_raw_sample,bits_per_sample",
                 "-of", "json", str(path)], 30)
    streams = json.loads(info.stdout).get("streams", [])
    if len(streams) != 1:
        raise ValueError("Expected exactly one audio stream")
    s = streams[0]
    duration = _number(s.get("duration"))
    channels = int(s["channels"])
    rate = int(s["sample_rate"])
    if duration is None or not 0 < duration <= 1800 or channels not in (1, 2) or not 8000 <= rate <= 192000:
        raise ValueError("Expected finite audio duration <=30 min, mono/stereo and supported sample rate")
    result = _run([ffmpeg, "-hide_banner", "-nostdin", "-nostats", "-v", "info",
                   *options, "-i", str(path), "-map", "0:a:0", "-af", FILTER,
                   "-f", "null", "-"])
    bits = _number(s.get("bits_per_raw_sample")) or _number(s.get("bits_per_sample"))
    stats = _parse_loudness(result.stderr)
    if _hash(path) != sha:
        raise ValueError("Audio changed during measurement")
    return {"sha256": sha, "codec": s["codec_name"], "duration_seconds": duration,
            "sample_rate_hz": rate, "channels": channels,
            "bits_per_sample": int(bits) if bits else None, **stats}


def compare(a, b):
    """Measure original input statistics only; do not export normalized audio."""
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise ValueError("Install FFmpeg and ffprobe on PATH to use acoustic-compare")
    versions = {name: _run([exe, "-version"], 10).stdout.splitlines()[0]
                for name, exe in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe))}
    arms = {"A": _measure(a, ffmpeg, ffprobe), "B": _measure(b, ffmpeg, ffprobe)}
    x, y = arms["A"], arms["B"]
    delta = {}
    for key in ("duration_seconds", "integrated_lufs", "true_peak_dbtp", "loudness_range_lu"):
        delta[key] = round(y[key] - x[key], 6) if x[key] is not None and y[key] is not None else None
    gains = None
    # Below the EBU absolute gate, FFmpeg may report non-finite values or
    # a floor. Avoid recommending gain when loudness is not meaningful.
    if (x["channels"] == y["channels"] and
            all(v["integrated_lufs"] is not None and v["integrated_lufs"] > -70
                and v["true_peak_dbtp"] is not None for v in arms.values())):
        target = min(x["integrated_lufs"], y["integrated_lufs"])
        # Attenuate only, also leave at least 1 dB true-peak headroom.
        target = min(target, *(v["integrated_lufs"] - v["true_peak_dbtp"] - 1 for v in arms.values()))
        gains = {arm: round(target - v["integrated_lufs"], 2) for arm, v in arms.items()}
    return {"schema": "acoustic-compare-v1", "tool_versions": versions,
            "measurement_filter": FILTER, "arms": arms, "B_minus_A": delta,
            "suggested_playback_gain_db": gains,
            "identical_file_bytes": x["sha256"] == y["sha256"], "audio_jobs_created": 0,
            "warnings": ["Whole-mix measurements, not isolated vocal expression.",
                         "Playback gain is an attenuation recommendation, not an audio edit.",
                         "No transcription, phoneme alignment or causal inference.",
                         "Non-finite measurements are null; do not infer quality from loudness."]}
