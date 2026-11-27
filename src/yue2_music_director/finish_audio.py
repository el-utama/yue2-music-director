"""Local FLAC measurements and fixed-gain rendering; no Studio dependency."""
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil

from . import acoustic as ac
from .headroom_policy import CEILING_DBTP, gain_for_true_peak

POLICY="whole-mix-fixed-gain-v1"
LU_TOLERANCE=0.15
TP_TOLERANCE=0.15
LRA_TOLERANCE=0.5
OUTPUT_BITS=24


def _finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def plan_gain(metrics):
    values=[metrics.get(k) for k in ("integrated_lufs","true_peak_dbtp","loudness_range_lu")]
    if not all(_finite(v) for v in values):
        raise ValueError("Finite integrated loudness, true peak and LRA required")
    loudness,tp,lra=values
    if not -70<loudness<=10 or not -150<=tp<=0 or not 0<=lra<=100:
        raise ValueError("Silence, unreliable loudness or unsafe peak evidence; review original")
    gain=0.0 if tp<=CEILING_DBTP else gain_for_true_peak(tp)
    if loudness+gain<=-70:
        raise ValueError("Gain would put loudness below absolute measurement gate")
    return gain


def tools():
    ffmpeg,ffprobe=shutil.which("ffmpeg"),shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise ValueError("FFmpeg and ffprobe required on PATH")
    versions={name:ac._run([exe,"-version"],10).stdout.splitlines()[0]
              for name,exe in (("ffmpeg",ffmpeg),("ffprobe",ffprobe))}
    return ffmpeg,ffprobe,versions


def sample_geometry(path,ffprobe):
    """Count decoded samples per channel, not a rounded duration estimate."""
    options=["-v","error","-f","flac","-protocol_whitelist","file","-select_streams","a"]
    result=ac._run([ffprobe,*options,"-show_entries",
                    "stream=codec_name,sample_rate,channels,duration_ts,time_base,bits_per_raw_sample,bits_per_sample",
                    "-of","json",str(path)],30)
    streams=json.loads(result.stdout).get("streams",[])
    if result.stderr.strip() or len(streams)!=1:
        raise ValueError("Expected one error-free decoded audio stream")
    stream=streams[0]
    try:
        rate=int(stream["sample_rate"])
        channels=int(stream["channels"])
        bits=int(stream.get("bits_per_raw_sample") or stream.get("bits_per_sample") or 0)
        exact=Fraction(int(stream["duration_ts"]))*Fraction(stream["time_base"])*rate
    except (KeyError,TypeError,ValueError,ZeroDivisionError) as exc:
        raise ValueError("Missing exact sample geometry") from exc
    if (stream.get("codec_name")!="flac" or not 8000<=rate<=192000
            or channels not in (1,2) or bits not in (16,24)
            or exact.denominator!=1 or not rate<=exact<=210*rate):
        raise ValueError("Expected 1–210 seconds of mono/stereo 16/24-bit FLAC with exact sample geometry")
    decoded=ac._run([ffprobe,*options,"-show_frames","-show_entries","frame=nb_samples",
                     "-of","json",str(path)],120)
    frames=json.loads(decoded.stdout).get("frames",[])
    if decoded.stderr.strip() or not frames:
        raise ValueError("Audio decoding failed")
    try:
        counts=[int(frame["nb_samples"]) for frame in frames]
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError("Missing decoded sample counts") from exc
    if any(n<=0 for n in counts) or sum(counts)!=exact:
        raise ValueError("Decoded sample count differs from declared FLAC duration")
    return {"sample_count_per_channel":sum(counts),"sample_rate_hz":rate,
            "channels":channels,"bits_per_sample":bits,"codec":"flac"}


def validate_measurement(measurement,geometry):
    for k in ("sample_rate_hz","channels","bits_per_sample","codec"):
        if measurement.get(k)!=geometry.get(k):
            raise ValueError("Acoustic and decoded stream geometry differ: "+k)
    rate=geometry["sample_rate_hz"]
    count=geometry["sample_count_per_channel"]
    if (type(rate) is not int or not 8000<=rate<=192000 or type(count) is not int
            or not rate<=count<=210*rate or geometry["channels"] not in (1,2)
            or geometry["bits_per_sample"] not in (16,24) or geometry["codec"]!="flac"):
        raise ValueError("Invalid decoded stream geometry")
    duration=measurement.get("duration_seconds")
    if not _finite(duration) or abs(duration-count/rate)>max(1/rate,1e-6):
        raise ValueError("Acoustic duration differs from decoded sample count")
    if not isinstance(measurement.get("sha256"),str) or len(measurement["sha256"])!=64:
        raise ValueError("Missing audio SHA-256")
    plan_gain(measurement)


def measure(path,ffmpeg,ffprobe,expected_sha=None):
    path=Path(path).resolve(strict=True)
    if not path.is_file() or path.suffix.lower()!=".flac":
        raise ValueError("Retained FLAC source required")
    if expected_sha is not None and ac._hash(path)!=expected_sha:
        raise ValueError("Retained audio hash differs")
    measurement=ac._measure(path,ffmpeg,ffprobe)
    geometry=sample_geometry(path,ffprobe)
    if ac._hash(path)!=measurement["sha256"] or expected_sha is not None and measurement["sha256"]!=expected_sha:
        raise ValueError("Audio changed during finishing measurement")
    validate_measurement(measurement,geometry)
    return {"acoustic":measurement,"geometry":geometry}


def render(source,target,gain,ffmpeg):
    if not -1.5<=gain<0 or Path(target).exists():
        raise ValueError("Unsafe gain or existing candidate; never overwrite")
    ac._run([ffmpeg,"-nostdin","-v","error","-xerror","-f","flac",
             "-protocol_whitelist","file","-i",str(source),"-map","0:a:0",
             "-vn","-sn","-dn","-af",f"volume={gain:.2f}dB:precision=double",
             "-c:a","flac","-sample_fmt","s32","-bits_per_raw_sample",str(OUTPUT_BITS),
             "-map_metadata","-1","-map_chapters","-1","-n",str(target)],180)


def verify_candidate(before,after,gain):
    a,b=before["acoustic"],after["acoustic"]
    x,y=before["geometry"],after["geometry"]
    validate_measurement(a,x)
    validate_measurement(b,y)
    if gain!=plan_gain(a) or gain>=0:
        raise ValueError("Candidate gain differs from measured policy")
    if (a["sha256"]==b["sha256"] or any(x[k]!=y[k] for k in
            ("sample_count_per_channel","sample_rate_hz","channels","codec"))
            or y["bits_per_sample"]!=OUTPUT_BITS):
        raise ValueError("Candidate audio geometry or identity differs")
    if (b["true_peak_dbtp"]>CEILING_DBTP
            or abs(b["true_peak_dbtp"]-a["true_peak_dbtp"]-gain)>TP_TOLERANCE
            or abs(b["integrated_lufs"]-a["integrated_lufs"]-gain)>LU_TOLERANCE
            or abs(b["loudness_range_lu"]-a["loudness_range_lu"])>LRA_TOLERANCE):
        raise ValueError("Candidate failed measured gain/headroom/dynamics checks")
    return True

def pcm_hash(path,ffmpeg,*,gain=None):
    """SHA-256 of decoded 24-bit PCM, with optional exact planned gain."""
    args=[ffmpeg,"-nostdin","-v","error","-xerror","-f","flac",
          "-protocol_whitelist","file","-i",str(path),"-map","0:a:0","-vn","-sn","-dn"]
    if gain is not None:
        if not -1.5<=gain<0:
            raise ValueError("Invalid fixed PCM gain")
        args.extend(["-af",f"volume={gain:.2f}dB:precision=double"])
    args.extend(["-c:a","pcm_s24le","-f","hash","-hash","sha256","-"])
    output=ac._run(args,180).stdout.strip()
    if not output.startswith("SHA256="):
        raise ValueError("Decoded PCM hash unavailable")
    digest=output[7:].lower()
    if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid decoded PCM hash")
    return digest
