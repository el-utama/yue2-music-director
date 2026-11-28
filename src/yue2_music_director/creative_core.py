"""Durable text-only creative stages. No Studio mutation or generation."""
from pathlib import Path
import argparse
import sqlite3
import re
import time
import sys

from . import composer, lyricist, creative_reviewer, native_draft as nd
from .creative_provider import TextProvider
from .listening_director import lock
from .multilingual_fidelity import SUPPORTED


def stage(root, role, module, provider, data, *, retry=False, semantic_check=None):
    identity={"role":role,"provider":provider.identity(),"prompt":module.PROMPT,"input":data}
    receipt=root/(role+".json")
    attempt=root/(role+".attempt.json")
    if receipt.exists():
        saved=nd.read(receipt)
        if not attempt.exists() or nd.read(attempt)!=identity or saved.get("identity")!=identity:
            raise ValueError("Retained stage identity differs: "+role)
        if saved.get("schema") not in (None,"creative-stage-semantic-v1"):
            raise ValueError("Unknown retained stage receipt schema: "+role)
        value=module.validate(saved["result"])
        if semantic_check is not None:
            semantic_check(value)
        print(role.capitalize()+": retained",flush=True)
        return value
    recovery=root/(role+".retry-1.attempt.json")
    if attempt.exists():
        if nd.read(attempt)!=identity:
            raise ValueError("Original stage identity differs: "+role)
        if not retry:
            raise ValueError("Unresolved stage attempt; explicit one-time text retry required: "+role)
        if recovery.exists():
            raise ValueError("Text retry already attempted; retain evidence: "+role)
        nd.create_journal(recovery,identity)
    else:
        if retry or recovery.exists():
            raise ValueError("No original unresolved stage to retry: "+role)
        nd.create_journal(attempt,identity)
    rejected=root/(role+(".retry-1" if retry else "")+".rejected.json")
    if rejected.exists():
        raise ValueError("Rejected response already retained: "+role)
    print(role.capitalize()+": requesting text",flush=True)
    started=time.monotonic()
    response=provider.complete(role,module.PROMPT,data)
    try:
        result=module.validate(response)
        if semantic_check is not None:
            semantic_check(result)
    except ValueError as exc:
        # Evidence of rejection is not a successful receipt. The existing attempt
        # journal still requires explicit, bounded recovery before another call.
        nd.atomic_write(rejected,{"schema":"creative-stage-rejected-v1",
                                  "identity":identity,"response":response,"reason":str(exc)})
        raise
    saved={"identity":identity,"result":result}
    if semantic_check is not None:
        saved["schema"]="creative-stage-semantic-v1"
    nd.atomic_write(receipt,saved)
    print(role.capitalize()+": complete ("+str(round(time.monotonic()-started,1))+" s)",flush=True)
    return result


def prepare(root, provider, request, language, duration, *, retry_role=None, duration_guidance=False, direction_guidance=False, timing_guidance=False, structured_direction=False, typed_spec=None, knowledge=None, style_recipe=None, song_form=None):
    data={"request":request,"language":language,"duration_seconds":duration}
    if song_form is not None:
        if song_form != lyricist.COMPACT_FORM:
            raise ValueError("Unknown frozen song form")
        data["song_form_guidance"] = lyricist.FORM_GUIDANCE

    def review_words(music, lyrics):
        diagnostics = lyricist.diagnostics(lyrics, language, compact_form=song_form is not None)
        return stage(root, "reviewer", creative_reviewer, provider,
                     {**data, "composition": music, "lyrics": lyrics, "diagnostics": diagnostics},
                     retry=retry_role == "reviewer")

    def role_data(role, data):
        result=data
        if knowledge is not None:
            from .creative_knowledge import payload
            result={**result, "knowledge_context": payload(knowledge, role)}
        if style_recipe is not None and role=="composer":
            from .style_selection import payload as style_payload
            result={**result, "style_recipe": style_payload(style_recipe)}
        return result
    if duration_guidance:
        # Advisory target only; the actual native score clock is screened before rendering.
        reserve=min(15,max(3,round(duration*0.08)))
        if song_form == lyricist.COMPACT_FORM and duration == lyricist.DEFAULT_DURATION:
            reserve = lyricist.ENDING_ALLOWANCE
        data["duration_plan"]={"hard_cap_seconds":duration,"target_score_seconds":duration-reserve,
              "ending_reserve_seconds":reserve,
              "guidance":"Plan a compact complete song, with a resolved final sung phrase and short instrumental tail inside the target. Allow room for introductions, instrumental breaks, breathing and sustained notes. Avoid redundant verses, long repeated choruses or extended outros. Lyricist should adapt line and section count to pacing; reviewer should stop implausibly long plans. Do not treat duration as an exact target or omit necessary closure."}
        if song_form == lyricist.COMPACT_FORM and duration == lyricist.DEFAULT_DURATION:
            data["duration_plan"]["ending_guidance"] = (
                "Aim to finish within 180 seconds. Up to ten extra seconds are available for a "
                "natural cadence, breath or ringing last chord. Do not plan extra lyrics to fill them."
            )
    if typed_spec is not None:
        from . import typed_creative as tc, composer_typed
        if direction_guidance or timing_guidance or structured_direction:
            raise ValueError("Typed direction uses a separate contract")
        spec=tc.validate_spec(typed_spec)
        data["typed_requirements"]=spec
        data["typed_guidance"]=tc.GUIDANCE
        from .creative_direction import TIMING_GUIDANCE
        data["opening_timing_guidance"]=TIMING_GUIDANCE
        music=stage(root,"composer",composer_typed,provider,role_data("composer",data),retry=retry_role=="composer",
                    semantic_check=lambda value:tc.check_composer(value,spec))
        if spec["lyrics"] is not None:
            if retry_role=="lyricist":
                raise ValueError("Exact operator lyrics do not use a provider stage")
            if any((root/name).exists() for name in ("lyricist.json","lyricist.attempt.json","lyricist.retry-1.attempt.json")):
                raise ValueError("Conflicting provider lyric receipts for exact lyrics")
            words={"lyrics":spec["lyrics"]}
            tc.check_lyrics(music,words["lyrics"],spec)
            receipt={"schema":"operator-lyrics-v1","input":{**data,"composition":music},"result":words,
                     "provider_calls":0}
            path=root/"operator-lyrics.json"
            if path.exists():
                if nd.read(path)!=receipt:
                    raise ValueError("Retained operator lyric receipt differs")
            else:
                nd.create_journal(path,receipt)
        else:
            words=stage(root,"lyricist",lyricist,provider,role_data("lyricist",{**data,"composition":music}),
                        retry=retry_role=="lyricist",semantic_check=lambda value:tc.check_lyrics(music,value["lyrics"],spec))
        review=review_words(music, words["lyrics"])
        return {"composition":music,"lyrics":words["lyrics"],"review":review}
    if direction_guidance:
        from . import creative_direction as cd
        data["direction_guidance"]=cd.STRUCTURED_GUIDANCE if structured_direction else cd.GUIDANCE
        if timing_guidance:
            data["opening_timing_guidance"]=cd.TIMING_GUIDANCE
    elif timing_guidance or structured_direction:
        raise ValueError("Timing/structured guidance requires direction guidance")
    music=stage(root,"composer",composer.Structured if structured_direction else composer,provider,role_data("composer",data),retry=retry_role=="composer",
                semantic_check=cd.parse_direction if direction_guidance else None)
    words=stage(root,"lyricist",lyricist,provider,role_data("lyricist",{**data,"composition":music}),retry=retry_role=="lyricist",
                semantic_check=(lambda value: cd.validate_opening(music,value["lyrics"])) if direction_guidance else None)
    review=review_words(music, words["lyrics"])
    return {"composition":music,"lyrics":words["lyrics"],"review":review}


def validate_job(job, request, language, duration):
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",job)
            or job.lower() in {"con","prn","aux","nul"} or re.fullmatch(r"(com|lpt)[1-9]",job.lower())):
        raise ValueError("Invalid job name")
    if not request.strip() or len(request)>4000 or language not in SUPPORTED or not 30<=duration<=208:
        raise ValueError("Invalid creative request, language or duration")


def launch(repo, job, request, language, duration, *, confirm_text=False, provider_factory=None, knowledge_query=None, confirm_knowledge_context=False):
    validate_job(job, request, language, duration)
    if confirm_knowledge_context and not confirm_text:
        raise ValueError("Knowledge transfer confirmation requires --confirm-text")
    if not confirm_text:
        if knowledge_query is not None:
            from .creative_knowledge import snapshot
            import json
            print(json.dumps(snapshot(repo/"local/knowledge-bank.sqlite", knowledge_query), ensure_ascii=True, indent=2))
        print("Plan only; no provider or Studio calls.")
        return 0
    provider=provider_factory() if provider_factory else TextProvider.for_repo(repo)
    jobs=repo/"results/creative"
    root=jobs/job
    with lock(jobs/".active",context={"root":root.relative_to(repo).as_posix(),"stage":"creative","job":job}):
        identity={"schema":"creative-job-v1","request":request,"language":language,
                  "duration_seconds":duration,"provider":provider.identity()}
        manifest=root/"job.json"
        knowledge = None
        if root.exists():
            saved = nd.read(manifest)
            knowledge = saved.get("knowledge")
            if knowledge is not None:
                if not confirm_knowledge_context:
                    raise ValueError("Resuming knowledge job requires --confirm-knowledge-context")
                if knowledge_query is not None and knowledge_query != knowledge["query"]:
                    raise ValueError("Retained knowledge query differs")
                identity["knowledge"] = knowledge
            elif knowledge_query is not None or confirm_knowledge_context:
                raise ValueError("Cannot add knowledge to a retained legacy job")
            if saved!=identity:
                raise ValueError("Retained job differs")
        else:
            if knowledge_query is not None:
                if not confirm_knowledge_context:
                    raise ValueError("Derived knowledge transfer requires --confirm-knowledge-context")
                from .creative_knowledge import snapshot
                knowledge = snapshot(repo/"local/knowledge-bank.sqlite", knowledge_query)
                identity["knowledge"] = knowledge
            elif confirm_knowledge_context:
                raise ValueError("New knowledge job needs --knowledge-query")
            root.mkdir(parents=True,exist_ok=False)
            nd.atomic_write(manifest,identity)
        result=prepare(root,provider,request,language,duration,knowledge=knowledge)
        nd.atomic_write(root/"creative-result.json",result)
        print("Creative result:",root/"creative-result.json")
        print("Editorial decision:",result["review"]["decision"])
        print("No Studio inference. Musical quality and originality not verified.")
        return 0 if result["review"]["decision"]=="retain" else 2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--job",required=True)
    p.add_argument("--request",required=True)
    p.add_argument("--language",default="en")
    p.add_argument("--duration",type=int,default=195)
    p.add_argument("--confirm-text",action="store_true")
    p.add_argument("--knowledge-query", help="Local lexical search; preview unless text transfer explicitly confirmed")
    p.add_argument("--confirm-knowledge-context", action="store_true", help="Allow only bounded numeric reference descriptors to text roles")
    a=p.parse_args()
    try:
        return launch(a.repo.resolve(),a.job,a.request,a.language,a.duration,confirm_text=a.confirm_text,knowledge_query=a.knowledge_query,confirm_knowledge_context=a.confirm_knowledge_context)
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error) as e:
        print("ERROR:",e,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
