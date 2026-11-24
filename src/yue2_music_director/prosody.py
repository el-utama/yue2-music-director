"""Lyric section and coarse phrase diagnostics; no invented syllable alignment."""
from __future__ import annotations
from collections import defaultdict
import re

SECTION = re.compile(r'^\s*\[([^\]]+)\]\s*$')
WORD = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")


def parse_lyrics(text: str) -> list[dict]:
    from .music import normalize_section
    counts = defaultdict(int)
    sections=[]
    current=None
    for line in text.splitlines():
        m=SECTION.fullmatch(line)
        if m:
            name=normalize_section(m.group(1))
            counts[name]+=1
            current={'name':name,'occurrence':counts[name],'lines':[]}
            sections.append(current)
        elif line.strip():
            if current is None:
                raise ValueError('lyric text before first [Section]')
            current['lines'].append(line.strip())
    if not sections:
        raise ValueError('no [Section] markers in lyrics')
    return sections


def estimate_syllables(line: str) -> int:
    """Rough English vowel-group estimate only; not phonetic transcription."""
    count=0
    for word in WORD.findall(line):
        word=word.lower()
        groups=re.findall(r'[aeiouy]+',word)
        n=len(groups)
        if word.endswith('e') and not word.endswith(('le','ye')) and n>1:
            n-=1
        count+=max(1,n)
    return count


def alignment(score, sections: list[dict]) -> list[str]:
    from .music import section_sequence
    found=section_sequence(score)
    provided=[section['name'] for section in sections]
    warnings=[]
    if found!=provided:
        warnings.append(f'SECTION MISMATCH score={found} lyrics={provided}')
    for item in sections:
        if item['name'] in ('verse','pre-chorus','chorus','bridge','outro') and not item['lines']:
            warnings.append('Empty vocal lyric section: '+item['name'])
        if any(estimate_syllables(line)==0 for line in item['lines']):
            warnings.append('Possible empty/unreadable syllable group')
    warnings.append('Lyric lines are mapped only to approximate bar groups; no verified syllable-to-note alignment')
    return warnings

def phrase_diagnostics(score, sections: list[dict]) -> list[dict]:
    """Coarse lyric-line-to-bar allocation, NOT a syllable-to-note alignment.

    Reports only quantities verifiable from the lyric text and parsed score.
    A flag means "review this phrase", not "the singer will be incorrect".
    """
    from .music import ScoreError, section_sequence
    if section_sequence(score) != [x['name'] for x in sections]:
        raise ScoreError('Cannot map phrases with mismatched section sequences')
    result=[]
    for group in sections:
        key=f"{group['name']}#{group['occurrence']}"
        bars=[i for i, section in enumerate(score.sections['Vocal']) if section==key]
        lines=group['lines']
        if not lines or not bars:
            continue
        for position,line in enumerate(lines):
            start=(position*len(bars))//len(lines)
            end=((position+1)*len(bars))//len(lines)
            selection=bars[start:end]
            events=[event for bar in selection for event in score.bar_events['Vocal'][bar]]
            notes=[event for event in events if event.kind=='note']
            rest_count=sum(event.kind=='rest' for event in events)
            syllables=estimate_syllables(line)
            ratio=round(len(notes)/syllables,2) if syllables else None
            result.append({
                'section':key,'line_index':position+1,'lyric':line,
                'approximate_syllables':syllables,'allocated_bars':len(selection),
                'notated_note_events':len(notes),'notated_rest_events':rest_count,
                'notes_per_estimated_syllable':ratio,
                'review_flags':(
                    ['few note events relative to estimated syllables']
                    if syllables and len(notes)<syllables*0.7
                    else []
                ) + (['zero bars allocated'] if not selection else [])
            })
    return result
