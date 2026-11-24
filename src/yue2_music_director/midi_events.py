"""Read-only Standard MIDI File event comparison (SMF 0/1 with PPQN timing).

No third-party dependencies, audio generation, or Studio communication.
Fail closed on malformed timing, truncated tracks or unsupported MIDI status.
"""
from __future__ import annotations
from collections import defaultdict,deque
from dataclasses import asdict,dataclass
from pathlib import Path
import hashlib

MAX_MIDI=20*1024*1024
MAX_EVENTS=1_000_000


class MIDIEventError(ValueError):
    pass


def vlq(raw: bytes,index: int) -> tuple[int,int]:
    value=0
    for _ in range(4):
        if index>=len(raw):
            raise MIDIEventError('Truncated variable length quantity')
        byte=raw[index]
        index+=1
        value=(value<<7)|(byte&127)
        if byte<128:
            return value,index
    raise MIDIEventError('MIDI variable length quantity is too large')


@dataclass(frozen=True)
class Note:
    track:int
    channel:int
    pitch:int
    start:int
    duration:int
    velocity:int
    order:int


def parse_midi_data(data: bytes) -> dict:
    if len(data)>MAX_MIDI:
        raise MIDIEventError('MIDI exceeds 20MiB')
    if len(data)<14 or data[:4]!=b'MThd':
        raise MIDIEventError('Not MIDI')
    hlen=int.from_bytes(data[4:8],'big')
    if hlen<6 or 8+hlen>len(data):
        raise MIDIEventError('Invalid MIDI header length')
    fmt=int.from_bytes(data[8:10],'big')
    tracks=int.from_bytes(data[10:12],'big')
    division=int.from_bytes(data[12:14],'big')
    if fmt not in (0,1) or not (1<=tracks<=1024) or division==0 or division&0x8000:
        raise MIDIEventError('Only SMF 0/1 PPQN MIDI supported')
    offset=8+hlen
    notes=[]
    note_on_offsets={}
    track_names={}
    tempos=[]
    signatures=[]
    sequence=0
    for track in range(tracks):
        if offset+8>len(data) or data[offset:offset+4]!=b'MTrk':
            raise MIDIEventError('Missing track chunk')
        size=int.from_bytes(data[offset+4:offset+8],'big')
        offset+=8
        end=offset+size
        if end>len(data):
            raise MIDIEventError('Truncated track chunk')
        payload_start=offset
        payload=data[offset:end]
        offset=end
        index=0
        tick=0
        status=None
        active=defaultdict(deque)
        events=0
        ended=False
        while index<len(payload):
            events+=1
            if events>MAX_EVENTS:
                raise MIDIEventError('Excessive MIDI events')
            delta,index=vlq(payload,index)
            tick+=delta
            if index>=len(payload):
                raise MIDIEventError('Truncated MIDI event')
            byte=payload[index]
            if byte>=0x80:
                status=byte
                index+=1
            elif status is None:
                raise MIDIEventError('Invalid running status')
            if status==0xff:
                if index>=len(payload):
                    raise MIDIEventError('Incomplete metadata')
                meta=payload[index]
                index+=1
                length,index=vlq(payload,index)
                if index+length>len(payload):
                    raise MIDIEventError('Truncated metadata')
                chunk=payload[index:index+length]
                index+=length
                status=None
                if meta==0x03:
                    track_names.setdefault(track,[]).append(chunk.decode('utf-8',errors='replace'))
                if meta==0x51:
                    if length!=3:raise MIDIEventError('Invalid tempo meta')
                    tempos.append((tick,int.from_bytes(chunk,'big')))
                elif meta==0x58:
                    if length<2:raise MIDIEventError('Invalid meter meta')
                    signatures.append((tick,chunk[0],chunk[1]))
                elif meta==0x2f:
                    if length or index!=len(payload):
                        raise MIDIEventError('Invalid end-of-track')
                    ended=True
                    break
                continue
            if status in (0xf0,0xf7):
                length,index=vlq(payload,index)
                if index+length>len(payload):
                    raise MIDIEventError('Truncated sysex')
                index+=length
                status=None
                continue
            if status>=0xf0:
                raise MIDIEventError('Unsupported system MIDI message')
            kind=status>>4
            channel=status&15
            nbytes=1 if kind in (0xc,0xd) else 2
            if index+nbytes>len(payload) or any(x>=128 for x in payload[index:index+nbytes]):
                raise MIDIEventError('Truncated channel message')
            a=payload[index]
            b=payload[index+1] if nbytes==2 else 0
            index+=nbytes
            if kind==0x9 and b>0:
                note_on_offsets[sequence]=payload_start+index-1
                active[(channel,a)].append((tick,b,sequence))
                sequence+=1
            elif kind==0x8 or (kind==0x9 and b==0):
                if not active[(channel,a)]:
                    raise MIDIEventError('Note off without matching note on')
                start,velocity,order=active[(channel,a)].popleft()
                if tick<start:
                    raise MIDIEventError('Negative MIDI note length')
                notes.append(Note(track,channel,a,start,tick-start,velocity,order))
        if not ended:
            raise MIDIEventError('Missing MIDI end-of-track')
        if any(queue for queue in active.values()):
            raise MIDIEventError('Dangling MIDI note on')
    if offset!=len(data):
        raise MIDIEventError('Trailing bytes after last MIDI track')
    notes.sort(key=lambda e:(e.track,e.order))
    return {'format':fmt,'tracks':tracks,'division':division,
            'tempos':sorted(tempos),'signatures':sorted(signatures),'notes':notes,
            'note_on_offsets':note_on_offsets,'track_names':track_names}


def compare_midi_data(original: bytes,candidate: bytes,allowed_pitch_tracks: list[int] | None=None) -> dict:
    a=parse_midi_data(original)
    b=parse_midi_data(candidate)
    for field in ('format','tracks','division','tempos','signatures'):
        if a[field]!=b[field]:
            raise MIDIEventError(f'MIDI metadata differs: {field}')
    if len(a['notes'])!=len(b['notes']):
        raise MIDIEventError('MIDI note counts differ')
    counters={'pitch_changes':0,'timing_changes':0,'velocity_changes':0}
    changed_tracks=set()
    changes=[]
    for na,nb in zip(a['notes'],b['notes']):
        if (na.track,na.channel)!=(nb.track,nb.channel):
            raise MIDIEventError('MIDI track/channel note ordering differs')
        pitch=na.pitch!=nb.pitch
        timing=(na.start,na.duration)!=(nb.start,nb.duration)
        velocity=na.velocity!=nb.velocity
        if any((pitch,timing,velocity)):
            if pitch and allowed_pitch_tracks is not None and na.track not in allowed_pitch_tracks:
                raise MIDIEventError(f'Pitch changed in protected MIDI track {na.track}')
            counters['pitch_changes']+=int(pitch)
            counters['timing_changes']+=int(timing)
            counters['velocity_changes']+=int(velocity)
            changed_tracks.add(na.track)
            changes.append({'track':na.track,'source_pitch':na.pitch,'candidate_pitch':nb.pitch,
                            'source_start':na.start,'candidate_start':nb.start,
                            'source_duration':na.duration,'candidate_duration':nb.duration,
                            'source_velocity':na.velocity,'candidate_velocity':nb.velocity})
    return {'notes':len(a['notes']),'tracks':a['tracks'],'division':a['division'],
            'changed_tracks':sorted(changed_tracks),'changes':changes,
            'original_sha256':hashlib.sha256(original).hexdigest(),
            'candidate_sha256':hashlib.sha256(candidate).hexdigest(),**counters}


def compare_files(original:Path,candidate:Path,allowed_pitch_tracks:list[int] | None=None) -> dict:
    return compare_midi_data(original.read_bytes(),candidate.read_bytes(),allowed_pitch_tracks)
