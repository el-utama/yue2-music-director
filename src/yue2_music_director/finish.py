"""One bounded postproduction pass; no song generation or source mutation."""
import json
from pathlib import Path
from .acoustic import _hash
from .instrument_dynamics import process
from .native_recognition import capture, _recognition
from .multilingual_fidelity import compare, assess


def finish(mix, instrumental, vocals, lyrics, baseline_asr, out, language,
           *, url=None, confirm=False, max_db=2.0):
    if not confirm:
        raise ValueError("Explicit --confirm-recognition required for at most one new local ASR call")
    out=Path(out).resolve()
    if out.exists():
        raise ValueError("Output already exists; inspect existing reports, never retry blindly")
    sources=[Path(p).resolve(strict=True) for p in (mix,instrumental,vocals,lyrics,baseline_asr)]
    if any(not p.is_file() for p in sources):
        raise ValueError("All inputs must be files")
    hashes={k:_hash(p) for k,p in zip(("mix","instrumental","vocals","lyrics","baseline_asr"),sources)}
    reference=sources[3].read_text(encoding="utf-8-sig")
    baseline=_recognition(json.loads(sources[4].read_text(encoding="utf-8-sig")))
    score=assess(reference,baseline,language)
    out.mkdir(parents=True,exist_ok=False)
    report={"schema":"finish-existing-v1","source_sha256":hashes,"language":language,
            "baseline_text_screen":score,"status":"started","audio_jobs_created":0,
            "recognition_calls":0,"naturalness_verified":False,"automatic_acceptance":False,
            "warnings":["Baseline ASR identity/settings are operator-supplied and not independently verified.",
                        "Candidate recognition uses existing Studio configuration, with automatic language detection.",
                        "No new generation, separation or manual lyric review.",
                        "An ASR non-regression is not a certificate of correct lyrics or improved naturalness."]}
    def save():
        (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    save()
    try:
        dynamics=process(*sources[:3],out/"dynamics",max_db)
        report["dynamics_status"]=dynamics["status"]
        report["attacks_edited"]=dynamics["attacks_edited"]
        if dynamics["status"]!="candidate_created":
            report["status"]="no_candidate"
            save()
            return report
        candidate=out/"dynamics/candidate.flac"
        report["candidate"]=str(candidate)
        report["candidate_sha256"]=_hash(candidate)
        report["status"]="recognition_pending"
        save()
        receipt=capture(candidate,out/"recognition",url,confirm=True)
        report["recognition_calls"]=receipt["recognition_calls"]
        transcript=_recognition(json.loads((out/"recognition/recognition.json").read_text(encoding="utf-8")))
        screen=compare(reference,baseline,transcript,language)
        report["lyric_screen"]=screen
        report["status"]=("retain_original_asr_regression" if screen["status"]=="regression"
                          else "candidate_nonregression_unverified")
        report["provisional_output"]=str(sources[0] if screen["status"]=="regression" else candidate)
        if _hash(candidate)!=report["candidate_sha256"]:
            raise ValueError("Candidate changed during screening")
        if [_hash(p) for p in sources]!=list(hashes.values()):
            raise ValueError("Input changed during workflow")
    except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
        report.pop("provisional_output",None)
        report["status"]="blocked"
        report["reason"]=str(exc)
        if (out/"recognition/submission.json").exists() and not report["recognition_calls"]:
            report["recognition_calls"]="unknown_after_submission"
    save()
    return report
