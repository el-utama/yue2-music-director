"""Read-only identity of an original take or an independently verified gain candidate."""
from pathlib import Path

from . import audio_finishing as fin, creative_core as cc, native_draft as nd


def select(repo,source,variant="original"):
    """Never render, measure, or select a candidate implicitly."""
    cc.validate_job(source["job"],"placeholder","en",195)
    cc.validate_job(variant,"placeholder","en",195)
    key={"job":source["job"],"variant":variant,
         "result_sha256":source["evidence"]["result_sha256"],
         "audio_sha256":source["result"]["audio_sha256"]}
    original=Path(source["audio"])
    if variant=="original":
        if nd._sha(original)!=key["audio_sha256"]:
            raise ValueError("Original source changed")
        return {"identity":key,"audio":original,"timeline_preserved":True}
    if variant.casefold()=="original":
        raise ValueError("Use exact original variant name")
    base=Path(repo)/"results/audio-finishing"
    root=base/source["job"]/variant
    if any(p.is_symlink() for p in (base,root.parent,root)):
        raise ValueError("Unexpected finishing source symlink")
    contract=fin.contract_for(source,variant)
    report=fin.verify(root,source,contract)
    if report["status"]!="candidate_verified" or report["timeline_preserved"] is not True:
        raise ValueError("No independently verified finishing candidate; select original")
    candidate=root/"candidate.flac"
    key["audio_sha256"]=report["candidate_audio_sha256"]
    key["finishing_report_sha256"]=nd._sha(root/"report.json")
    if nd._sha(candidate)!=key["audio_sha256"] or nd._sha(original)!=contract["source_audio_sha256"]:
        raise ValueError("Finishing source changed")
    return {"identity":key,"audio":candidate,"timeline_preserved":True}
