"""Continue a captured, peak-only blocked native preview. Never submit processing."""
import json
import math
from pathlib import Path
import shutil

from .acoustic import compare, _run
from .headroom_policy import gain_for_true_peak
from .mcp import Client, configured_endpoint, unpack
from .native_process import inspect_preview, _run as processing_run, _verify_run
from .native_recognition import _sha, _write, _busy_keys, capture, _recognition, recognition_preflight
from .multilingual_fidelity import assess, compare as compare_text


def _read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def gain_plan(acoustic):
    a,b=acoustic["arms"]["A"],acoustic["arms"]["B"]
    if any(a[k]!=b[k] for k in ("duration_seconds","sample_rate_hz","channels")):
        raise ValueError("Preview format or duration differs")
    tp=b["true_peak_dbtp"]
    la,lb=a["integrated_lufs"],b["integrated_lufs"]
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (tp,la,lb)):
        raise ValueError("Missing finite acoustic metrics")
    if not -1<tp<=0 or abs(lb-la)>1:
        raise ValueError("Not a peak-only blocked preview")
    return gain_for_true_peak(tp)


def corrected_pass(before, after, gain):
    a,b=before["arms"]["A"],before["arms"]["B"]
    x,y=after["arms"]["A"],after["arms"]["B"]
    return (a["sha256"]==x["sha256"]
            and all(a[k]==y[k] for k in ("duration_seconds","sample_rate_hz","channels"))
            and y["true_peak_dbtp"] is not None and y["true_peak_dbtp"]<=-1
            and y["integrated_lufs"] is not None
            and abs(y["integrated_lufs"]-b["integrated_lufs"]-gain)<=0.15
            and abs(y["integrated_lufs"]-a["integrated_lufs"])<=2.5)


def continue_preview(source, directory, lyrics, baseline_asr, language, url=None, *, confirm=False):
    if not confirm:
        raise ValueError("Explicit --confirm-recognition required")
    source=Path(source).resolve(strict=True)
    directory=Path(directory).resolve(strict=True)
    if inspect_preview(directory,source)["status"]!="preview_acoustic_blocked":
        raise ValueError("Only a captured acoustic-blocked preview can be continued")
    out=directory/"headroom-continuation"
    if out.exists() or (directory/"recognition").exists() or (directory/"evaluation.json").exists():
        raise ValueError("Existing continuation or recognition evidence; never retry blindly")
    submission=_read(directory/"submission.json")
    report=_read(directory/"report.json")
    raw=directory/"preview.flac"
    lyrics,baseline_asr=Path(lyrics).resolve(strict=True),Path(baseline_asr).resolve(strict=True)
    hashes=(_sha(lyrics),_sha(baseline_asr))
    if submission.get("screening")!={"language":language,"lyrics_sha256":hashes[0],"baseline_asr_sha256":hashes[1]}:
        raise ValueError("Screening inputs do not match original transaction")
    reference=lyrics.read_text(encoding="utf-8-sig")
    baseline=_recognition(_read(baseline_asr))
    assess(reference,baseline,language)
    # Remeasure the saved raw preview instead of trusting stored numbers alone.
    before=compare(source,raw)
    gain=gain_plan(before)
    if before["arms"]["B"]["sha256"]!=report["preview_sha256"] or before["arms"]["A"]["sha256"]!=report["source_sha256"]:
        raise ValueError("Captured preview or source changed")
    ffmpeg=shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("FFmpeg required")
    client=Client(configured_endpoint(url),timeout=30).connect()
    recognition_preflight(client)
    current=processing_run(unpack(client.call("processing_get",{})))
    if current is not None:
        _verify_run(current,report["request"],report["run_id"])
        if not current["done"] or not current["preview_ready"] or current["error"] is not None:
            raise ValueError("Native preview is not completed")
    if _busy_keys(unpack(client.call("studio_status",{})),current):
        raise ValueError("Studio has other active work")
    out.mkdir(exist_ok=False)
    _write(out/"plan.json",{"gain_db":gain,"source_sha256":report["source_sha256"],
                            "raw_preview_sha256":report["preview_sha256"],"run_id":report["run_id"],
                            "screening":submission["screening"]})
    target=out/"candidate.flac"
    _run([ffmpeg,"-nostdin","-v","error","-f","flac","-protocol_whitelist","file",
          "-i",str(raw),"-map","0:a:0","-af",f"volume={gain:.2f}dB:precision=double",
          "-c:a","flac","-sample_fmt","s32","-bits_per_raw_sample","24","-n",str(target)],180)
    after=compare(source,target)
    result={"status":"headroom_acoustic_blocked","gain_db":gain,"before":before,"after":after,
            "processing_calls":0,"audio_jobs_created":0,"recognition_calls":0,"library_mutations":0,
            "automatic_acceptance":False,"naturalness_verified":False,"provisional_output":str(source),
            "warnings":["Fixed gain only; raw effect loudness difference remains limited to 1 LU. Final difference allows separately measured headroom attenuation.",
                        "ASR disagreement is not verified pronunciation or musical quality."]}
    def unchanged():
        return (_sha(source)==report["source_sha256"] and _sha(raw)==report["preview_sha256"]
                and _sha(target)==after["arms"]["B"]["sha256"] and (_sha(lyrics),_sha(baseline_asr))==hashes)
    if corrected_pass(before,after,gain) and unchanged():
        try:
            rec=capture(target,out/"recognition",url,confirm=True,pending_processing=current)
            result["recognition_calls"]=rec["recognition_calls"]
            if not unchanged() or processing_run(unpack(client.call("processing_get",{})))!=current:
                raise ValueError("Preview transaction or inputs changed")
            screen=compare_text(reference,baseline,_recognition(_read(out/"recognition/recognition.json")),language)
            result["lyric_screen"]=screen
            result["status"]="retain_original_asr_regression" if screen["status"]=="regression" else "candidate_nonregression_unverified"
            if screen["status"]!="regression":
                result["provisional_output"]=str(target)
        except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
            result["status"]="screening_blocked"
            result["reason"]=str(exc)
            if (out/"recognition/submission.json").exists() and not result["recognition_calls"]:
                result["recognition_calls"]="unknown_after_submission"
    _write(out/"report.json",result)
    return result
