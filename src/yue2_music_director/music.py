"""Strict, non-destructive subset parser and phrase-aware pitch humanizer for YuE2 ABC.

No arbitrary ABC eval, no LLM dependency, no network. Unknown notation fails closed.
Supports separate Vocal/Ins voice sections, note/rest/tie/chord tokens and Z rests.
This does not provide syllable-to-note alignment or acoustic performance control.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import random
import re

NOTE = re.compile(r"(?P<acc>\^\^|__|\^|_|=)?(?P<letter>[A-Ga-g])(?P<oct>[,']*)(?P<dur>\d+(?:/\d+)?|/\d*|/+)?(?P<tie>-)?")
REST = re.compile(r"(?P<sym>[zxZ])(?P<dur>\d+(?:/\d+)?|/\d*|/+)?")
CHORD = re.compile(r'"(?:[^"\\]|\\.)*"')
NATURAL = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
SHARP_ORDER = 'FCGDAEB'
FLAT_ORDER = 'BEADGCF'
FIFTHS = {'C':0,'G':1,'D':2,'A':3,'E':4,'B':5,'F#':6,'C#':7,
          'F':-1,'Bb':-2,'Eb':-3,'Ab':-4,'Db':-5,'Gb':-6,'Cb':-7}
CHORD_PATTERN = re.compile(r'^([A-G])([b#]?)(m?)(maj7|7)?(?:/[A-G][b#]?)?$')


class ScoreError(ValueError):
    """Invalid or unsupported YuE2 ABC subset."""


@dataclass(frozen=True)
class Event:
    voice: str
    bar: int                 # zero-based within voice
    section: str             # e.g. chorus#2
    kind: str                # note, rest or multirest
    raw: str
    line: int
    start: int               # character offsets within line
    end: int
    offset: Fraction
    duration: Fraction
    chord: str
    pitch: int | None = None
    letter: str = ''
    octave: str = ''
    tied: bool = False
    accidental: str = ''


def duration(symbol: str | None) -> Fraction:
    if not symbol:
        return Fraction(1)
    if symbol.startswith('/'):
        if symbol.strip('/') == '':
            return Fraction(1, 2 ** len(symbol))
        return Fraction(1, int(symbol[1:]))
    if '/' in symbol:
        a, b = symbol.split('/', 1)
        return Fraction(int(a), int(b))
    return Fraction(int(symbol))


def key_signature(key: str) -> dict[str, int]:
    if key not in FIFTHS:
        raise ScoreError('unsupported key: '+key)
    n = FIFTHS[key]
    order = SHARP_ORDER if n > 0 else FLAT_ORDER
    return {letter: (1 if n > 0 else -1) for letter in order[:abs(n)]}


def chord_tones(chord: str) -> set[int] | None:
    match = CHORD_PATTERN.fullmatch(chord)
    if not match:
        return None
    letter, accidental, minor, seventh = match.groups()
    root = (NATURAL[letter] + {'':0, 'b':-1, '#':1}[accidental]) % 12
    steps = [0, 3 if minor else 4, 7]
    if seventh:
        steps.append(11 if seventh == 'maj7' else 10)
    return {(root + step) % 12 for step in steps}


def note_pitch(letter: str, octave_marks: str, acc: str, signature: dict,
               carried: dict[tuple, int]) -> int:
    upper = letter.upper()
    octave = (5 if letter.islower() else 4) + octave_marks.count("'") - octave_marks.count(',')
    if acc:
        adjustment = {'^':1,'^^':2,'_':-1,'__':-2,'=':0}[acc]
        carried[(upper, octave)] = adjustment
    else:
        adjustment = carried.get((upper, octave), signature.get(upper, 0))
    return 12 * (octave + 1) + NATURAL[upper] + adjustment


def normalize_section(name: str) -> str:
    name = name.strip().lower().replace('_','-')
    if name.startswith('verse'): return 'verse'
    if name.startswith('pre-chorus') or name.startswith('pre chorus'): return 'pre-chorus'
    if name.startswith('chorus'): return 'chorus'
    if name.startswith('bridge'): return 'bridge'
    if name in ('instrumental break','instrumental','interlude'): return 'interlude'
    if name.startswith('intro'): return 'intro'
    if name.startswith('outro'): return 'outro'
    return name


@dataclass
class Score:
    source: str
    lines: list[str]
    headers: dict[str, str]
    events: list[Event]
    bar_events: dict[str, list[list[Event]]]
    bar_chords: dict[tuple[str, int], list[str]]
    sections: dict[str, list[str]]
    bar_units: Fraction
    warnings: list[str]

    @property
    def counts(self) -> dict[str, int]:
        return {v:len(bars) for v, bars in self.bar_events.items()}


def parse_score(source: str) -> Score:
    lines = source.splitlines(keepends=True)
    headers: dict[str, str] = {}
    bar_events: dict[str, list[list[Event]]] = defaultdict(list)
    bar_chords: dict[tuple[str,int], list[str]] = {}
    sections: dict[str, list[str]] = defaultdict(list)
    all_events: list[Event] = []
    current_voice: str | None = None
    current_section = 'unmarked#1'
    section_counts: dict[str,int] = defaultdict(int)
    for i,line in enumerate(lines):
        content = line.rstrip('\r\n')
        trimmed = content.strip()
        if not trimmed:
            continue
        if trimmed.startswith('%'):
            section = normalize_section(trimmed[1:])
            section_counts[section] += 1
            current_section = f'{section}#{section_counts[section]}'
            continue
        if re.match(r'^[A-Za-z]:', trimmed):
            key = trimmed[0]
            value = trimmed[2:].strip()
            if key == 'V':
                current_voice = value.split()[0] if value else None
                if current_voice not in ('Vocal','Ins'):
                    raise ScoreError(f'line {i+1}: unsupported voice {current_voice}')
            else:
                headers[key] = value
            continue
        if current_voice is None:
            raise ScoreError(f'line {i+1}: notes without V: declaration')
        signature = key_signature(headers.get('K', ''))
        pieces = content.split('|')
        cursor = 0
        for piece in pieces:
            if not piece.strip():
                cursor += len(piece) + 1
                continue
            bar_index = len(bar_events[current_voice])
            found: list[Event] = []
            active_chord = ''
            chords: list[str] = []
            carried: dict[tuple,int] = {}
            offset = Fraction(0)
            at = 0
            while at < len(piece):
                if piece[at].isspace():
                    at += 1
                    continue
                if piece[at] == '"':
                    cm = CHORD.match(piece, at)
                    if not cm:
                        raise ScoreError(f'line {i+1}: unclosed chord symbol')
                    active_chord = cm.group()[1:-1]
                    chords.append(active_chord)
                    at = cm.end()
                    continue
                m = NOTE.match(piece, at)
                kind = 'note'
                if not m:
                    m = REST.match(piece, at)
                    kind = 'rest'
                if not m:
                    raise ScoreError(f'line {i+1}: unsupported token {piece[at:at+14]!r}')
                raw = m.group()
                dur = duration(m.group('dur'))
                if dur <= 0:
                    raise ScoreError('zero or negative note length')
                symbol = m.group('sym') if kind == 'rest' else ''
                if symbol == 'Z':
                    if found or piece[m.end():].strip():
                        raise ScoreError('Z multibar rest must occupy entire measure')
                    if dur.denominator != 1:
                        raise ScoreError('Z requires an integer bar count')
                    count = int(dur)
                    if count > 10000:
                        raise ScoreError('multibar rest too large')
                    ev = Event(current_voice,bar_index,current_section,'multirest',
                               raw,i,cursor+at,cursor+m.end(),Fraction(0),dur,active_chord)
                    all_events.append(ev)
                    for z in range(count):
                        sections[current_voice].append(current_section)
                        bar_events[current_voice].append([ev] if z == 0 else [])
                    found = []
                    offset = Fraction(-1)
                    at = m.end()
                    break
                pitch = None
                letter = octave_marks = accidental = ''
                tied = False
                if kind == 'note':
                    letter = m.group('letter')
                    octave_marks = m.group('oct')
                    accidental = m.group('acc') or ''
                    tied = bool(m.group('tie'))
                    pitch = note_pitch(letter,octave_marks,accidental,signature,carried)
                ev = Event(current_voice,bar_index,current_section,kind,raw,i,
                           cursor+at,cursor+m.end(),offset,dur,active_chord,
                           pitch,letter,octave_marks,tied,accidental)
                found.append(ev)
                all_events.append(ev)
                offset += dur
                at = m.end()
            if offset >= 0:
                bar_events[current_voice].append(found)
                sections[current_voice].append(current_section)
                if chords:
                    bar_chords[(current_voice,bar_index)] = chords
                expected = headers.get('M')
                unit = headers.get('L')
                if expected and unit:
                    try:
                        n,d = map(int,expected.split('/'))
                        ln,ld = map(int,unit.split('/'))
                        target = Fraction(n,d)/Fraction(ln,ld)
                    except (ValueError,ZeroDivisionError):
                        raise ScoreError('invalid meter or note unit') from None
                    if offset != target:
                        raise ScoreError(f'{current_voice} bar {bar_index+1}: '
                                         f'{offset} note units, expected {target}')
            cursor += len(piece)+1
    if not headers.get('M') or not headers.get('L') or not headers.get('K'):
        raise ScoreError('M:, L: and K: headers are required')
    n,d = map(int,headers['M'].split('/'))
    ln,ld = map(int,headers['L'].split('/'))
    if min(n,d,ln,ld) <= 0:
        raise ScoreError('invalid meter values')
    expected = Fraction(n,d)/Fraction(ln,ld)
    if set(bar_events) != {'Vocal','Ins'}:
        raise ScoreError(f'expected Vocal and Ins, found {sorted(bar_events)}')
    if len(bar_events['Vocal']) != len(bar_events['Ins']):
        raise ScoreError('Vocal/Ins bar counts differ')
    for voice in ('Vocal','Ins'):
        notes = [e for e in all_events if e.voice==voice and e.kind != 'multirest']
        for idx,e in enumerate(notes):
            if e.tied:
                if idx+1 == len(notes) or notes[idx+1].kind!='note' or notes[idx+1].pitch!=e.pitch:
                    raise ScoreError(f'invalid tie at {voice} bar {e.bar+1}')
    warnings = []
    if not headers.get('T'):
        warnings.append('Empty ABC title')
    warnings.append('No proven syllable-to-note mapping; do not infer exact vocal prosody')
    return Score(source,lines,headers,all_events,dict(bar_events),bar_chords,
                 dict(sections),expected,warnings)


def section_sequence(score: Score) -> list[str]:
    out = []
    previous = None
    for value in score.sections['Vocal']:
        if value != previous:
            out.append(value.split('#',1)[0])
            previous = value
    return out


def repeated_pitch_fraction(score: Score, voice='Vocal') -> float:
    notes = [e.pitch for e in score.events if e.voice==voice and e.kind=='note']
    if len(notes) < 2: return 0.0
    return sum(a==b for a,b in zip(notes,notes[1:])) / (len(notes)-1)


def patch_score(score: Score, changes: list[dict]) -> str:
    lines = score.lines[:]
    by_line: dict[int,list[dict]] = defaultdict(list)
    seen = set()
    for change in changes:
        loc = (change['line'],change['start'],change['end'])
        if loc in seen:
            raise ScoreError('overlapping edit')
        seen.add(loc)
        by_line[change['line']].append(change)
    for i,patches in by_line.items():
        for edit in sorted(patches,key=lambda x:x['start'],reverse=True):
            if lines[i][edit['start']:edit['end']]!=edit['old']:
                raise ScoreError('source changed since planning edits')
            lines[i] = lines[i][:edit['start']] + edit['new'] + lines[i][edit['end']:]
    return ''.join(lines)


def humanize_pitch(source: str, lyrics: str, seed=42, max_edits=12,
                   protect=('chorus','intro','interlude','outro')) -> dict:
    """Make conservative, chord-aware phrase-level edits; preserve timing and hook.

    A phrase is provisionally a group of bars allocated to one lyric line.
    This is *not* a verified syllable alignment. Rhythm editing is deliberately
    disabled until a genuine lyric-to-note alignment is supplied.
    """
    from .prosody import parse_lyrics, alignment
    score = parse_score(source)
    lyrics_sections = parse_lyrics(lyrics)
    warnings = alignment(score,lyrics_sections)
    if any(x.startswith('SECTION MISMATCH') for x in warnings):
        raise ScoreError('; '.join(warnings))
    signature = key_signature(score.headers['K'])
    rng = random.Random(seed)
    candidates: list[tuple[float,dict]] = []
    vocal_notes = [e for e in score.events if e.voice=='Vocal' and e.kind=='note']
    vocal_sections = score.sections['Vocal']
    # Repeated section occurrence => exact lyric group, e.g. chorus#2.
    grouped = []
    last = None
    for s in vocal_sections:
        if s != last:
            grouped.append((s,[]))
            last = s
        grouped[-1][1].append(len(grouped[-1][1]))
    phrase_count = {}
    for item in lyrics_sections:
        key = item['name']+'#'+str(item['occurrence'])
        phrase_count[key] = max(1,len(item['lines']))
    indices: dict[str,list[int]] = defaultdict(list)
    for i,sec in enumerate(vocal_sections):
        indices[sec].append(i)
    for index,e in enumerate(vocal_notes):
        category=e.section.split('#')[0]
        if category in protect or category not in ('verse','pre-chorus','bridge'):
            continue
        if e.accidental or e.tied or (index>0 and vocal_notes[index-1].tied):
            continue
        bar_notes = [x for x in score.bar_events['Vocal'][e.bar] if x.kind=='note']
        if len(bar_notes) < 3 or e is bar_notes[0] or e is bar_notes[-1]:
            continue
        locations=indices[e.section]
        line_total=phrase_count.get(e.section,1)
        local_bar=locations.index(e.bar)
        phrase = min(line_total-1, (local_bar*line_total)//max(1,len(locations)))
        first = (phrase*len(locations))//line_total
        last_bar = ((phrase+1)*len(locations)-1)//line_total
        # Guard phrase starts/ends as stronger melodic anchors.
        if local_bar in (first,last_bar):
            continue
        chords = score.bar_chords.get(('Vocal',e.bar),[])
        tones = chord_tones(chords[0]) if chords else None
        if not tones:
            continue
        prev = vocal_notes[index-1].pitch if index>0 else None
        nxt = vocal_notes[index+1].pitch if index+1<len(vocal_notes) else None
        options=[]
        for letter in 'ABCDEFG':
            variant=letter.lower() if e.letter.islower() else letter
            if variant==e.letter:
                continue
            new_pitch = note_pitch(variant,e.octave,'',signature,{})
            if new_pitch%12 not in tones or abs(new_pitch-e.pitch)>4:
                continue
            if prev is not None and abs(new_pitch-prev)>8: continue
            if nxt is not None and abs(new_pitch-nxt)>8: continue
            # Penalize replacing one repeated note with another duplicate.
            repeats_old = int(prev==e.pitch)+int(nxt==e.pitch)
            repeats_new = int(prev==new_pitch)+int(nxt==new_pitch)
            quality = 2*(repeats_old-repeats_new)-abs(new_pitch-e.pitch)*0.15
            if quality >= 0.2:
                options.append((quality,variant))
        if not options:
            continue
        options.sort(key=lambda v:v[0],reverse=True)
        best=options[0]
        replacement=e.raw.replace(e.letter+e.octave,best[1]+e.octave,1)
        if replacement == e.raw:
            continue
        edit = {'line':e.line,'start':e.start,'end':e.end,'old':e.raw,
                'new':replacement,'section':e.section,'bar':e.bar+1,
                'lyric_line_index':phrase+1,'pitch_before':e.pitch,
                'pitch_after':note_pitch(best[1],e.octave,'',signature,{})}
        candidates.append((best[0]+rng.random()*0.04,edit))
    candidates.sort(key=lambda item:item[0],reverse=True)
    chosen=[]
    used_phrases=set()
    for _,edit in candidates:
        key=(edit['section'],edit['lyric_line_index'])
        if key in used_phrases: continue
        if any(abs(edit['bar']-x['bar'])<=1 for x in chosen): continue
        chosen.append(edit)
        used_phrases.add(key)
        if len(chosen)>=max_edits: break
    result = patch_score(score,chosen)
    parsed = parse_score(result)
    if parsed.counts!=score.counts or parsed.bar_chords!=score.bar_chords:
        raise ScoreError('bar or chord preservation failed')
    if len(parsed.events)!=len(score.events):
        raise ScoreError('event count changed')
    for old,new in zip(score.events,parsed.events):
        if (old.voice,old.section,old.kind,old.duration,old.offset)!=(new.voice,new.section,new.kind,new.duration,new.offset):
            raise ScoreError('non-pitch structure changed')
        if old.voice=='Ins' or old.section.split('#')[0] in protect:
            if (old.raw,old.pitch)!=(new.raw,new.pitch):
                raise ScoreError('protected phrase or instrument changed')
    report = {'seed':seed,'max_edits':max_edits,'changes':chosen,
              'change_count':len(chosen),'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
              'output_sha256':hashlib.sha256(result.encode()).hexdigest(),
              'original_repeat_fraction':round(repeated_pitch_fraction(score),3),
              'candidate_repeat_fraction':round(repeated_pitch_fraction(parsed),3),
              'section_sequence':section_sequence(score),
              'warnings':warnings+score.warnings+['Pitch edits do not directly control vocal timbre, vibrato or microtiming.']}
    return {'abc':result,'report':report}
