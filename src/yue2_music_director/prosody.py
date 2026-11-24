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
