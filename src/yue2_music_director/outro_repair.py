"""Experimental repair of a nine-bar silent Vocal outro; original remains untouched."""
import argparse
import json
import math
import re
import statistics
import sys
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
from urllib.request import Request,build_opener,ProxyHandler

from .experiments import _canonical,_sha,_write,reference_configuration
from .mcp import Client,configured_endpoint,unpack,_NoRedirect,MCPError
from .music import parse_score,patch_score
from .prosody import parse_lyrics
from .native_draft import load_brief,read,request_for,verify_completed_settings,create_journal
from .job_receipt import extract_song_job_id
from .temporal_evidence import native_song_read
from .native_recognition import _sha as file_sha

CHORDS=["Dmaj7","Em7","A7","Dmaj7"]*2+["Dmaj7"]
# Two phrases, ten and nine intended syllable attacks; last bar remains instrumental.
MELODY=["F4A4F8","G8B8","A4G4E8","F8D6z2",
        "F4A4F8","G8B8","A8E8","F6D8z2"]


def patch_outro(abc):
    score=parse_score(abc)
    if (score.headers["M"],score.headers["L"],score.headers["K"])!=("4/4","1/16","D"):
        raise ValueError("This repair template requires D major, 4/4, L:1/16")
    q=re.fullmatch(r"1/4\s*=\s*(\d+)",score.headers.get("Q",""))
    if not q or not 40<=int(q[1])<=240:
        raise ValueError("Unsupported score tempo")
    bars=score.sections["Vocal"]
    tail=[i for i,s in enumerate(bars) if s=="outro#1"]
    if len(tail)!=9 or tail!=list(range(len(bars)-9,len(bars))):
        raise ValueError("Expected one terminal nine-bar outro")
    rests=[]
    for i,chord in zip(tail,CHORDS):
        events=score.bar_events["Vocal"][i]
        if len(events)!=1 or events[0].raw!="z16" or events[0].kind!="rest" or score.bar_chords.get(("Vocal",i))!=[chord]:
            raise ValueError("Original outro differs from verified silent chord template")
        rests.append(events[0])
    prior=[e.pitch for e in score.events if e.voice=="Vocal" and e.kind=="note" and e.bar<tail[0]]
    if not prior:
        raise ValueError("No preceding vocal register")
    # Adapt octave to the immediately preceding vocal register, staying inside
    # the observed song-wide range; no invented note-to-syllable alignment.
    recent=[e.pitch for e in score.events if e.voice=="Vocal" and e.kind=="note" and tail[0]-16<=e.bar<tail[0]] or prior
    pitches={"D":62,"E":64,"F":66,"G":67,"A":69,"B":71}
    offsets=[o for o in (-12,0,12) if min(prior)<=62+o and 71+o<=max(prior)]
    if not offsets:
        raise ValueError("Template does not fit observed vocal range")
    offset=min(offsets,key=lambda o:abs(statistics.median(recent)-(66.5+o)))
    def transpose(m):
        return m[0]+("," if offset<0 else "'" if offset>0 else "")
    edits=[{"line":e.line,"start":e.start,"end":e.end,"old":e.raw,
            "new":re.sub("[A-G]",transpose,melody)} for e,melody in zip(rests,MELODY)]
    patched=patch_score(score,edits)
    check=parse_score(patched)
    if (check.counts!=score.counts or check.sections!=score.sections or check.bar_chords!=score.bar_chords):
        raise ValueError("Patch changed protected structure")
    def signature(s):
        return [(e.voice,e.bar,e.offset,e.duration,e.raw,e.pitch) for e in s.events
                if e.voice=="Ins" or e.bar<tail[0]]
    if signature(score)!=signature(check):
        raise ValueError("Patch changed protected notes")
    if sum(e.kind=="note" and e.voice=="Vocal" and e.bar in tail for e in check.events)!=19:
        raise ValueError("Expected nineteen new vocal note attacks")
    bar_seconds=Fraction(240,int(q[1]))
    return patched,float(tail[0]*bar_seconds),float(len(bars)*bar_seconds)


def codes(value):
    if not isinstance(value,str) or not value.strip():
        raise ValueError("Missing semantic stream")
    parts=value.strip().split(",")
    if len(parts)>15000 or any(not p.strip().isdigit() or int(p)>=32768 for p in parts):
        raise ValueError("Invalid native semantic stream")
    return [str(int(p)) for p in parts]


def prepare_replay(song,brief):
    replay=song.get("replay_request")
    settings=song.get("generation_settings")
    if not isinstance(replay,dict) or not isinstance(settings,dict):
        raise ValueError("Missing native replay or generation settings object")
    # Studio import_tracks explicitly documents sparse engine replay records:
    # default-valued fields are omitted. generation_settings starts with the
    # submitted request, overlays replay and fills engine defaults.
    # Never assume a missing mode is full, or ignore an explicit conflict.
    modes=[record["cot"] for record in (settings,replay) if "cot" in record]
    metadata=song.get("metadata")
    if isinstance(metadata,dict) and metadata.get("cot") is not None:
        modes.append(metadata["cot"])
    if not modes or any(mode!="full" for mode in modes):
        raise ValueError("Full-score mode not established by retained metadata: "
                         +"replay="+repr(replay.get("cot"))+", settings="+repr(settings.get("cot")))
    print("Full-score mode: verified"+(" from generation settings (sparse replay)" if "cot" not in replay else " from replay"),flush=True)
    if (replay.get("backing_song_id") or replay.get("adapters") not in (None,[])
            or replay.get("companion_scale") not in (None,0) or replay.get("seed")!=brief["seed"]
            or replay.get("lm_seed")!=brief["seed"]):
        raise ValueError("Replay configuration differs from retained reference")
    abc=settings.get("abc")
    if not isinstance(abc,str) or not isinstance(replay.get("abc"),str) or abc.strip()!=replay["abc"].strip():
        raise ValueError("Saved score and replay score disagree")
    groups=parse_lyrics(brief["lyrics"])
    outro=groups[-1]
    if outro["name"]!="outro" or len(outro["lines"])!=2:
        raise ValueError("This melody template requires two final lyric lines")
    if replay.get("lyrics","").strip()!=brief["lyrics"].strip():
        raise ValueError("Replay lyrics differ from brief")
    fixed,start,end=patch_outro(abc)
    original=codes(replay.get("semantic_tokens"))
    # Native source documents 25 semantic frames/s. Score clock is not
    # an acoustic boundary; allow only a close whole-duration match.
    if abs(len(original)/25-end)>3:
        raise ValueError("Score and semantic stream durations differ by more than three seconds")
    cut=math.floor(start*25)
    if not 0<cut<len(original) or not 10<=end-start<=45:
        raise ValueError("Unsafe continuation boundary")
    fields=dict(replay)
    for key in ("truncated","lyric_schedule","abc_continue","score_edit"):
        fields.pop(key,None)
    fields.update(cot="full",abc=fixed,semantic_tokens=",".join(original[:cut]),continue_semantic_tokens=True,
                  duration=end+0.5,lm_batch_size=1,synth_batch_size=1,output_format="flac")
    sampling=dict(fields.get("semantic_sampling") or {})
    sampling.update(min_tokens=cut+int((end-start)*25*0.9),max_tokens=math.ceil((end+0.5)*25))
    fields["semantic_sampling"]=sampling
    return {"title":brief["title"]+" - Outro candidate","replay_request":fields},cut,start,end


def submit(url,payload):
    endpoint=urlsplit(configured_endpoint(url))
    if endpoint.path!="/mcp":
        raise ValueError("Standard local endpoint required")
    target=urlunsplit((endpoint.scheme,endpoint.netloc,"/v1/music/replay","",""))
    req=Request(target,data=_canonical(payload),headers={"Content-Type":"application/json","Accept":"application/json"},method="POST")
    with build_opener(ProxyHandler({}),_NoRedirect()).open(req,timeout=90) as response:
        raw=response.read(16_777_217)
    if len(raw)>16_777_216:
        raise ValueError("Replay receipt exceeds bound")
    return json.loads(raw)


def run(repo,url,confirm):
    brief=load_brief(repo/"local/brief.json")
    root=repo/"results/drafts"/_sha(_canonical(brief))
    original=read(root/"journal_song.json")
    if (original.get("brief_sha256")!=_sha(_canonical(brief)) or
        original.get("request_sha256")!=_sha(_canonical(request_for(brief))) or
        original.get("state") not in ("SUBMITTED","COMPLETED") or not original.get("job_id")):
        raise ValueError("Original draft journal identity not verified")
    client=Client(configured_endpoint(url),timeout=90).connect()
    job_id=original["job_id"]
    job=unpack(client.call("song_job_get",{"job_id":job_id,"response_format":"concise"}))
    if job.get("id")!=job_id or job.get("status")!="completed" or len(job.get("songs",[]))!=1:
        raise ValueError("Original draft not confirmed complete")
    verify_completed_settings(job,brief)
    song_id=job["songs"][0]["id"]
    song=native_song_read(url,song_id)
    if song.get("id")!=song_id or song.get("metadata",{}).get("job_id")!=job_id:
        raise ValueError("Original song provenance mismatch")
    audio=Path(unpack(client.call("library_song_files",{"song_id":song_id}))["audio"])
    if not audio.is_absolute() or not audio.is_file() or audio.suffix.lower()!=".flac":
        raise ValueError("Original FLAC unavailable")
    sha=file_sha(audio)
    payload,cut,start,end=prepare_replay(song,brief)
    out=root/"outro-repair"
    out.mkdir(exist_ok=True)
    path=out/"journal.json"
    plan={"original_job_id":job_id,"original_song_id":song_id,"original_audio_sha256":sha,
          "payload_sha256":_sha(_canonical(payload)),"prefix_frames":cut,"planned_outro_start":start,
          "planned_score_end":end,"acoustic_boundary_verified":False}
    print("Planned outro:",round(start,3),"to",round(end,3),"seconds; retained frames:",cut,flush=True)
    print("19 vocal note attacks added; instrumental score and earlier score unchanged.",flush=True)
    if path.exists():
        j=read(path)
        if any(j.get(k)!=v for k,v in plan.items()) or not j.get("job_id"):
            raise ValueError("Existing candidate attempt uncertain or differs; never resubmit")
    else:
        _write(out/"plan.json",plan)
        _write(out/"request.json",payload)
        if not confirm:
            print("Plan only. No generation.")
            return
        status=unpack(client.call("studio_status",{}))
        reference_configuration(client,status,request_for(brief),unpack(client.call("song_defaults",{})),
                                unpack(client.call("studio_capabilities",{})))
        if file_sha(audio)!=sha:
            raise ValueError("Original audio changed")
        j={**plan,"state":"SUBMISSION_ATTEMPTED"}
        create_journal(path,j)
        print("Submitting one experimental outro continuation candidate...",flush=True)
        raw=submit(url,payload)
        _write(out/"receipt.json",raw)
        candidate_id=extract_song_job_id(raw)
        if not candidate_id:
            raise ValueError("Candidate receipt ambiguous; never resubmit")
        j.update(job_id=candidate_id,state="SUBMITTED")
        _write(path,j)
    for i in range(21):
        result=unpack(client.call("song_job_get",{"job_id":j["job_id"],"response_format":"concise"}))
        if result.get("id")!=j["job_id"]:
            raise ValueError("Candidate job identity mismatch")
        print("Candidate status:",result.get("status"),flush=True)
        if result.get("status")=="completed":
            break
        if result.get("status") not in ("queued","running") or i==20:
            raise ValueError("Candidate not completed; never resubmit")
        client.call("studio_wait",{"job_id":j["job_id"],"seconds":45})
    if len(result.get("songs",[]))!=1:
        raise ValueError("Expected one candidate song")
    candidate=result["songs"][0]["id"]
    if candidate==song_id:
        raise ValueError("Unexpected original song identity")
    saved=native_song_read(url,candidate)
    if saved.get("id")!=candidate or saved.get("metadata",{}).get("job_id")!=j["job_id"]:
        raise ValueError("Candidate provenance mismatch")
    prefix=codes(payload["replay_request"]["semantic_tokens"])
    generated=codes(saved.get("replay_request",{}).get("semantic_tokens"))
    preserved=generated[:len(prefix)]==prefix
    if file_sha(audio)!=sha:
        raise ValueError("Original audio changed")
    _write(out/"report.json",{**plan,"candidate_song_id":candidate,"semantic_prefix_equal":preserved,
                              "original_unchanged":True,"waveform_prefix_verified":False,"automatic_acceptance":False})
    print("Original audio unchanged. Candidate semantic prefix equal:",preserved)
    print("Candidate library title:",payload["title"])
    print("No automatic replacement; actual pronunciation and waveform continuity not verified.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--url",required=True)
    parser.add_argument("--confirm",action="store_true")
    args=parser.parse_args()
    try:
        run(args.repo.resolve(),args.url,args.confirm)
        return 0
    except (ValueError,OSError,KeyError,TypeError,MCPError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
