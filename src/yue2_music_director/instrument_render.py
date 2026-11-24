"""Offline paired MIDI render QA. Measures response, not subjective naturalness."""
from array import array
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import wave

from .midi_events import parse_midi_data, compare_midi_data
from .instrument_velocity import ROLES


def accompaniment(data):
    parsed = parse_midi_data(data)
    keep = {i for i,n in parsed["track_names"].items()
            if len(n)==1 and n[0].strip().casefold() in ROLES}
    if not keep or parsed["format"] != 1 or 0 in keep:
        raise ValueError("Expected SMF 1 with named accompaniment and separate conductor")
    if any(n.track==0 for n in parsed["notes"]):
        raise ValueError("Conductor contains notes")
    # Keep conductor and accompaniment track chunks, preserving tempo, meter,
    # program, controllers, timing and velocities in the retained tracks.
    start = 8+int.from_bytes(data[4:8],"big")
    header = bytearray(data[:start])
    tracks = []
    for i in range(parsed["tracks"]):
        end = start+8+int.from_bytes(data[start+4:start+8],"big")
        if i==0 or i in keep:
            tracks.append(data[start:end])
        start=end
    header[10:12] = len(tracks).to_bytes(2,"big")
    out = bytes(header)+b"".join(tracks)
    parse_midi_data(out)
    return out


def _seconds(tick, tempos, division):
    last, seconds, tempo = 0, 0.0, 500000
    for at, value in tempos:
        if at > tick:
            break
        if value <= 0:
            raise ValueError("Invalid tempo")
        seconds += (at-last)*tempo/(division*1e6)
        last, tempo = at,value
    return seconds+(tick-last)*tempo/(division*1e6)


def _read_wav(path):
    with wave.open(str(path),"rb") as f:
        if f.getsampwidth()!=2 or f.getnchannels()!=2 or f.getframerate()!=44100:
            raise ValueError("Expected stereo 44.1 kHz PCM16 render")
        if not 0 < f.getnframes() <= 44100*1800:
            raise ValueError("Invalid render duration")
        samples=array("h",f.readframes(f.getnframes()))
    if sys.byteorder!="little":
        samples.byteswap()
    return samples


def _db(samples,start,end):
    a,b=round(start*44100)*2,round(end*44100)*2
    if a<0 or b>len(samples) or b<=a:
        return None
    part=samples[a:b]
    energy=sum(x*x for x in part)/len(part)
    return 10*math.log10(energy/(32768**2)) if energy>0 else None


def measure(a_path,b_path,midi_a,midi_b):
    a,b=_read_wav(a_path),_read_wav(b_path)
    x,y=parse_midi_data(midi_a),parse_midi_data(midi_b)
    if len(a)!=len(b):
        raise ValueError("Render lengths differ")
    groups=defaultdict(list)
    for p,q in zip(x["notes"],y["notes"]):
        groups[p.start].append((p.velocity,q.velocity))
    ticks=sorted(groups)
    if not ticks:
        raise ValueError("No accompaniment onsets")
    times=[_seconds(t,x["tempos"],x["division"]) for t in ticks]
    rows=[]
    for i,(tick,start) in enumerate(zip(ticks,times)):
        end=min(start+0.08,times[i+1] if i+1<len(times) else start+0.08)
        if end-start<0.025:
            continue
        da,db=_db(a,start,end),_db(b,start,end)
        if da is None or db is None or da < -65 or db < -65:
            continue
        change=statistics.mean(q-p for p,q in groups[tick])
        rows.append((da,db,change))
    deltas=[r[1]-r[0] for r in rows]
    spread=lambda v: statistics.pstdev(v) if len(v)>1 else None
    return {"onsets_total":len(ticks),"onsets_measured":len(rows),
            "onset_rms_sd_db":{"control":spread([r[0] for r in rows]),"candidate":spread([r[1] for r in rows])},
            "paired_gain_delta_sd_db":spread(deltas),
            "median_paired_gain_delta_db":statistics.median(deltas) if deltas else None,
            "sample_difference":a!=b,"clipped_samples":{"control":sum(abs(v)>=32767 for v in a),
                "candidate":sum(abs(v)>=32767 for v in b)},
            "duration_seconds":len(a)/(2*44100),
            "scope":"mixed accompaniment onset windows; not isolated note attacks"}


def run(source,candidate,soundfont,out,renderer="fluidsynth"):
    a,b=Path(source).read_bytes(),Path(candidate).read_bytes()
    report=compare_midi_data(a,b)
    if report["pitch_changes"] or report["timing_changes"] or not report["velocity_changes"]:
        raise ValueError("Expected velocity-only candidate")
    parsed=parse_midi_data(a)
    allowed={parsed["note_on_offsets"][n.order] for n in parsed["notes"]
             if len(parsed["track_names"].get(n.track,[]))==1
             and parsed["track_names"][n.track][0].strip().casefold() in ROLES}
    if len(a)!=len(b) or any(p!=q and i not in allowed for i,(p,q) in enumerate(zip(a,b))):
        raise ValueError("Candidate changes protected MIDI bytes")
    sf=Path(soundfont).resolve(strict=True)
    if not sf.is_file() or sf.suffix.lower()!=".sf2":
        raise ValueError("Explicit local SF2 file required")
    exe=shutil.which(renderer)
    if not exe:
        raise ValueError("FluidSynth executable unavailable; no download attempted")
    def invoke(args,timeout):
        result=subprocess.run([exe,*args],capture_output=True,text=True,timeout=timeout)
        if result.returncode:
            raise ValueError("FluidSynth failed: "+result.stderr[-1000:])
        return result.stdout
    version=invoke(["--version"],15).strip()
    def digest(path):
        with path.open("rb") as f:
            h=hashlib.sha256()
            for chunk in iter(lambda:f.read(1048576),b""):
                h.update(chunk)
        return h.hexdigest()
    sf_hash=digest(sf)
    out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    ma,mb=accompaniment(a),accompaniment(b)
    for label,mid in (("control",ma),("candidate",mb)):
        midi=out/(label+".mid")
        wav=out/(label+".wav")
        midi.write_bytes(mid)
        invoke(["-ni","-F",str(wav),"-T","wav","-O","s16","-r","44100",
                "-g","0.5",str(sf),str(midi)],180)
    metrics=measure(out/"control.wav",out/"candidate.wav",ma,mb)
    if digest(sf)!=sf_hash:
        raise ValueError("SoundFont changed during rendering")
    sd=metrics["paired_gain_delta_sd_db"]
    status=("response_detected" if metrics["onsets_measured"]>=8 and sd is not None and sd>=0.1
            and metrics["sample_difference"] and not any(metrics["clipped_samples"].values())
            else "inconclusive")
    result={"schema":"instrument-render-qa-v1","renderer":version,"soundfont_sha256":sf_hash,
            "velocity_changes":report["velocity_changes"],"metrics":metrics,"status":status,
            "naturalness_verified":False,"audio_jobs_created":0,"local_renders":2,
            "warnings":["Same SF2/renderer settings; no YuE2 generation.",
                        "0.1 dB variation is a diagnostic threshold, not a naturalness criterion.",
                        "Rendered ABC-derived accompaniment is not the original generated arrangement."]}
    (out/"report.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return result
