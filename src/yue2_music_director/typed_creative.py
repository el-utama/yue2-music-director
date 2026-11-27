"""Opt-in explicit creative requirements; never extract hard rules from prose."""
import re

from . import creative_direction as cd, lyricist
from .musical_review import validate_constraints
from .prosody import parse_lyrics

POLICY="reviewed-score-v4-typed"
SPEC_SCHEMA="creative-spec-v1"
INTENT_SCHEMA="artist-intent-v2"
GUIDANCE={
    "version":"typed-direction-v1",
    "composer":"Return typed direction with separate opening, vocal, narrator and ordered section_plan entries. Explicit requirements are authoritative. Preserve supplied style and lyric section structure; do not infer singer identity from narrator. For unspecified fields, choose a coherent musical direction. Section IDs are normalized occurrences such as verse#1, chorus#1, chorus#2. A purpose describes each section's musical/story function; positive English style describes the sound including chosen vocal identity. Never put production cues in sung lines.",
    "lyricist":"Follow composition.direction and section_plan exactly. If an instrumental intro is chosen, use an empty opening [Intro]. If direct vocal is chosen, begin with a sung section. Use the selected narrator; do not add or omit planned sections.",
    "reviewer":"Explicit typed requirements are mandatory where declared. Review consistency between style and vocal direction, story and narrator, exact section plan, requested musical constraints and closure. Stop unresolved conflict. Native score gates, not this judgment, establish assessable score requirements. Do not claim acoustic identity or alignment."
}
DEFAULTS={"opening":None,"vocal":None,"narrator":None,"style":None,"lyrics":None,
          "section_purposes":{},"score_constraints":{}}


def _text(v,limit):
    return isinstance(v,str) and bool(v.strip()) and len(v)<=limit


def section_ids(lyrics):
    return [f"{g['name']}#{g['occurrence']}" for g in parse_lyrics(lyrics)]


def _section_id(value):
    return isinstance(value,str) and len(value)<=80 and bool(re.fullmatch(r"[a-z][a-z0-9 -]*#[1-9][0-9]*",value))


def _purposes(value):
    if (not isinstance(value,dict) or len(value)>24
            or any(not _section_id(k) or not _text(v,1000) for k,v in value.items())):
        raise ValueError("Invalid explicit section purposes")
    return dict(value)


def opening_of(lyrics):
    groups=parse_lyrics(lyrics)
    first=groups[0]
    if first["name"]=="intro" and not first["lines"] and len(groups)>1 and groups[1]["lines"]:
        return "instrumental_intro"
    if first["name"] not in ("intro","interlude") and first["lines"]:
        return "direct_vocal"
    raise ValueError("Lyrics require a supported vocal opening or a wordless intro followed by vocals")


def validate_spec(value):
    if (not isinstance(value,dict) or value.get("schema")!=SPEC_SCHEMA
            or not set(value)<={"schema",*DEFAULTS}):
        raise ValueError("Invalid explicit creative specification")
    spec={**DEFAULTS,**value}
    if spec["opening"] is not None and spec["opening"] not in cd.OPENINGS:
        raise ValueError("Invalid requested opening")
    if spec["vocal"] is not None and spec["vocal"] not in cd.VOICES:
        raise ValueError("Invalid requested vocal identity")
    for k,limit in (("narrator",500),("style",2000),("lyrics",20000)):
        if spec[k] is not None and not _text(spec[k],limit):
            raise ValueError("Invalid requested "+k)
    spec["section_purposes"]=_purposes(spec["section_purposes"])
    constraints=spec["score_constraints"]
    if not isinstance(constraints,dict) or not set(constraints)<={"key","tempo_bpm","section_order","sung_sections"}:
        raise ValueError("Use only supported native score constraints; specify opening separately")
    validate_constraints(constraints)
    for k in ("section_order","sung_sections"):
        if k in constraints and constraints[k]["mode"]!="free":
            vals=constraints[k]["value"]
            if not vals or len(vals)>24 or len(set(vals))!=len(vals) or any(not _section_id(x) for x in vals):
                raise ValueError("Invalid explicit section occurrence constraint")
    if spec["lyrics"] is not None:
        lyricist.validate({"lyrics":spec["lyrics"]})
        ids=section_ids(spec["lyrics"])
        sung=[f"{g['name']}#{g['occurrence']}" for g in parse_lyrics(spec["lyrics"]) if g["lines"]]
        if spec["opening"] is not None and opening_of(spec["lyrics"])!=spec["opening"]:
            raise ValueError("Requested opening conflicts with exact supplied lyrics")
        if not set(spec["section_purposes"])<=set(ids):
            raise ValueError("Requested section purpose not present in exact supplied lyrics")
        for k,actual in (("section_order",ids),("sung_sections",sung)):
            if k in constraints and constraints[k]["mode"]=="must" and constraints[k]["value"]!=actual:
                raise ValueError("Requested "+k+" conflicts with exact supplied lyrics")
    return spec


def validate_direction(value):
    if (not isinstance(value,dict) or set(value)!={"opening","vocal","narrator","section_plan"}
            or value["opening"] not in cd.OPENINGS or value["vocal"] not in cd.VOICES
            or not _text(value["narrator"],500)
            or not isinstance(value["section_plan"],list) or not 1<=len(value["section_plan"])<=24):
        raise ValueError("Invalid typed musical direction")
    ids=[]
    for item in value["section_plan"]:
        if (not isinstance(item,dict) or set(item)!={"section","purpose"}
                or not _section_id(item["section"]) or not _text(item["purpose"],1000)):
            raise ValueError("Invalid typed section purpose")
        ids.append(item["section"])
    counts={}
    for key in ids:
        name,number=key.rsplit("#",1)
        counts[name]=counts.get(name,0)+1
        if int(number)!=counts[name]:
            raise ValueError("Invalid section occurrence order")
    if value["opening"]=="instrumental_intro" and (ids[0]!="intro#1" or len(ids)<2):
        raise ValueError("Typed instrumental opening needs a planned intro")
    if value["opening"]=="direct_vocal" and ids[0].split("#")[0] in ("intro","interlude"):
        raise ValueError("Typed direct vocal needs a sung opening")
    return value


def _style_cues(style,vocal):
    # Only literal descriptor conflicts are screened; no claim of acoustic voice
    # identity or complete natural-language semantic understanding.
    cues=set(re.findall(r"\b(?:male|female|duet|mixed|androgynous)\b",style.lower()))
    if vocal not in cues:
        raise ValueError("Positive style must state the chosen vocal identity")
    if vocal in ("male","female","androgynous") and cues-{vocal}:
        raise ValueError("Conflicting literal vocal identity cues in style")


def check_composer(music,spec):
    d=validate_direction(music["direction"])
    for k in ("opening","vocal","narrator"):
        if spec[k] is not None and d[k]!=spec[k]:
            raise ValueError("Composer conflicts with explicit "+k)
    if spec["style"] is not None and music["style"]!=spec["style"]:
        raise ValueError("Composer changed exact supplied style")
    _style_cues(music["style"],d["vocal"])
    plan={i["section"]:i["purpose"] for i in d["section_plan"]}
    if any(plan.get(k)!=v for k,v in spec["section_purposes"].items()):
        raise ValueError("Composer changed explicit section purpose")
    if spec["lyrics"] is not None:
        check_lyrics(music,spec["lyrics"],spec)
    constraints=spec["score_constraints"]
    if "section_order" in constraints and constraints["section_order"]["mode"]=="must":
        if list(plan)!=constraints["section_order"]["value"]:
            raise ValueError("Composer conflicts with explicit section order")
    return d


def check_lyrics(music,lyrics,spec):
    d=validate_direction(music["direction"])
    lyricist.validate({"lyrics":lyrics})
    if spec["lyrics"] is not None and lyrics!=spec["lyrics"]:
        raise ValueError("Exact supplied lyrics changed")
    if section_ids(lyrics)!=[i["section"] for i in d["section_plan"]] or opening_of(lyrics)!=d["opening"]:
        raise ValueError("Lyrics do not match typed opening and section plan")
    sung=[f"{g['name']}#{g['occurrence']}" for g in parse_lyrics(lyrics) if g["lines"]]
    constraint=spec["score_constraints"].get("sung_sections")
    if constraint and constraint["mode"]=="must" and sung!=constraint["value"]:
        raise ValueError("Lyrics conflict with explicit sung sections")
    return d


def intent_fields(music,spec,lyrics):
    d=check_composer(music,spec)
    check_lyrics(music,lyrics,spec)
    return {"schema":INTENT_SCHEMA,"direction":d,"requested":spec,
            "section_purposes":{i["section"]:i["purpose"] for i in d["section_plan"]},
            "constraints":{**spec["score_constraints"],"opening":{"mode":"must","value":d["opening"]},
                           "opening_timing":{"mode":"must","value":d["opening"]}}}
