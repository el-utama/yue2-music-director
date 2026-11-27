"""Read-only, point-in-time preflight for new local production."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import shutil

from . import artist_run, audio_critic
from .creative_provider import TextProvider
from .lock_status import LOCKS
from .mcp import Client, configured_endpoint

BRIEF={"title":"Readiness fixture","style":"English, acoustic folk, gentle vocals, 80 BPM",
       "lyrics":"[Verse 1]\nA short line","language":"en","seed":42,"duration_seconds":90}
ERRORS=(OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError, OverflowError)


def _windows_host():
    return os.name=="nt"


def inspect(repo,url,*,media_dir=None,client_factory=None,provider_factory=None):
    checks={}
    def set_check(name,status,detail):
        checks[name]={"status":status,"detail":detail}
    set_check("windows_host","pass" if _windows_host() else "blocked",
              "Windows Studio host required for the local captioner.")
    tools=all(shutil.which(name) for name in ("ffmpeg","ffprobe"))
    set_check("ffmpeg","pass" if tools else "blocked","FFmpeg and ffprobe must be on PATH.")
    markers=[name for name in ("autonomous","drafts","critic")
             if os.path.lexists(repo/LOCKS[name])]
    set_check("production_locks","blocked" if markers else "pass",
              "Inspect existing markers: "+", ".join(markers) if markers else "No production markers observed.")
    # No provider calls, no identity or credential values printed.
    try:
        provider=(provider_factory or TextProvider.for_repo)(repo)
        if not isinstance(provider,TextProvider):
            raise ValueError("Invalid provider")
        del provider
        set_check("provider_configuration","pass","Local configuration loaded; authentication not tested.")
    except ERRORS:
        set_check("provider_configuration","blocked","Local configuration unavailable or invalid; inspect existing setup.")
    if media_dir is None:
        set_check("moss_files","not_checked","Optional --media-dir requires the actual Studio managed media directory.")
    else:
        try:
            installed=audio_critic.inventory_media(media_dir)
            set_check("moss_files","pass" if installed["ready"] else "blocked",
                      "Managed captioner, model sizes and DLLs checked; runtime not tested.")
        except ERRORS:
            set_check("moss_files","blocked","Managed media directory or captioner inventory unavailable.")
    if not tools or markers or not _windows_host():
        set_check("native_reference","not_checked","Resolve local host, FFmpeg or lock blockers first.")
    else:
        try:
            target=configured_endpoint(url)
            # Existing checks print local model metadata; do not expose it in a shareable readiness report.
            with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
                client=(client_factory or Client)(target,timeout=10).connect()
                artist_run._preflight(client,BRIEF,artist_run.plan_request(BRIEF,{"follow_lyrics":True}),wait=False)
            set_check("native_reference","pass","Native schemas, idle state, Whisper and stock reference checks passed.")
        except ERRORS:
            set_check("native_reference","blocked","Native read-only preflight failed. Check Studio is running, idle, Whisper ready and stock reference configuration.")
    blocked=any(v["status"]=="blocked" for v in checks.values())
    return {"schema":"local-readiness-v1","status":"blocked" if blocked else "preflight_pass",
            "checks":checks,"not_verified":["provider authentication and quota","actual GPU memory and synthesis",
            "captioner execution","artistic quality"],"execution_authorized":False,
            "provider_calls":0,"generation_calls":0,"recognition_calls":0,
            "settings_writes":0,"library_mutations":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--url",required=True)
    p.add_argument("--ready",action="store_true")
    p.add_argument("--media-dir",type=Path)
    a=p.parse_args()
    report=inspect(a.repo.resolve(),a.url,media_dir=a.media_dir)
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 2 if report["status"]=="blocked" else 0


if __name__=="__main__":
    raise SystemExit(main())
