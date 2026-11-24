"""Read-only, fail-closed checks for the restricted YuE2 ABC score grammar.

This is not a general-purpose ABC parser. It never edits the score.
"""
from __future__ import annotations
from collections import defaultdict
from fractions import Fraction
import re

_TOKEN = re.compile(r'(?:(?:\^\^|__|\^|_|=)?[A-Ga-g][,\']*|[zx])(?:\d+(?:/\d+)?|/\d*|/+)?-?|Z\d*')
_CHORD = re.compile(r'"(?:[^"\\]|\\.)*"')


class UnsupportedScore(ValueError):
    pass


def _duration(token: str) -> Fraction:
    bare = re.sub(r'^(?:\^\^|__|\^|_|=)?[A-Ga-g][,\']*|^[zxZ]', '', token).rstrip('-')
    if not bare:
        return Fraction(1)
    if bare.startswith('/'):
        if bare.strip('/') == '':
            return Fraction(1, 2 ** len(bare))
        return Fraction(1, int(bare[1:]))
    if '/' in bare:
        n, d = bare.split('/', 1)
        return Fraction(int(n), int(d))
    return Fraction(int(bare))


def validate_score(text: str) -> dict:
    """Return voice bar counts, sections, errors and warnings, without side effects.

    A Z multi-bar rest counts integer measures. Unsupported constructs fail.
    """
    headers: dict[str, str] = {}
    active_voice: str | None = None
    bars: dict[str, int] = defaultdict(int)
    sections: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    music: list[tuple[int, str, str]] = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if line.startswith('%'):
            sections.append(line[1:].strip().lower())
            continue
        if re.match(r'^[A-Za-z]:', line):
            key, value = line[0], line[2:].strip()
            if key == 'V':
                active_voice = value.split()[0] if value else None
            else:
                headers[key] = value
            continue
        if not active_voice:
            raise UnsupportedScore(f'line {n}: notes before voice declaration')
        music.append((n, active_voice, line))
    if headers.get('M') is None or headers.get('L') is None:
        raise UnsupportedScore('M: and L: headers required')
    try:
        top, bottom = map(int, headers['M'].split('/'))
        unit_top, unit_bottom = map(int, headers['L'].split('/'))
        expected = Fraction(top, bottom) / Fraction(unit_top, unit_bottom)
    except (ValueError, ZeroDivisionError):
        raise UnsupportedScore('invalid M: or L: header') from None
    if expected <= 0:
        raise UnsupportedScore('invalid bar duration')
    for n, voice, line in music:
        for raw_measure in line.split('|'):
            if not raw_measure.strip():
                continue
            measure = _CHORD.sub('', raw_measure)
            remaining = measure.replace(' ', '').replace('\t', '')
            if re.fullmatch(r'Z\d*', remaining):
                bars[voice] += int(remaining[1:] or 1)
                continue
            duration = Fraction(0)
            index = 0
            while index < len(remaining):
                match = _TOKEN.match(remaining, index)
                if not match or match.group().startswith('Z'):
                    raise UnsupportedScore(f'line {n}: unrecognized token near {remaining[index:index+12]!r}')
                duration += _duration(match.group())
                index = match.end()
            bars[voice] += 1
            if duration != expected:
                errors.append(f'line {n}, {voice}: measure {bars[voice]} has {duration}, expected {expected}')
    if set(bars) != {'Vocal', 'Ins'}:
        errors.append(f'expected Vocal and Ins voices; found {sorted(bars)}')
    if len(set(bars.values())) > 1:
        errors.append(f'voice bar counts differ: {dict(bars)}')
    if not headers.get('T'):
        warnings.append('title is empty')
    if 'w' not in headers:
        warnings.append('syllable alignment not supplied')
    return {'bars': dict(bars), 'sections': sections, 'errors': errors, 'warnings': warnings}
