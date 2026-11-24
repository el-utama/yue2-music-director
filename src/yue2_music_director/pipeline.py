"""Safe offline-oriented one-command orchestration for YuE2 Music Director.

Stages: score audit -> lyric diagnostics -> pitch candidate -> optional A/B
manifest -> optional MIDI conversion. Never calls song_create.
"""
from __future__ import annotations
import json
from pathlib import Path
from .music import parse_score, section_sequence, humanize_pitch
from .prosody import parse_lyrics,alignment,phrase_diagnostics
from .experiments import prepare
from .midi import probe


def run(abc:Path,lyrics:Path,out:Path,style:Path | None=None,seed:int=42,
        max_edits:int=12,midi:bool=False,url:str | None=None,title:str='YuE2 A/B',
        profile:str='conservative') -> dict:
    if not 1<=max_edits<=100:
        raise ValueError('run requires 1-100 maximum edits; use audit for no-change analysis')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output directory already contains files; use a fresh output directory')
    if not abc.is_file() or not lyrics.is_file():
        raise ValueError('ABC and lyric text files are required')
    source=abc.read_text(encoding='utf-8-sig')
    lyric_text=lyrics.read_text(encoding='utf-8-sig')
    parsed=parse_score(source)
    groups=parse_lyrics(lyric_text)
    warnings=alignment(parsed,groups)
    if any(x.startswith('SECTION MISMATCH') for x in warnings):
        raise ValueError('; '.join(warnings))
    diagnostics=phrase_diagnostics(parsed,groups)
    result=humanize_pitch(source,lyric_text,seed,max_edits,profile=profile)
    if result['report']['change_count']==0:
        raise ValueError('No safe pitch candidates for this score; no output written')
    if style is not None and not style.is_file():
        raise ValueError('Style text file does not exist')
    out.mkdir(parents=True,exist_ok=True)
    candidate=out/'candidate_pitch.abc'
    report=out/'score_report.json'
    if candidate.exists() or report.exists():
        raise ValueError('Unexpected output collision')
    candidate.write_text(result['abc'],encoding='utf-8')
    report.write_text(json.dumps({
        'original':str(abc),'candidate':str(candidate),
        'bars':parsed.counts,'sections':section_sequence(parsed),
        'diagnostics':diagnostics,'warnings':warnings,
        'humanization':result['report']
    },indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    summary={'candidate':str(candidate),'report':str(report),
             'pitch_changes':result['report']['change_count'],
             'audio_jobs_created':0}
    if style is not None:
        prepare(abc,candidate,lyrics,style,out/'ab',seed,title)
        summary['ab_manifest']=str(out/'ab'/'manifest.json')
    if midi:
        probe([abc,candidate],out/'midi',url)
        summary['midi_report']=str(out/'midi'/'midi_probe_report.json')
    return summary
