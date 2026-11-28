"""Read-only, hash-linked source evidence for completed autonomous songs.

Historical retrieval never replays provider stages or recomputes musical
judgments under today's policy. Hash links detect inconsistent local
artifacts, not a malicious rewrite of every receipt.
"""
from pathlib import Path

from . import creative_core as cc, native_draft as nd, listening_director as ld

POLICIES={"reviewed-score-v1","reviewed-score-v2","reviewed-score-v3","reviewed-score-v4-typed","reviewed-score-v5-structured"}
PLAN_FILES={"manifest.json","journal_plan.json","plan-result.json","plan-receipt.json","native-plan.abc"}


def resolve(repo,job):
    cc.validate_job(job,"placeholder","en",195)
    parent=Path(repo)/"results/autonomous"/job
    roots=[p for p in (parent,parent/"continuation-1") if (p/"result.json").is_file()]
    if len(roots)!=1:
        raise ValueError("Exactly one completed retained result required: "+job)
    return parent,roots[0]


def _receipt(root,role,provider):
    receipt=nd.read(root/(role+".json"))
    attempt=nd.read(root/(role+".attempt.json"))
    if (receipt.get("schema") not in (None,"creative-stage-semantic-v1")
            or receipt.get("identity")!=attempt or attempt.get("role")!=role
            or attempt.get("provider")!=provider
            or not isinstance(attempt.get("prompt"),str) or not attempt["prompt"].strip()
            or not isinstance(attempt.get("input"),dict)
            or not isinstance(receipt.get("result"),dict)):
        raise ValueError("Retained creative stage identity differs: "+role)
    recovery=root/(role+".retry-1.attempt.json")
    if recovery.exists() and nd.read(recovery)!=attempt:
        raise ValueError("Retained creative retry identity differs: "+role)
    return attempt["input"],receipt["result"]


def _creative(parent,identity,brief):
    data,music=_receipt(parent,"composer",identity["provider"])
    if identity["production_policy"]=="reviewed-score-v4-typed":
        spec=identity.get("creative_spec")
        if not isinstance(spec,dict) or data.get("typed_requirements")!=spec:
            raise ValueError("Retained typed requirements differ")
    else:
        spec=None
    if spec is not None and spec.get("lyrics") is not None:
        receipt=nd.read(parent/"operator-lyrics.json")
        words_input={**data,"composition":music}
        words={"lyrics":spec["lyrics"]}
        if (receipt!={"schema":"operator-lyrics-v1","input":words_input,"result":words,"provider_calls":0}
                or any((parent/n).exists() for n in ("lyricist.json","lyricist.attempt.json","lyricist.retry-1.attempt.json"))):
            raise ValueError("Retained exact operator lyric identity differs")
    else:
        words_input,words=_receipt(parent,"lyricist",identity["provider"])
    review_input,review=_receipt(parent,"reviewer",identity["provider"])
    if (any(data.get(k)!=identity.get(k) for k in ("request","language","duration_seconds"))
            or words_input!={**data,"composition":music}
            or {k:v for k,v in review_input.items() if k!="diagnostics"}!=
                {**data,"composition":music,"lyrics":words["lyrics"]}
            or not isinstance(review_input.get("diagnostics"),list)
            or review.get("decision")!="retain"):
        raise ValueError("Retained creative input lineage differs")
    creative=nd.read(parent/"creative-result.json")
    if (creative!={"composition":music,"lyrics":words["lyrics"],"review":review}
            or any(music.get(k)!=brief[k] for k in ("title","style"))
            or words["lyrics"]!=brief["lyrics"]):
        raise ValueError("Retained creative result differs")
    for k,limit in (("title",150),("style",2000),("concept",2000),("emotional_arc",2000),("performance",2000)):
        if not isinstance(music.get(k),str) or not music[k].strip() or len(music[k])>limit:
            raise ValueError("Invalid retained creative metadata: "+k)
    return creative


def _continuation(parent,root,job):
    if root==parent:
        return
    contract=nd.read(root/"continuation.json")
    from .duration_fit import FIT_SCHEMA
    if (contract.get("schema") not in ("retained-plan-continuation-v1",FIT_SCHEMA)
            or contract.get("parent_job")!=job
            or contract.get("original_job_sha256")!=nd._sha(parent/"job.json")
            or contract.get("original_stop_sha256")!=nd._sha(parent/"plan-stop.json")
            or contract.get("original_plan_decision_sha256")!=nd._sha(parent/"production/plan-decision.json")
            or set(contract.get("source_files",{}))!=PLAN_FILES):
        raise ValueError("Retained continuation lineage differs")
    for name,sha in contract["source_files"].items():
        if any(nd._sha(base/"production"/name)!=sha for base in (parent,root)):
            raise ValueError("Retained continuation source differs: "+name)
    if contract.get("review")!=nd.read(root/"production/plan-decision.json"):
        raise ValueError("Retained continuation review differs")
    return contract


def _packet(production,brief,intent,row):
    """Read frozen observations, without current prompt/parser or writes."""
    out=production/"neutral-listening"
    packet=nd.read(out/"review-packet.json")
    contract=nd.read(out/"contract.json")
    runtime=nd.read(out/"runtime.json")
    prompt=out/"prompt.txt"
    if (contract.get("schema")!="neutral-listening-v1" or contract.get("audio_sha256")!=row["audio_sha256"]
            or contract.get("automatic_acceptance") is not False
            or prompt.read_bytes().decode("utf-8").replace("\r\n","\n")!=contract.get("prompt")
            or packet.get("schema")!="director-review-v1"
            or packet.get("neutral_contract")!=contract or packet.get("brief")!=brief
            or packet.get("artistic_intent")!=intent
            or packet.get("automatic_acceptance") is not False
            or packet.get("revision_authorized") is not False
            or any(packet.get(k)!=row[k] for k in ("audio","audio_sha256","acoustic","lyric_screen"))):
        raise ValueError("Retained listening packet identity differs")
    ranges=contract["ranges"]
    observations=packet["observations"]
    if not isinstance(ranges,list) or len(ranges)!=2 or len(observations)!=len(ranges):
        raise ValueError("Retained listening observation count differs")
    for index,((start,duration),item) in enumerate(zip(ranges,observations),1):
        stem="arm-1-part-"+str(index)
        raw=out/(stem+".txt")
        receipt=nd.read(out/(stem+".json"))
        expected={"audio_sha256":row["audio_sha256"],"start_seconds":start,
                  "duration_seconds":duration,"prompt_sha256":nd._sha(prompt),"runtime":runtime}
        if (receipt.get("identity")!=expected or receipt.get("response_sha256")!=nd._sha(raw)
                or item.get("start_seconds")!=start or item.get("duration_seconds")!=duration
                or item.get("raw_response")!=raw.read_text(encoding="utf-8",errors="replace")):
            raise ValueError("Retained listening receipt differs")
    return packet


def _inputs(parent,root,job):
    identity=nd.read(parent/"job.json")
    if (identity.get("schema")!="autonomous-job-v1" or identity.get("job")!=job
            or identity.get("production_policy") not in POLICIES):
        raise ValueError("Retained autonomous identity differs")
    cc.validate_job(job,identity["request"],identity["language"],identity["duration_seconds"])
    contract=_continuation(parent,root,job)
    brief=nd.load_brief(root/"brief.json")
    intent=nd.read(root/"intent.json")
    original_brief=nd.load_brief(parent/"brief.json")
    original_intent=nd.read(parent/"intent.json")
    from .duration_fit import FIT_SCHEMA, verify_frozen
    if contract and contract["schema"]==FIT_SCHEMA:
        verify_frozen(parent,root,contract)
    elif brief!=original_brief or intent!=original_intent:
        raise ValueError("Retained brief/intent identity differs")
    if identity["duration_seconds"]!=brief["duration_seconds"] or identity["language"]!=brief["language"]:
        raise ValueError("Retained brief/intent identity differs")
    creative=_creative(parent,identity,original_brief)
    if any(original_intent.get(k)!=creative["composition"][k] for k in ("concept","emotional_arc","performance")):
        raise ValueError("Retained creative intent differs")
    if identity["production_policy"]=="reviewed-score-v4-typed":
        spec=identity["creative_spec"]
        direction=creative["composition"]["direction"]
        if (intent.get("schema")!="artist-intent-v2" or intent.get("direction")!=direction
                or intent.get("requested")!=spec
                or intent.get("section_purposes")!={i["section"]:i["purpose"] for i in direction["section_plan"]}
                or intent.get("constraints")!={**spec["score_constraints"],
                    "opening":{"mode":"must","value":direction["opening"]},
                    "opening_timing":{"mode":"must","value":direction["opening"]}}
                or spec.get("lyrics") is not None and spec["lyrics"]!=brief["lyrics"]):
            raise ValueError("Retained typed intent lineage differs")
    return identity,brief,intent,creative


def _native(root,brief,intent):
    production=root/"production"
    draft=production/"draft"
    report=nd.read(draft/"report.json")
    if report.get("artistic_intent")!=intent:
        raise ValueError("Retained native artistic intent differs")
    row=ld.verify_take(draft,brief,report,historical=True)
    packet=_packet(production,brief,intent,row)
    return report,row,packet


def continuation_before_director(repo,job):
    """Only a fully retained continuation with no final result, no new work."""
    cc.validate_job(job,"placeholder","en",195)
    parent=Path(repo)/"results/autonomous"/job
    root=parent/"continuation-1"
    if not root.is_dir() or any((p/"result.json").exists() for p in (parent,root)):
        raise ValueError("Director recovery requires an incomplete retained continuation")
    identity,brief,intent,creative=_inputs(parent,root,job)
    report,row,packet=_native(root,brief,intent)
    return {"job":job,"parent":parent,"root":root,"identity":identity,"brief":brief,
            "intent":intent,"creative":creative,"report":report,"row":row,"packet":packet,
            "audio":Path(row["audio"]),"frozen_hashes":{
                name:nd._sha(root/name) for name in ("continuation.json","brief.json","intent.json",
                "production/draft/report.json","production/neutral-listening/review-packet.json")}}


def load(repo,job):
    parent,root=resolve(repo,job)
    identity,brief,intent,creative=_inputs(parent,root,job)
    production=root/"production"
    draft=production/"draft"
    final=nd.read(root/"result.json")
    report,row,packet=_native(root,brief,intent)
    packet_path=production/"neutral-listening/review-packet.json"
    if (final.get("schema")!="autonomous-result-v1" or final.get("status") not in ("provisional","review_required")
            or final.get("automatic_acceptance") is not False or final.get("revision_authorized") is not False
            or final.get("brief_sha256")!=nd._sha(root/"brief.json")
            or final.get("native_report_sha256")!=nd._sha(draft/"report.json")
            or final.get("listening_packet_sha256")!=nd._sha(packet_path)
            or final.get("song_id")!=report.get("song_id")):
        raise ValueError("Retained autonomous result differs")
    if any(final.get(k)!=row[k] for k in ("audio","audio_sha256")):
        raise ValueError("Retained audio identity differs")
    director_input,director=_receipt(root,"director",identity["provider"])
    if (director!=final.get("director") or director_input.get("request")!=identity["request"]
            or director_input.get("brief")!=brief or director_input.get("intent")!=intent):
        raise ValueError("Retained Director receipt differs")
    evidence={"job":job,"result_sha256":nd._sha(root/"result.json"),
              "creative_sha256":nd._sha(parent/"creative-result.json")}
    return {"job":job,"parent":parent,"root":root,"identity":identity,"brief":brief,
            "intent":intent,"creative":creative,"report":report,"result":final,"row":row,
            "packet":packet,"audio":Path(row["audio"]),"evidence":evidence}
