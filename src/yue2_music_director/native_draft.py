"""One native reference draft from a private brief; no speculative corrections."""
import argparse
import json
import math
import os
import shutil
import sys
from pathlib import Path

from .acoustic import _measure
from .experiments import _canonical, _sha as digest, _write as atomic_write, reference_configuration
from .job_receipt import extract_song_job_id
from .mcp import Client, configured_endpoint, unpack, MCPError
from .multilingual_fidelity import SUPPORTED, assess
from .native_recognition import _sha, _recognition, capture, recognition_preflight
from .prosody import parse_lyrics
from .stock_selection import select_stock


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_brief(path):
    if path.stat().st_size > 100_000:
        raise ValueError("Brief exceeds size limit")
    brief=read(path)
    keys={"title","style","lyrics","language","seed","duration_seconds"}
    if not isinstance(brief,dict) or set(brief)!=keys:
        raise ValueError("Brief requires title, style, lyrics, language, seed, duration_seconds")
    for key,limit in (("title",150),("style",2000),("lyrics",20000)):
        if not isinstance(brief[key],str) or not brief[key].strip() or len(brief[key])>limit:
            raise ValueError("Invalid brief field: "+key)
    if not isinstance(brief["language"],str) or brief["language"] not in SUPPORTED:
        raise ValueError("Unsupported text-screen language")
    if type(brief["seed"]) is not int or not 0<=brief["seed"]<2**31:
        raise ValueError("Seed must be a nonnegative 31-bit integer")
    if type(brief["duration_seconds"]) is not int or not 30<=brief["duration_seconds"]<=240:
        raise ValueError("Draft generation cap must be 30–240 seconds")
    if not any(group["lines"] for group in parse_lyrics(brief["lyrics"])):
        raise ValueError("Tagged vocal lyrics required")
    return brief


def request_for(brief):
    return {"music_source":{"kind":"local"},"title":brief["title"],
            "style":brief["style"],"lyrics":brief["lyrics"],"cot":"full",
            "duration_seconds":brief["duration_seconds"],"output_format":"flac",
            "seed":brief["seed"],"lm_seed":brief["seed"],"abc_continue":False,
            "lyric_timing":True,"lm_batch_size":1,"synth_batch_size":1,
            "adapters":[],"companion_scale":0}


def create_journal(path,journal):
    # Persist the attempt before the irreversible POST. No retry on ambiguity.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        json.dump(journal,f,indent=2)
        f.flush()
        os.fsync(f.fileno())


def verify_completed_settings(job,brief):
    # Upstream yue_request_from only inserts adapters for a non-empty
    # request; compact_job serializes the missing field as JSON null.
    for key in ("seed","lm_seed"):
        if type(job.get(key)) is not int or job[key]!=brief["seed"]:
            raise ValueError("Completed job seed mismatch: "+key+"="+repr(job.get(key)))
    if "adapters" not in job or job["adapters"] not in (None,[]):
        raise ValueError("Completed job does not confirm disabled adapters")


def verify_directed_score(abc,brief):
    # Lazy import: generation_control reuses this module's brief helpers.
    from .generation_control import inspect_plan
    review=inspect_plan(abc,brief)
    if not review["eligible_for_render"]:
        raise ValueError("Directed score failed structural review: "+repr(review))
    return review


def score_signature(abc):
    from .music import parse_score
    score=parse_score(abc)
    return (tuple(score.headers.get(k) for k in ("M","L","K","Q")),
            score.sections,score.bar_chords,
            [(e.voice,e.bar,e.section,e.kind,e.offset,e.duration,e.pitch,e.tied)
             for e in score.events])


def verify_saved_directed_score(saved,abc,song_id,job_id,brief):
    if (saved.get("id")!=song_id or not isinstance(saved.get("metadata"),dict)
            or saved["metadata"].get("job_id")!=job_id):
        raise ValueError("Directed song provenance mismatch")
    settings=saved.get("generation_settings")
    if (not isinstance(settings,dict) or settings.get("cot")!="full"
            or settings.get("lyrics")!=brief["lyrics"]
            or not isinstance(settings.get("abc"),str)
            or score_signature(settings["abc"])!=score_signature(abc)):
        raise ValueError("Saved directed score or lyrics differ; retain song, do not regenerate")


def execute(brief,root,url,*,max_waits=20,restore_stock=False,abc=None):
    request=request_for(brief)
    if abc is not None:
        review=verify_directed_score(abc,brief)
        request["abc"]=abc
    request_sha=digest(_canonical(request))
    brief_sha=digest(_canonical(brief))
    if not root.exists():
        root.mkdir(parents=True,exist_ok=False)
        atomic_write(root/"brief.json",brief)
        atomic_write(root/"request.json",request)
    elif read(root/"brief.json")!=brief or read(root/"request.json")!=request:
        raise ValueError("Retained draft does not match current brief")
    report_path=root/"report.json"
    if report_path.exists():
        report=read(report_path)
        if report["brief_sha256"]!=brief_sha or report["request_sha256"]!=request_sha:
            raise ValueError("Saved report identity differs")
        audio=Path(report["audio"])
        if _sha(audio)!=report["audio_sha256"]:
            raise ValueError("Saved draft audio changed")
        return report
    ffmpeg,ffprobe=shutil.which("ffmpeg"),shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise ValueError("FFmpeg and ffprobe required before generation")
    client=Client(configured_endpoint(url),timeout=90).connect()
    tools={t["name"]:t.get("inputSchema",{}) for t in client.tools()}
    required={"song_create","song_job_get","studio_wait","library_song_files",
              "studio_status","song_defaults","studio_capabilities","models_status",
              "engine_options_get"}
    if not required<=tools.keys():
        raise ValueError("Native draft capabilities missing")
    if abc is not None and "score_to_midi" not in tools:
        raise ValueError("Native score compatibility tool unavailable")
    journal_path=root/"journal_song.json"
    if journal_path.exists():
        journal=read(journal_path)
        if journal.get("request_sha256")!=request_sha or journal.get("brief_sha256")!=brief_sha:
            raise ValueError("Journal identity differs")
        if journal.get("state") not in ("SUBMITTED","COMPLETED") or not journal.get("job_id"):
            raise ValueError("Previous submission outcome unknown; inspect Studio, never resubmit")
    else:
        schema=tools["song_create"]
        if not set(request)<=set(schema.get("properties",{})) or not set(schema.get("required",[]))<=set(request):
            raise ValueError("Song request does not fit advertised schema")
        recognition_preflight(client)
        if restore_stock:
            select_stock(client,tools)
        defaults=unpack(client.call("song_defaults",{}))
        capabilities=unpack(client.call("studio_capabilities",{}))
        status=unpack(client.call("studio_status",{}))
        configuration=reference_configuration(client,status,request,defaults,capabilities)
        if abc is not None:
            from .midi import extract_midi,midi_header
            if "abc" not in tools["score_to_midi"].get("properties",{}):
                raise ValueError("Native MIDI tool schema mismatch")
            midi=midi_header(extract_midi(client.call("score_to_midi",{"abc":abc})))
            atomic_write(root/"score-review.json",{"structural_review":review,"midi":midi,
                         "score_sha256":digest(abc.encode("utf-8"))})
            print("Directed score: structural and native MIDI compatibility passed.",flush=True)
        journal={"state":"SUBMISSION_ATTEMPTED","brief_sha256":brief_sha,
                 "request_sha256":request_sha,"reference_configuration":configuration}
        create_journal(journal_path,journal)
        print("Submitting one native song...",flush=True)
        raw=client.call("song_create",request)
        atomic_write(root/"submission-response.json",raw)
        job_id=extract_song_job_id(raw)
        if not job_id:
            raise ValueError("No unambiguous job ID; do not resubmit")
        journal.update(state="SUBMITTED",job_id=job_id)
        atomic_write(journal_path,journal)
    job_id=journal["job_id"]
    for attempt in range(max_waits+1):
        job=unpack(client.call("song_job_get",{"job_id":job_id,"response_format":"concise"}))
        if not isinstance(job,dict) or job.get("id")!=job_id:
            raise ValueError("Job response identity mismatch")
        state=job.get("status")
        print("Native job status:",state,flush=True)
        if state=="completed":
            break
        if state not in ("queued","running") or attempt==max_waits:
            raise ValueError("Job not completed in bounded wait; retain journal, resume only known job")
        client.call("studio_wait",{"job_id":job_id,"seconds":45})
    verify_completed_settings(job,brief)
    songs=job.get("songs")
    if (not isinstance(songs,list) or len(songs)!=1 or not isinstance(songs[0],dict)
            or not isinstance(songs[0].get("id"),str) or not songs[0]["id"]):
        raise ValueError("Expected exactly one completed library song")
    song_id=songs[0]["id"]
    files=unpack(client.call("library_song_files",{"song_id":song_id}))
    if not isinstance(files,dict) or not isinstance(files.get("audio"),str):
        raise ValueError("Completed song audio unavailable")
    audio=Path(files["audio"])
    if not audio.is_absolute() or audio.suffix.lower()!=".flac" or not audio.is_file():
        raise ValueError("Expected existing absolute native FLAC")
    audio=audio.resolve(strict=True)
    audio_sha=_sha(audio)
    if journal["state"]=="COMPLETED":
        if journal.get("song_id")!=song_id or journal.get("audio_sha256")!=audio_sha:
            raise ValueError("Completed audio identity changed")
    else:
        journal.update(state="COMPLETED",song_id=song_id,audio_sha256=audio_sha)
        atomic_write(journal_path,journal)
    if abc is not None:
        from .temporal_evidence import native_song_read
        verify_saved_directed_score(native_song_read(url,song_id),abc,song_id,job_id,brief)
        print("Saved native score and lyric conditioning verified.",flush=True)
    print("Measuring existing native draft...",flush=True)
    acoustic_path=root/"acoustic.json"
    if acoustic_path.exists():
        acoustic=read(acoustic_path)
    else:
        acoustic=_measure(audio,ffmpeg,ffprobe)
        atomic_write(acoustic_path,acoustic)
    if acoustic["sha256"]!=audio_sha:
        raise ValueError("Acoustic evidence identity differs")
    recognition=root/"recognition"
    if not recognition.exists():
        print("Running one authorized local lyric recognition...",flush=True)
        capture(audio,recognition,url,confirm=True,language=brief["language"])
    receipt=read(recognition/"receipt.json")
    submission=read(recognition/"submission.json")
    if (receipt.get("state")!="RESPONSE_RECEIVED" or receipt.get("audio_sha256")!=audio_sha
            or submission.get("audio_sha256")!=audio_sha
            or submission.get("provider")!="whisper"
            or submission.get("language_requested")!=brief["language"]):
        raise ValueError("Recognition evidence incomplete or mismatched; never retry")
    raw=read(recognition/"recognition.json")
    screen=assess(brief["lyrics"],_recognition(raw),brief["language"])
    peak=acoustic.get("true_peak_dbtp")
    loudness=acoustic.get("integrated_lufs")
    peak_pass=(type(peak) in (int,float) and math.isfinite(peak) and peak<=-1
               and type(loudness) in (int,float) and math.isfinite(loudness) and loudness>-70)
    if _sha(audio)!=audio_sha:
        raise ValueError("Audio changed during draft QA")
    duration=acoustic.get("duration_seconds")
    duration_pass=type(duration) in (int,float) and math.isfinite(duration) and 0<duration<=brief["duration_seconds"]+2
    report={"schema":"native-draft-v1","status":"provisional_draft" if peak_pass and duration_pass else "technical_review_required",
            "brief_sha256":brief_sha,"request_sha256":request_sha,"audio":str(audio),
            "audio_sha256":audio_sha,"job_id":job_id,"song_id":song_id,
            "acoustic":acoustic,"lyric_screen":screen,"headroom_pass":peak_pass,"duration_cap_screen_pass":duration_pass,
            "budget":{"song_jobs":1,"recognition_calls":1},
            "automatic_acceptance":False,"naturalness_verified":False,
            "phonetic_alignment_verified":False,"next_action":"retain_draft_and_stop",
            "warnings":["Single take, no musical winner or validated pronunciation.",
                        "Duration is a generation cap, not guaranteed song length.",
                        "Reference policy is stock Balanced only, not a universal model preference.",
                        "No automatic regeneration, finishing, export, or further model changes."]}
    if abc is not None:
        report["generation_path"]="director_authored_score"
        report["saved_score_verified"]=True
        report["score_review"]=read(root/"score-review.json")
    atomic_write(report_path,report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--url",required=True)
    parser.add_argument("--confirm-run",action="store_true")
    parser.add_argument("--director-demo",action="store_true",help="Use the original research brief and precomposed score")
    parser.add_argument("--select-stock",action="store_true",help="Explicitly clear own-model override before a new draft")
    args=parser.parse_args()
    try:
        repo=args.repo.resolve()
        abc=None
        if args.director_demo:
            if args.select_stock:
                raise ValueError("Directed demo does not change model selection")
            example=repo/"examples/director-demo"
            brief=load_brief(example/"brief.json")
            abc=(example/"score.abc").read_text(encoding="utf-8")
            review=verify_directed_score(abc,brief)
            key="directed-"+digest(_canonical({"brief":brief,"abc":abc}))
            print("Director composition:",brief["title"],"| planned seconds:",round(review["score_seconds"],2),flush=True)
        else:
            brief=load_brief(repo/"local/brief.json")
            key=digest(_canonical(brief))
        if args.select_stock and not args.confirm_run:
            raise ValueError("Stock selection requires explicit --confirm-run")
        if not args.confirm_run:
            print("Plan only: one native stock Balanced draft, one local Whisper recognition." if abc is None else "Plan only: validated director-authored score, native MIDI check, one new song and one local recognition.")
            print("No GPU job authorized. Use --confirm-run only to approve both operations.")
            return 0
        drafts=repo/"results/drafts"
        drafts.mkdir(parents=True,exist_ok=True)
        lock=drafts/".active"
        fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(fd)
        try:
            report=execute(brief,drafts/key,args.url,restore_stock=args.select_stock,abc=abc)
        finally:
            lock.unlink()
        metric=report["lyric_screen"]["primary_metric"]
        print("Draft:",report["status"])
        print("True peak:",report["acoustic"]["true_peak_dbtp"],"dBTP")
        print(metric,"disagreement:",report["lyric_screen"][metric]["disagreement_rate"])
        print("Local audio:",report["audio"])
        print("Automatic acceptance: false")
        return 0
    except (ValueError,OSError,KeyError,TypeError,MCPError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
