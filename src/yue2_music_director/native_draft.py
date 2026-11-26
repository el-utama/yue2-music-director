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


def verify_native_directed_layout(abc):
    """Conservative subset of pinned Studio abc::parse for authored scores."""
    import re
    lines=abc.splitlines()
    voices=('V: Vocal clef=treble name="Vocal Melody" snm="Vocal"',
            'V: Ins clef=treble name="Ins Melody" snm="Inst."')
    if (len(lines)<12 or lines[:2]!=["X:1","T:"] or tuple(lines[5:7])!=voices
            or not re.fullmatch(r"M:[1-9][0-9]*/[1-9][0-9]*",lines[2])
            or not re.fullmatch(r"L:1/(?:4|8|16|32)",lines[3])
            or not re.fullmatch(r"Q:1/4=[1-9][0-9]*",lines[4])
            or not lines[7].startswith("K:")):
        raise ValueError("Directed score failed native layout: expected exact eight-line native header")
    i=8
    while i<len(lines):
        if lines[i].startswith("% "):
            i+=1
        if i+3>=len(lines) or lines[i]!="V: Vocal" or lines[i+2]!="V: Ins":
            raise ValueError("Directed score failed native layout: expected paired Vocal/Ins group")
        counts=[]
        for line in (lines[i+1],lines[i+3]):
            if not line.endswith("|") or any(not b.strip() for b in line[:-1].split("|")):
                raise ValueError("Directed score failed native layout: invalid barlines")
            count=0
            for bar in line[:-1].split("|"):
                rest=re.fullmatch(r"Z([2-4])?",bar.strip())
                count+=int(rest[1] or 1) if rest else 1
            counts.append(count)
        if counts[0]!=counts[1] or not 1<=counts[0]<=4:
            raise ValueError("Directed score failed native layout: groups require 1–4 equal bars")
        i+=4
    # The local structural parser permits arbitrary numeric durations. Native
    # only allows the following token lengths; native MIDI is still the authority.
    from .music import parse_score
    score=parse_score(abc)
    for e in score.events:
        if e.kind!="multirest" and e.duration not in (1,2,3,4,6,8,12,16,24,32,48):
            raise ValueError("Directed score failed native layout: unsupported note/rest duration")


def verify_directed_score(abc,brief):
    # Lazy import: generation_control reuses this module's brief helpers.
    from .generation_control import inspect_plan
    review=inspect_plan(abc,brief)
    if not review["eligible_for_render"]:
        raise ValueError("Directed score failed structural review: "+repr(review))
    verify_native_directed_layout(abc)
    return review


def score_signature(abc, *, native=False):
    from .music import parse_score
    score=parse_score(abc,native=native)
    return (tuple(score.headers.get(k) for k in ("M","L","K","Q")),
            score.sections,score.bar_chords,
            [(e.voice,e.bar,e.section,e.kind,e.offset,e.duration,e.pitch,e.tied) + ((e.chord,) if native else ())
             for e in sorted(score.events,key=lambda e:(e.voice,e.bar,e.offset))])


def verify_saved_directed_score(saved,abc,song_id,job_id,brief,*,native=False):
    if (saved.get("id")!=song_id or not isinstance(saved.get("metadata"),dict)
            or saved["metadata"].get("job_id")!=job_id):
        raise ValueError("Directed song provenance mismatch")
    settings=saved.get("generation_settings")
    if (not isinstance(settings,dict) or settings.get("cot")!="full"
            or settings.get("lyrics")!=brief["lyrics"]
            or not isinstance(settings.get("abc"),str)
            or score_signature(settings["abc"],native=native)!=score_signature(abc,native=native)):
        raise ValueError("Saved directed score or lyrics differ; retain song, do not regenerate")


def execute(brief,root,url,*,max_waits=20,restore_stock=False,abc=None,artist=None,expected_configuration=None):
    request=request_for(brief)
    if artist is not None:
        from .artist_run import evaluate_plan, route_for
        route=route_for(artist)
        if (route=="direct_native")!=(abc is None):
            raise ValueError("Artistic route and score presence differ")
        if restore_stock:
            raise ValueError("Artistic run cannot change model selection")
        if abc is not None:
            review=evaluate_plan(abc,brief,artist)
            if review["decision"]!="retain":
                raise ValueError("Native plan is not cleared for synthesis")
            if expected_configuration is None and route=="reviewed_native":
                raise ValueError("Reviewed native route requires retained planner configuration")
    elif abc is not None:
        review=verify_directed_score(abc,brief)
    if abc is not None:
        request["abc"]=abc
    request_sha=digest(_canonical(request))
    brief_sha=digest(_canonical(brief))
    if not root.exists():
        root.mkdir(parents=True,exist_ok=False)
        atomic_write(root/"brief.json",brief)
        atomic_write(root/"request.json",request)
    elif read(root/"brief.json")!=brief or read(root/"request.json")!=request:
        raise ValueError("Retained draft does not match current brief")
    if artist is not None:
        policy={"intent":artist,"planner_configuration":expected_configuration}
        policy_path=root/"artist-policy.json"
        if policy_path.exists():
            if read(policy_path)!=policy:
                raise ValueError("Retained artistic policy differs")
        elif (root/"journal_song.json").exists() or (root/"report.json").exists():
            raise ValueError("Existing draft lacks artistic policy identity")
        else:
            atomic_write(policy_path,policy)
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
        if expected_configuration is not None and journal.get("reference_configuration")!=expected_configuration:
            raise ValueError("Retained synthesis configuration differs from planner")
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
        if expected_configuration is not None and configuration!=expected_configuration:
            raise ValueError("Native configuration changed after score planning")
        if abc is not None:
            from .midi import extract_midi,midi_header
            if "abc" not in tools["score_to_midi"].get("properties",{}):
                raise ValueError("Native MIDI tool schema mismatch")
            response=client.call("score_to_midi",{"abc":abc})
            atomic_write(root/"score-midi-response.json",response)
            midi=midi_header(extract_midi(response))
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
    if abc is not None or artist is not None:
        from .temporal_evidence import native_song_read
        saved=native_song_read(url,song_id)
        if abc is not None:
            verify_saved_directed_score(saved,abc,song_id,job_id,brief,native=artist is not None)
            print("Saved native score and lyric conditioning verified.",flush=True)
        else:
            if (not isinstance(saved,dict) or saved.get("id")!=song_id
                    or not isinstance(saved.get("metadata"),dict) or saved["metadata"].get("job_id")!=job_id):
                raise ValueError("Saved native song provenance mismatch")
            settings=saved.get("generation_settings")
            if not isinstance(settings,dict) or settings.get("cot")!="full" or settings.get("lyrics")!=brief["lyrics"]:
                raise ValueError("Saved native lyric conditioning differs")
        if artist is not None:
            saved_abc=saved["generation_settings"].get("abc")
            if isinstance(saved_abc,str) and saved_abc.strip():
                saved_path=root/"saved-score.abc"
                if saved_path.exists():
                    if saved_path.read_bytes()!=saved_abc.encode("utf-8"):
                        raise ValueError("Retained saved native score changed")
                else:
                    with saved_path.open("xb") as stream:
                        stream.write(saved_abc.encode("utf-8"))
                from .musical_review import review_score
                post_review=review_score(saved_abc,brief["lyrics"],constraints=artist["constraints"],
                                         max_seconds=brief["duration_seconds"])
            else:
                post_review={"status":"unassessable","reason":"Saved native ABC unavailable",
                             "render_authorized":False}
            atomic_write(root/"saved-score-review.json",post_review)
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
    if artist is not None:
        report["generation_path"]=route
        report["artistic_intent"]=artist
        report["saved_score_review"]=read(root/"saved-score-review.json")
        report["listening_verdict"]="unrated"
        report["artistic_acceptance"]="unverified"
        report["budget"]=artist["budget"]
        report["actual_lyric_conditioning_verified"]=True
    if abc is not None:
        if artist is None:
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
    choices=parser.add_mutually_exclusive_group()
    choices.add_argument("--director-demo",action="store_true",help="Use the original research brief and precomposed score")
    choices.add_argument("--artist-demo",action="store_true",help="Original generation-first artistic study")
    choices.add_argument("--artist",action="store_true",help="Use local brief and artistic intent")
    parser.add_argument("--select-stock",action="store_true",help="Explicitly clear own-model override before a new draft")
    args=parser.parse_args()
    try:
        repo=args.repo.resolve()
        if args.artist or args.artist_demo:
            if args.select_stock:
                raise ValueError("Artistic run does not change model selection")
            from .artist_run import launch
            return launch(repo,args.url,confirm=args.confirm_run,demo=args.artist_demo)
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
