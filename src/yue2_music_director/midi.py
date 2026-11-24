"""MCP score_to_midi compatibility check. Does not generate audio."""
from __future__ import annotations
import base64
import binascii
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from .mcp import Client,configured_endpoint
from .music import parse_score

MAX_MIDI=1_500_000
MAX_ABC=1_024_000


def extract_midi(response) -> bytes:
    candidates=[]
    if isinstance(response,dict):
        candidates.append(response.get('structuredContent'))
        candidates.extend(response.get('content',[]))
        candidates.append(response)

    def seek(item,depth=0):
        if depth>6:
            return None
        if isinstance(item,dict):
            if item.get('type')=='text':
                value=item.get('text','')
                try:return seek(json.loads(value),depth+1)
                except (ValueError,TypeError):return seek(value,depth+1)
            for name in ('data','midi_base64','base64','midi','file','result','output','resource'):
                if name in item:
                    value=seek(item[name],depth+1)
                    if value is not None:return value
        if isinstance(item,list):
            for elem in item[:20]:
                value=seek(elem,depth+1)
                if value is not None:return value
        if isinstance(item,str):
            value=item.strip()
            if value.startswith('data:') and ',' in value:
                value=value.split(',',1)[1]
            if len(value)>2_000_000 or len(value)<24:
                return None
            if not re.fullmatch(r'[A-Za-z0-9+/=\s]+',value):
                return None
            try:
                decoded=base64.b64decode(value,validate=True)
            except (ValueError,binascii.Error):
                return None
            if decoded.startswith(b'MThd'):
                return decoded
        return None
    for candidate in candidates:
        found=seek(candidate)
        if found is not None:
            if len(found)>MAX_MIDI:
                raise ValueError('MIDI exceeds size limit')
            return found
    raise ValueError('MCP result does not contain valid base64 MIDI')


def midi_header(data: bytes) -> dict:
    if len(data)<22 or data[:4]!=b'MThd':
        raise ValueError('Missing MIDI header')
    header_size=int.from_bytes(data[4:8],'big')
    if header_size<6 or len(data)<8+header_size:
        raise ValueError('Invalid MIDI header length')
    fmt=int.from_bytes(data[8:10],'big')
    count=int.from_bytes(data[10:12],'big')
    division=int.from_bytes(data[12:14],'big')
    if fmt not in (0,1,2) or not 1<=count<=1024 or division==0:
        raise ValueError('Invalid MIDI metadata')
    cursor=8+header_size
    for index in range(count):
        if cursor+8>len(data) or data[cursor:cursor+4]!=b'MTrk':
            raise ValueError(f'Missing track {index}')
        size=int.from_bytes(data[cursor+4:cursor+8],'big')
        cursor+=size+8
        if cursor>len(data):
            raise ValueError('Truncated track')
    if cursor != len(data):
        raise ValueError('Unexpected trailing MIDI data')
    return {'format':fmt,'tracks':count,'division':division,'bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest()}


def probe(sources: list[Path],out: Path,url: str | None=None,client_factory=Client):
    if not sources:
        raise ValueError('At least one ABC source is required')
    client=client_factory(configured_endpoint(url))
    client.connect()
    tools={item.get('name'):item for item in client.tools()}
    schema=tools.get('score_to_midi',{}).get('inputSchema',{})
    if 'abc' not in schema.get('properties',{}):
        raise ValueError('Connected Studio does not expose score_to_midi(abc)')
    out.mkdir(parents=True,exist_ok=True)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),
            'note':'MIDI conversion proves compatibility, not vocal or audio quality','results':[]}
    for index,source in enumerate(sources,1):
        raw=source.read_bytes()
        if len(raw)>MAX_ABC:
            raise ValueError('ABC exceeds 1MB limit')
        abc=raw.decode('utf-8-sig')
        parse_score(abc)
        response=client.call('score_to_midi',{'abc':abc})
        midi=extract_midi(response)
        meta=midi_header(midi)
        target=out/f'{index:02d}_{source.stem}.mid'
        if target.exists():
            raise ValueError('Output MIDI already exists; refusing overwrite')
        target.write_bytes(midi)
        report['results'].append({'source':str(source),'output':str(target),
                                  'source_sha256':hashlib.sha256(raw).hexdigest(),'midi':meta})
    path=out/'midi_probe_report.json'
    if path.exists(): raise ValueError('Report already exists; refusing overwrite')
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return report
