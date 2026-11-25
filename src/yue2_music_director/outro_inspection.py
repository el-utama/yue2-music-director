"""Read the retained draft's original score and outro evidence; never submit jobs."""
import argparse
import re
import sys
from pathlib import Path
from .native_draft import load_brief, read, request_for, verify_completed_settings
from .experiments import _sha, _canonical
from .mcp import Client, configured_endpoint, unpack, MCPError
from .prosody import parse_lyrics
from .temporal_evidence import native_song_read


def inspect(repo,url):
    brief=load_brief(repo/"local/brief.json")
    root=repo/"results/drafts"/_sha(_canonical(brief))
    journal=read(root/"journal_song.json")
    if (journal.get("brief_sha256")!=_sha(_canonical(brief))
            or journal.get("request_sha256")!=_sha(_canonical(request_for(brief)))
            or journal.get("state") not in ("SUBMITTED","COMPLETED")
            or not isinstance(journal.get("job_id"),str) or not journal["job_id"]):
        raise ValueError("No verified retained job for this brief; no submission attempted")
    job_id=journal["job_id"]
    client=Client(configured_endpoint(url),timeout=90).connect()
    job=unpack(client.call("song_job_get",{"job_id":job_id,"response_format":"concise"}))
    if not isinstance(job,dict) or job.get("id")!=job_id or job.get("status")!="completed":
        raise ValueError("Retained job not confirmed completed")
    songs=job.get("songs")
    if not isinstance(songs,list) or len(songs)!=1 or not isinstance(songs[0],dict) or not songs[0].get("id"):
        raise ValueError("Expected one completed song")
    song_id=songs[0]["id"]
    song=native_song_read(url,song_id)
    if not isinstance(song,dict) or song.get("id")!=song_id:
        raise ValueError("Library song identity mismatch")
    meta=song.get("metadata")
    if not isinstance(meta,dict) or meta.get("job_id")!=job_id:
        raise ValueError("Library song provenance does not match retained job")
    print("Retained song:",brief["title"])
    try:
        verify_completed_settings(job,brief)
        print("Requested seeds and disabled adapters: confirmed by compact job metadata")
    except ValueError as exc:
        print("Metadata warning:",exc)
    print("Actual replay seed:",meta.get("seed"),"LM seed:",meta.get("lm_seed"))
    print("Duration:",meta.get("duration_seconds"))
    outro=[line for group in parse_lyrics(brief["lyrics"]) if group["name"]=="outro" for line in group["lines"]]
    print("Expected outro words:",len(" ".join(outro).split()))
    for line in outro:
        print(line)
    settings=song.get("generation_settings")
    score=settings.get("abc") if isinstance(settings,dict) else None
    if not isinstance(score,str) or not score.strip():
        print("Saved score unavailable; cannot locate planned outro.")
    else:
        sections=list(re.finditer(r"(?im)^%\s*(?:verse[^\r\n]*|pre[- ]chorus[^\r\n]*|chorus[^\r\n]*|bridge[^\r\n]*|intro[^\r\n]*|outro[^\r\n]*|interlude[^\r\n]*|instrumental[^\r\n]*)\s*$",score))
        print("Planned sections:",", ".join(m.group().strip() for m in sections)[:1000])
        starts=[m.start() for m in sections if m.group().lower().lstrip("% ").startswith("outro")]
        print("Saved outro section present:",bool(starts))
        print("Score tail (not a verified audio alignment):")
        print(score[starts[-1]:][:6000] if starts else score[-6000:])
    replay=song.get("replay_request")
    tokens=replay.get("semantic_tokens") if isinstance(replay,dict) else None
    print("Retained semantic stream available:",isinstance(tokens,str) and bool(tokens.strip()))
    print("Original song unchanged. New song jobs: 0. Recognition calls: 0.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--url",required=True)
    args=parser.parse_args()
    try:
        inspect(args.repo.resolve(),args.url)
        return 0
    except (ValueError,OSError,KeyError,TypeError,MCPError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
