"""Offline arrangement-preserving stem-delta processing.

Not a per-instrument velocity editor or a learned naturalness evaluator.
Only the contribution estimated by the instrumental stem is attenuated;
the original mix, rather than a recombined pair of stems, is the base.
"""
from array import array
from contextlib import ExitStack
import json
import math
from pathlib import Path
import shutil
import statistics
import sys
from tempfile import TemporaryDirectory

from .acoustic import _hash, _run, compare, FORMATS

BLOCK_MS = 10
MAX_SECONDS = 600


def _db(energy):
    return 10 * math.log10(max(energy, 1e-12))


def residual_budget(residual_db, requested_db):
    """Conservative engineering proxy, not a bound on vocal leakage.

    Scale maximum gain change so that gain-change fraction times the
    measured reconstruction residual RMS is at most -40 dB of mix RMS.
    Reject gross mismatch independently; preserve original mix residual.
    """
    if not math.isfinite(residual_db) or residual_db > -20:
        return 0.0
    fraction = min(1-10**(-requested_db/20), 10**((-40-residual_db)/20))
    return -20*math.log10(1-fraction)


def envelope(energies, max_db=2.0):
    """Enhance existing attack-level contrast, not a synthetic beat grid."""
    if not math.isfinite(max_db) or not 0.25 <= max_db <= 3:
        raise ValueError("max_db must be between 0.25 and 3")
    levels = [_db(e) for e in energies]
    onsets = []
    for i in range(4, len(levels)-8):
        if (levels[i] > -50 and levels[i] - _db(statistics.mean(energies[i-4:i])) >= 4
                and (not onsets or i-onsets[-1] >= 12)):
            onsets.append(i)
    attacks = [_db(statistics.mean(energies[i:i+8])) for i in onsets]
    gains = [0.0]*len(energies)
    edited = []
    if len(onsets) >= 8:
        for n, i in enumerate(onsets):
            local = attacks[max(0,n-4):n+5]
            # Attenuate below-local-median attacks only; never amplify.
            depth = min(max_db, max(0.0, (statistics.median(local)-attacks[n]-0.5)*0.5))
            if depth < 0.1:
                continue
            edited.append({"block":i, "attenuation_db":round(depth,3)})
            # Smooth attack and release over 120 ms; no hard gain edges.
            for k in range(-1, 12):
                if 0 <= i+k < len(gains):
                    shape = 0.0 if k==-1 else (1.0 if k<=3 else (12-k)/9)
                    gains[i+k] = min(gains[i+k], -depth*shape)
    return gains, onsets, edited


def _pcm(raw):
    if len(raw)%4:
        raise ValueError("Truncated float PCM")
    values = array("f")
    values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    if any(not math.isfinite(v) for v in values):
        raise ValueError("Nonfinite PCM")
    return values


def _bytes(values):
    if sys.byteorder != "little":
        values.byteswap()
    return values.tobytes()


def _blocks(paths, block_samples):
    with ExitStack() as stack:
        files = [stack.enter_context(p.open("rb")) for p in paths]
        while True:
            chunks = [f.read(block_samples*4) for f in files]
            if not any(chunks):
                break
            if len({len(c) for c in chunks}) != 1:
                raise ValueError("PCM lengths differ")
            yield [_pcm(c) for c in chunks]


def inspect(paths, block_samples):
    energies = []
    total = residual = 0.0
    count = 0
    for mix, ins, voice in _blocks(paths,block_samples):
        if any(abs(x)>1.00001 for x in mix):
            raise ValueError("Source mix exceeds PCM full scale")
        energies.append(sum(x*x for x in ins)/len(ins))
        total += sum(x*x for x in mix)
        residual += sum((x-y-z)**2 for x,y,z in zip(mix,ins,voice))
        count += len(mix)
    if not count or total<=1e-9:
        raise ValueError("Empty or silent mix")
    return energies, _db(residual/total), count


def apply_delta(mix, ins, start_db, end_db, channels):
    if len(mix)!=len(ins) or len(mix)%channels:
        raise ValueError("PCM channel mismatch")
    output = array("f")
    frames=len(mix)//channels
    for i,(x,y) in enumerate(zip(mix,ins)):
        fraction=(i//channels+1)/frames
        db=start_db+(end_db-start_db)*fraction
        # Preserve the original mix exactly except for the accompaniment delta.
        output.append(x+(10**(db/20)-1)*y)
    return output


def _decode(path, target, ffmpeg, ffprobe):
    fmt=FORMATS.get(path.suffix.lower())
    if not fmt:
        raise ValueError("Only FLAC and WAV inputs are supported")
    opts=["-f",fmt,"-protocol_whitelist","file"]
    probe=_run([ffprobe,"-v","error",*opts,"-show_entries",
                "stream=codec_type,sample_rate,channels,duration","-select_streams","a","-of","json",str(path)],30)
    streams=json.loads(probe.stdout).get("streams",[])
    if len(streams)!=1 or streams[0].get("codec_type")!="audio":
        raise ValueError(f"{path.name}: expected one audio stream, found {len(streams)}")
    s=streams[0]
    rate,channels=int(s["sample_rate"]),int(s["channels"])
    duration=float(s.get("duration",0))
    if rate not in (44100,48000) or channels not in (1,2) or not 0<duration<=MAX_SECONDS:
        raise ValueError("Expected 44.1/48 kHz mono/stereo, duration up to 10 minutes")
    _run([ffmpeg,"-nostdin","-v","error",*opts,"-i",str(path),"-map","0:a:0",
          "-c:a","pcm_f32le","-f","f32le","-n",str(target)],180)
    if target.stat().st_size > MAX_SECONDS*rate*channels*4:
        raise ValueError("Decoded PCM exceeds duration limit")
    return rate,channels


def process(mix, instrumental, vocals, out, max_db=2.0):
    if not math.isfinite(max_db) or not 0.25<=max_db<=3:
        raise ValueError("max_db must be between 0.25 and 3")
    inputs=[Path(p).resolve(strict=True) for p in (mix,instrumental,vocals)]
    if len(set(inputs))!=3 or any(not p.is_file() for p in inputs):
        raise ValueError("Three distinct source files required")
    out=Path(out).resolve()
    if out.exists():
        raise ValueError("Output directory already exists")
    ffmpeg,ffprobe=shutil.which("ffmpeg"),shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise ValueError("FFmpeg and ffprobe required")
    hashes=[_hash(p) for p in inputs]
    report={"schema":"instrument-dynamics-v1","source_sha256":dict(zip(
        ("mix","instrumental","vocals"),hashes)),"max_attenuation_db":max_db,
        "audio_jobs_created":0,"recognition_calls":0,"naturalness_verified":False,
        "warnings":["Stem-delta processing only; not per-note MIDI velocity.",
                    "Vocal leakage into the instrumental stem can be affected.",
                    "Onset contrast heuristic is not a calibrated naturalness score."]}
    with TemporaryDirectory(prefix="yue2-dynamics-") as tmp:
        work=Path(tmp)
        raws=[work/(str(i)+".f32") for i in range(3)]
        formats=[_decode(p,q,ffmpeg,ffprobe) for p,q in zip(inputs,raws)]
        rate,channels=formats[0]
        if any(c!=channels for _,c in formats):
            raise ValueError(f"Channel count differs; no downmix: {formats}")
        original_frames=[p.stat().st_size//(4*channels) for p in raws]
        if any(p.stat().st_size%(4*channels) or n<=0 for p,n in zip(raws,original_frames)):
            raise ValueError("Invalid decoded frame count")
        frames=original_frames[0]
        adjustments=[]
        for i in (1,2):
            stem_rate=formats[i][0]
            # Require durations to agree within two source/target frames.
            # No arbitrary time stretch, offset search or long padding.
            if abs(original_frames[i]/stem_rate-frames/rate)>2/min(rate,stem_rate):
                raise ValueError(f"Stem duration differs: rates={formats}, frames={original_frames}")
            if stem_rate!=rate:
                target=work/(str(i)+".resampled.f32")
                _run([ffmpeg,"-nostdin","-v","error","-f","f32le","-ar",str(stem_rate),
                      "-ac",str(channels),"-i",str(raws[i]),"-af",
                      f"aresample={rate}:resampler=swr:filter_size=64:phase_shift=10",
                      "-c:a","pcm_f32le","-f","f32le","-n",str(target)],180)
                raws[i]=target
            size=raws[i].stat().st_size
            if size%(4*channels):
                raise ValueError("Invalid resampled PCM frame count")
            delta=size//(4*channels)-frames
            if abs(delta)>4:
                raise ValueError(f"Unexpected resampled frame difference: {delta}")
            if delta:
                with raws[i].open("r+b") as f:
                    f.truncate(frames*channels*4)
            adjustments.append({"stem":("instrumental","vocals")[i-1],
                                "source_rate_hz":stem_rate,"source_frames":original_frames[i],
                                "resampled":stem_rate!=rate,"tail_frames_removed":max(0,delta),
                                "tail_frames_zero_padded":max(0,-delta)})
        report["source_sample_rates_hz"]=[r for r,_ in formats]
        report["source_frame_counts"]=original_frames
        report["stem_alignment"]=adjustments
        block=rate//100*channels
        energies,residual,count=inspect(raws,block)
        report.update({"sample_rate_hz":rate,"channels":channels,"frames":count//channels,
                       "reconstruction_residual_db":residual})
        effective_db=residual_budget(residual,max_db)
        report["effective_max_attenuation_db"]=effective_db
        report["residual_proxy_target_db"]=-40
        report["warnings"].append("Residual budget is a global engineering proxy, not a bound on vocal leakage or a quality certificate.")
        if effective_db<0.25:
            gains,onsets,edited=[0.0]*len(energies),[],[]
            report["status"]="blocked_reconstruction"
        else:
            gains,onsets,edited=envelope(energies,effective_db)
        report.update({"onsets_detected":len(onsets),"attacks_edited":len(edited),
                       "gain_min_db":min(gains),"edits":edited})
        if not edited:
            report.setdefault("status","no_safe_effect")
        else:
            raw_out=work/"candidate.f32"
            peak=0.0
            previous=0.0
            with raw_out.open("wb") as f:
                for i,(original,stem) in enumerate(_blocks(raws[:2],block)):
                    values=apply_delta(original,stem,previous,gains[i],channels)
                    peak=max(peak,max(abs(x) for x in values))
                    f.write(_bytes(values))
                    previous=gains[i]
            report["candidate_sample_peak"]=peak
            if peak>1:
                report["status"]="blocked_sample_peak"
            else:
                target=work/"candidate.flac"
                _run([ffmpeg,"-nostdin","-v","error","-f","f32le","-ar",str(rate),
                      "-ac",str(channels),"-i",str(raw_out),"-c:a","flac","-sample_fmt","s32",
                      "-bits_per_raw_sample","24","-n",str(target)],180)
                acoustic=compare(inputs[0],target)
                report["acoustic"]=acoustic
                a,b=acoustic["arms"]["A"],acoustic["arms"]["B"]
                if (a["true_peak_dbtp"] is None or b["true_peak_dbtp"] is None
                        or a["integrated_lufs"] is None or b["integrated_lufs"] is None
                        or b["true_peak_dbtp"]>max(0,a["true_peak_dbtp"])+0.05
                        or abs(b["integrated_lufs"]-a["integrated_lufs"])>1
                        or abs(b["duration_seconds"]-a["duration_seconds"])>1/rate):
                    report["status"]="blocked_acoustic_guard"
                else:
                    report["status"]="candidate_created"
        if [_hash(p) for p in inputs]!=hashes:
            raise ValueError("Source changed during processing")
        out.mkdir(parents=True,exist_ok=False)
        if report["status"]=="candidate_created":
            with (out/"candidate.flac").open("xb") as f, target.open("rb") as src:
                shutil.copyfileobj(src,f)
        (out/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return report
