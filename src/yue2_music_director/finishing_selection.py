"""Compare completed finishing experiments, not artistic quality or new inference."""
import json
import math
from pathlib import Path

from .native_recognition import _sha, _write, _recognition
from .multilingual_fidelity import compare, assess
from .native_headroom import gain_plan, corrected_pass


def read(path):
    data=json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data,dict):
        raise ValueError("Expected JSON object")
    return data


def receipt(directory, digest):
    marker=read(directory/"submission.json")
    response=read(directory/"receipt.json")
    if (marker.get("state")!="SUBMITTING" or response.get("state")!="RESPONSE_RECEIVED"
            or marker.get("audio_sha256")!=digest or response.get("audio_sha256")!=digest
            or marker.get("provider")!="whisper" or marker.get("language_requested") is not None):
        raise ValueError("Recognition receipt does not match candidate and automatic detection")
    return _recognition(read(directory/"recognition.json"))


def metrics(acoustic, source_hash, candidate_hash):
    a,b=acoustic["arms"]["A"],acoustic["arms"]["B"]
    if a["sha256"]!=source_hash or b["sha256"]!=candidate_hash:
        raise ValueError("Acoustic report hashes differ")
    for arm in (a,b):
        for key in ("duration_seconds","sample_rate_hz","channels","integrated_lufs","true_peak_dbtp"):
            if type(arm[key]) not in (float,int) or not math.isfinite(arm[key]):
                raise ValueError("Invalid acoustic metric")
        if arm["duration_seconds"]<=0 or arm["sample_rate_hz"]<=0 or arm["channels"] not in (1,2):
            raise ValueError("Invalid acoustic format")
    if any(a[k]!=b[k] for k in ("sample_rate_hz","channels")) or abs(a["duration_seconds"]-b["duration_seconds"])>1/a["sample_rate_hz"]:
        raise ValueError("Candidate format or duration differs")
    return a,b


def select(source, lyrics, baseline_asr, language, out, *, custom=None, native=None):
    """Offline report only. Existing local evidence is trusted, not cryptographically authenticated."""
    source,lyrics,baseline_asr=[Path(p).resolve(strict=True) for p in (source,lyrics,baseline_asr)]
    out=Path(out).resolve()
    if out.exists() or (custom is None and native is None):
        raise ValueError("Fresh report path and at least one candidate directory required")
    sh,lh,bh=(_sha(p) for p in (source,lyrics,baseline_asr))
    reference=lyrics.read_text(encoding="utf-8-sig")
    baseline=_recognition(read(baseline_asr))
    score=assess(reference,baseline,language)
    primary=score["primary_metric"]
    rows=[]
    for kind,folder in (("custom_instrument_dynamics",custom),("native_headroom",native)):
        if folder is None:
            continue
        row={"method":kind,"eligible":False}
        try:
            d=Path(folder).resolve(strict=True)
            if kind=="custom_instrument_dynamics":
                report=read(d/"report.json")
                target=d/"dynamics/candidate.flac"
                digest=_sha(target)
                hashes=report["source_sha256"]
                if (report.get("schema")!="finish-existing-v1" or
                        (hashes["mix"],hashes["lyrics"],hashes["baseline_asr"])!=(sh,lh,bh)
                        or report["language"]!=language or report["candidate_sha256"]!=digest
                        or report["dynamics_status"]!="candidate_created"):
                    raise ValueError("Custom transaction fingerprints do not match")
                dynamics=read(d/"dynamics/report.json")
                if dynamics["status"]!="candidate_created" or dynamics["source_sha256"]["mix"]!=sh:
                    raise ValueError("Custom dynamics report differs")
                acoustic=dynamics["acoustic"]
                raw_a,raw_b=metrics(acoustic,sh,digest)
                if abs(raw_b["integrated_lufs"]-raw_a["integrated_lufs"])>1:
                    raise ValueError("Custom loudness guard failed")
                recognition=d/"recognition"
            else:
                parent=read(d/"report.json")
                submission=read(d/"submission.json")
                identity=read(d/"run_identity.json")
                c=d/"headroom-continuation"
                report=read(c/"report.json")
                plan=read(c/"plan.json")
                target=c/"candidate.flac"
                digest=_sha(target)
                raw_digest=_sha(d/"preview.flac")
                expected={"language":language,"lyrics_sha256":lh,"baseline_asr_sha256":bh}
                if (submission["state"]!="SUBMITTING" or submission["source_sha256"]!=sh
                        or submission["screening"]!=expected or plan["screening"]!=expected
                        or parent["source_sha256"]!=sh or plan["source_sha256"]!=sh
                        or parent["preview_sha256"]!=raw_digest or plan["raw_preview_sha256"]!=raw_digest
                        or parent["run_id"]!=plan["run_id"] or identity["run_id"]!=plan["run_id"]
                        or parent["request"]!=submission["request"] or identity["request"]!=submission["request"]
                        or parent["status"]!="preview_acoustic_blocked"):
                    raise ValueError("Native transaction fingerprints do not match")
                before=report["before"]
                metrics(before,sh,raw_digest)
                gain=gain_plan(before)
                acoustic=report["after"]
                metrics(acoustic,sh,digest)
                if plan["gain_db"]!=gain or report["gain_db"]!=gain or not corrected_pass(before,acoustic,gain):
                    raise ValueError("Native gain correction guard failed")
                recognition=c/"recognition"
            a,b=metrics(acoustic,sh,digest)
            if report["status"] not in ("candidate_nonregression_unverified","retain_original_asr_regression") or report["recognition_calls"]!=1:
                raise ValueError("Missing completed screening")
            screen=compare(reference,baseline,receipt(recognition,digest),language)
            if report["lyric_screen"]!=screen:
                raise ValueError("Recorded lyric screen differs from recomputed evidence")
            row.update({"path":str(target),"sha256":digest,"lyric_screen":screen,
                        "true_peak_dbtp":b["true_peak_dbtp"],"integrated_lufs":b["integrated_lufs"],
                        "headroom_pass":b["true_peak_dbtp"]<=-1.0})
            if screen["status"]=="regression" or report["status"]!="candidate_nonregression_unverified":
                row["reason"]="asr_regression"
            elif not row["headroom_pass"]:
                row["reason"]="insufficient_headroom"
            else:
                row["eligible"]=True
        except (ValueError,OSError,KeyError,TypeError) as exc:
            row["reason"]="evidence_invalid"
            row["detail"]=str(exc)
        rows.append(row)
    eligible=[row for row in rows if row["eligible"]]
    # Rank only among technical passes by primary ASR metric; equal evidence is a tie.
    best=min((row["lyric_screen"]["arms"]["candidate"][primary]["edits"] for row in eligible),default=None)
    winners=[row for row in eligible if row["lyric_screen"]["arms"]["candidate"][primary]["edits"]==best]
    result={"schema":"finishing-selection-v1","source_sha256":sh,"lyrics_sha256":lh,"baseline_asr_sha256":bh,
            "baseline":score,"candidates":rows,"status":"provisional_candidate" if len(winners)==1 else
            "tie_no_unique_candidate" if winners else "retain_original_no_eligible_candidate",
            "provisional_output":winners[0]["path"] if len(winners)==1 else str(source),
            "automatic_acceptance":False,"naturalness_verified":False,"audio_jobs_created":0,
            "recognition_calls":0,"processing_calls":0,"library_mutations":0,
            "warnings":["Offline selection uses recorded measurements and checks hashes, not fresh acoustic measurements.",
                        "Baseline recognition provenance remains operator-supplied. ASR is not a musical quality ranking.",
                        "The source is a fallback, not a certificate of release-ready headroom.",
                        "A tie retains the source; no forced additional processing."]}
    if (_sha(source),_sha(lyrics),_sha(baseline_asr))!=(sh,lh,bh) or any(_sha(Path(row["path"]))!=row["sha256"] for row in rows if "sha256" in row):
        raise ValueError("Selection inputs changed")
    out.parent.mkdir(parents=True,exist_ok=True)
    _write(out,result)
    return result
