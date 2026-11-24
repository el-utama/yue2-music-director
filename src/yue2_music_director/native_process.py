"""Native Studio preview adapter, based on pinned upstream ProcessRun contract.

No keep/discard, no generation, no implicit endpoint discovery.
The caller must reserve the Studio processing workspace for the whole run.
"""
import math
import json
import time
from pathlib import Path
import shutil

from .mcp import Client, configured_endpoint, unpack
from .native_recognition import _busy_keys, _sha, _write, capture, _recognition, recognition_preflight
from .multilingual_fidelity import assess, compare as compare_text
from .acoustic import compare

REQUIRED = {"studio_status", "library_song_files", "processing_get", "processing_start"}


def effect_request(song_id, effect, amount):
    if not isinstance(song_id,str) or not song_id.strip():
        raise ValueError("A library song ID is required")
    if not math.isfinite(amount) or not 0.05<=amount<=0.3:
        raise ValueError("Conservative preview amount must be 0.05 to 0.3")
    if effect=="naturalize":
        # Explicitly set all fields from the audited upstream defaults.
        settings={"amount":amount,"vibrato_rate":4.5,"vibrato_depth":1.0,
                  "formant_strength":1.0,"metallic_reduction":1.0,
                  "quantization_mask":0.0,"transition_smooth":1.0,"seed":1}
    elif effect=="lifter":
        settings={"denoise_strength":0.0,"noise_floor":0.1,"hf_mix":0.0,
                  "transient_boost":amount,"shimmer_reduction_db":0.0}
    else:
        raise ValueError("Only naturalize or lifter previews are supported")
    return {"song_id":song_id,effect:settings}


def _run(data):
    if not isinstance(data,dict) or "run" not in data:
        raise ValueError("Unrecognized processing_get result")
    run=data["run"]
    if run is not None and not isinstance(run,dict):
        raise ValueError("Invalid processing run")
    return run


def _verify_run(run, request, previous_id=None):
    if not isinstance(run,dict) or not isinstance(run.get("id"),str) or not run["id"]:
        raise ValueError("Processing run identity unavailable")
    effect=next(k for k in request if k!="song_id")
    if (run.get("song_id")!=request["song_id"] or run.get("stages")!=[effect]
            or previous_id is not None and run["id"]!=previous_id):
        raise ValueError("Processing run does not match this transaction")
    actual=run.get("request")
    if not isinstance(actual,dict) or not isinstance(actual.get(effect),dict):
        raise ValueError("Native processing request not echoed")
    settings=actual[effect]
    if set(settings)!=set(request[effect]):
        raise ValueError("Unexpected native effect settings")
    for key,value in request[effect].items():
        if type(settings[key]) not in (float,int) or not math.isclose(settings[key],value,rel_tol=1e-6,abs_tol=1e-8):
            raise ValueError("Native processing settings differ")
    if any(v is not None for k,v in actual.items() if k!=effect):
        raise ValueError("Unexpected extra processing stage or region")
    if type(run.get("done")) is not bool or type(run.get("preview_ready")) is not bool or "error" not in run:
        raise ValueError("Unrecognized native completion fields")
    return run["id"]


def _source_file(files, source):
    # Fail closed if an installed version exposes a different schema.
    if not isinstance(files,dict):
        raise ValueError("Unrecognized library files response")
    paths=[]
    for key in ("audio","audio_path"):
        value=files.get(key)
        if isinstance(value,dict):
            value=value.get("path")
        if isinstance(value,str) and value:
            paths.append(Path(value))
    if not paths or any(not p.is_absolute() or not p.is_file() or not p.samefile(source) for p in paths):
        raise ValueError("Library audio identity not verified against explicit source")


def _workspace(source):
    work=source.parent/"processing"
    if work.is_symlink() or work.exists() and not work.is_dir():
        raise ValueError("Unexpected processing workspace")
    if work.exists() and any(work.iterdir()):
        raise ValueError("Processing workspace is not empty; no automatic cleanup")
    return work


def preflight(client, source, request):
    tools=client.tools()
    names={t.get("name") for t in tools}
    if not REQUIRED<=names:
        raise ValueError("Required native processing tools not advertised")
    schema=next(t.get("inputSchema") for t in tools if t.get("name")=="processing_start")
    if not isinstance(schema,dict) or not set(request)<=set(schema.get("properties",{})):
        raise ValueError("Processing request not supported by local schema")
    if _run(unpack(client.call("processing_get",{}))) is not None:
        raise ValueError("An existing processing run is present; refusing to replace it")
    busy=_busy_keys(unpack(client.call("studio_status",{})))
    if busy:
        raise ValueError("Studio not idle: "+", ".join(busy))
    _source_file(unpack(client.call("library_song_files",{"song_id":request["song_id"]})),source)
    return _workspace(source)


def preview(source, song_id, effect, amount, out, url=None, *, confirm=False, timeout=300,
            lyrics=None, baseline_asr=None, language=None, confirm_recognition=False):
    """Read-only preflight by default, or one explicit preview and acoustic report."""
    source=Path(source).resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in (".flac",".wav"):
        raise ValueError("Expected original local FLAC/WAV")
    out=Path(out).resolve()
    if out.exists():
        raise ValueError("Output already exists; never retry submission blindly")
    if type(timeout) is not int or not 10<=timeout<=600:
        raise ValueError("Timeout must be 10 to 600 seconds")
    request=effect_request(song_id,effect,amount)
    screening=any(v is not None for v in (lyrics,baseline_asr,language)) or confirm_recognition
    if screening and not (lyrics is not None and baseline_asr is not None and language and confirm_recognition and confirm):
        raise ValueError("Screening requires lyrics, baseline ASR, language and both confirmations")
    if screening:
        reference_path=Path(lyrics).resolve(strict=True)
        baseline_path=Path(baseline_asr).resolve(strict=True)
        reference=reference_path.read_text(encoding="utf-8-sig")
        baseline=_recognition(json.loads(baseline_path.read_text(encoding="utf-8-sig")))
        assess(reference,baseline,language)
        input_hashes=(_sha(reference_path),_sha(baseline_path))
    client=Client(configured_endpoint(url),timeout=30).connect()
    source_hash=_sha(source)
    work=preflight(client,source,request)
    if screening:
        recognition_preflight(client)
    if out==work.resolve() or work.resolve() in out.parents:
        raise ValueError("Output must be outside Studio processing workspace")
    if _sha(source)!=source_hash:
        raise ValueError("Source changed during preflight")
    if not confirm:
        return {"status":"preflight_passed","effect":effect,"processing_calls":0,
                "audio_jobs_created":0,"recognition_calls":0,"library_mutations":0}
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ValueError("FFmpeg and ffprobe are required for preview QA")
    out.mkdir(parents=True,exist_ok=False)
    submission={"state":"SUBMITTING","request":request,"source_sha256":source_hash}
    if screening:
        submission["screening"]={"language":language,"lyrics_sha256":input_hashes[0],
                                 "baseline_asr_sha256":input_hashes[1]}
    _write(out/"submission.json",submission)
    # No retry. A failure after this call is an uncertain submission.
    receipt=unpack(client.call("processing_start",request))
    _write(out/"receipt.json",receipt)
    if not isinstance(receipt,dict) or receipt.get("error"):
        raise ValueError("Native preview submission receipt uncertain; never retry blindly")
    deadline=time.monotonic()+timeout
    run_id=None
    while time.monotonic()<deadline:
        run=_run(unpack(client.call("processing_get",{})))
        first=run_id is None
        run_id=_verify_run(run,request,run_id)
        if first:
            _write(out/"run_identity.json",{"run_id":run_id,"request":request})
        if run["error"] is not None:
            raise ValueError("Native processing reported failure")
        if run["done"]:
            if not run["preview_ready"]:
                raise ValueError("Run completed without preview")
            break
        time.sleep(1)
    else:
        raise ValueError("Preview deadline exceeded; inspect existing run, never retry blindly")
    # Upstream workspace is source media/processing; no guessed filename.
    entries=list(work.iterdir()) if work.is_dir() and not work.is_symlink() else []
    if len(entries)!=1 or not entries[0].is_file() or entries[0].is_symlink() or entries[0].suffix.lower()!=".flac":
        raise ValueError("Cannot identify one new native FLAC preview in the exclusive workspace")
    path=entries[0]
    sha=_sha(path)
    target=out/"preview.flac"
    with path.open("rb") as f,target.open("xb") as g:
        shutil.copyfileobj(f,g)
    current=_run(unpack(client.call("processing_get",{})))
    _verify_run(current,request,run_id)
    if not current["done"] or not current["preview_ready"] or current["error"] is not None or _sha(path)!=sha or _sha(target)!=sha or _sha(source)!=source_hash:
        raise ValueError("Source or preview changed during capture")
    acoustic=compare(source,target)
    a,b=acoustic["arms"]["A"],acoustic["arms"]["B"]
    passed=(a["duration_seconds"]==b["duration_seconds"]
            and a["sample_rate_hz"]==b["sample_rate_hz"] and a["channels"]==b["channels"]
            and b["true_peak_dbtp"] is not None and b["true_peak_dbtp"]<=-1.0
            and a["integrated_lufs"] is not None and b["integrated_lufs"] is not None
            and abs(a["integrated_lufs"]-b["integrated_lufs"])<=1.0)
    report={"status":"preview_acoustic_pass" if passed else "preview_acoustic_blocked",
            "run_id":run_id,"request":request,"source_sha256":source_hash,"preview_sha256":sha,
            "acoustic":acoustic,"processing_calls":1,"audio_jobs_created":0,"recognition_calls":0,
            "library_mutations":0,"automatic_acceptance":False,"naturalness_verified":False,
            "warnings":["Preview identification relies on exclusive workspace use and observed run identity.",
                        "Pending Studio preview is deliberately retained; no keep/discard.",
                        "Baseline ASR provenance/settings are operator-supplied; ASR is not verified sung fidelity."]}
    _write(out/"report.json",report)
    if not screening or not passed:
        return report
    # Keep the preview/acoustic report even when recognition fails. No blind retry.
    evaluation={"status":"screening_pending","processing_run_id":run_id,"recognition_calls":0,
                "automatic_acceptance":False,"naturalness_verified":False,"library_mutations":0}
    try:
        if (_sha(reference_path),_sha(baseline_path))!=input_hashes or _sha(target)!=sha or _sha(source)!=source_hash:
            raise ValueError("Screening inputs changed")
        receipt=capture(target,out/"recognition",url,confirm=True,pending_processing=current)
        evaluation["recognition_calls"]=receipt["recognition_calls"]
        observed=_recognition(json.loads((out/"recognition/recognition.json").read_text(encoding="utf-8")))
        latest=_run(unpack(client.call("processing_get",{})))
        if latest!=current or _sha(target)!=sha or _sha(source)!=source_hash or (_sha(reference_path),_sha(baseline_path))!=input_hashes:
            raise ValueError("Preview transaction or screening inputs changed")
        screen=compare_text(reference,baseline,observed,language)
        evaluation["lyric_screen"]=screen
        evaluation["status"]="retain_original_asr_regression" if screen["status"]=="regression" else "candidate_nonregression_unverified"
        evaluation["provisional_output"]=str(source if screen["status"]=="regression" else target)
    except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
        evaluation["status"]="screening_blocked"
        evaluation["reason"]=str(exc)
        if (out/"recognition/submission.json").exists() and not evaluation["recognition_calls"]:
            evaluation["recognition_calls"]="unknown_after_submission"
    _write(out/"evaluation.json",evaluation)
    return {**report,"evaluation":evaluation,"recognition_calls":evaluation["recognition_calls"]}


def inspect_preview(out, source):
    """Read existing evidence only. Never contact Studio or retry uncertain work."""
    out=Path(out).resolve(strict=True)
    source=Path(source).resolve(strict=True)
    def load(name):
        path=out/name
        if not path.is_file():
            return None
        data=json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data,dict):
            raise ValueError("Invalid transaction record: "+name)
        return data
    submission=load("submission.json")
    if submission is None or submission.get("state")!="SUBMITTING" or _sha(source)!=submission.get("source_sha256"):
        raise ValueError("Missing submission or original source no longer matches")
    receipt=load("receipt.json")
    identity=load("run_identity.json")
    report=load("report.json")
    evaluation=load("evaluation.json")
    marker=load("recognition/submission.json")
    recognition_receipt=load("recognition/receipt.json")
    status={"schema":"native-preview-inspect-v1","processing_calls":0,"recognition_calls":0,
            "library_mutations":0,"automatic_acceptance":False,"naturalness_verified":False,
            "retry_allowed":False,"submission_recorded":True,"receipt_recorded":receipt is not None,
            "run_id":identity.get("run_id") if identity else None,
            "provisional_output":str(source)}
    if report is None:
        status["status"]="processing_outcome_unverified"
        return status
    target=out/"preview.flac"
    if (report.get("source_sha256")!=submission["source_sha256"]
            or report.get("request")!=submission["request"]
            or identity is None or report.get("run_id")!=identity.get("run_id")
            or identity.get("request")!=submission["request"]
            or not target.is_file() or _sha(target)!=report.get("preview_sha256")):
        raise ValueError("Preview evidence does not match recorded transaction")
    status["status"]=report.get("status")
    if marker is not None:
        status["prior_recognition_state"]="response_received" if recognition_receipt else "unknown_after_submission"
        if marker.get("audio_sha256")!=report["preview_sha256"] or (recognition_receipt and
                recognition_receipt.get("audio_sha256")!=report["preview_sha256"]):
            raise ValueError("Recognition receipt does not match preview")
    if evaluation is not None:
        if evaluation.get("processing_run_id")!=report["run_id"]:
            raise ValueError("Evaluation does not match preview run")
        status["status"]=evaluation.get("status")
        if (status["status"]=="candidate_nonregression_unverified" and report["status"]=="preview_acoustic_pass"
                and recognition_receipt and recognition_receipt.get("state")=="RESPONSE_RECEIVED"
                and marker and evaluation.get("lyric_screen",{}).get("status") in ("improved","unchanged")):
            status["provisional_output"]=str(target)
    elif marker is not None:
        status["status"]="recognition_outcome_unverified"
    elif report["status"]=="preview_acoustic_pass":
        status["status"]="preview_acoustic_pass_unscreened"
    return status
