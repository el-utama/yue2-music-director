"""Offline A/B preparation and explicit one-shot YuE2 song submission.

Critical invariant: persist journal BEFORE the single song_create POST.
Timeouts/unknown outcomes remain locked until manually reconciled.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import os
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, build_opener, ProxyHandler
from pathlib import Path
from .job_receipt import extract_song_job_id, AmbiguousJobReceipt
from .music import parse_score, section_sequence
from .prosody import parse_lyrics, alignment
from .mcp import Client, configured_endpoint, unpack, _NoRedirect
from .native_recognition import _busy_keys

MAX_SOURCE = 512_000
MAX_TEXT = 100_000


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj) -> bytes:
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path,obj: dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name('.'+path.name+'.tmp')
    with temp.open('w',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,indent=2,ensure_ascii=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp,path)


def _read(path: Path,size: int) -> tuple[str,str]:
    raw=path.read_bytes()
    if len(raw)>size:
        raise ValueError(f'File exceeds {size} bytes: {path}')
    return raw.decode('utf-8-sig'),_sha(raw)


def prepare(original: Path,candidate: Path,lyrics: Path,style: Path,root: Path,seed=42,
            title='YuE2 Music Director A/B'):
    if root.exists() and any(root.iterdir()):
        raise ValueError('Experiment output directory must be empty; use a new directory')
    inputs={}
    for name,path,size in [('A',original,MAX_SOURCE),('B',candidate,MAX_SOURCE),
                           ('lyrics',lyrics,MAX_TEXT),('style',style,MAX_TEXT)]:
        content,digest=_read(path,size)
        inputs[name]={'path':str(path.absolute()),'sha256':digest}
        inputs[name]['text']=content
    scores=[parse_score(inputs[arm]['text']) for arm in 'AB']
    if inputs['A']['text']==inputs['B']['text']:
        raise ValueError('A and B have identical ABC: not a useful experiment')
    # Controlled pitch-only A/B: timing, notes count, chords, instrument and hook
    # must match. This comparison is symbolic, NOT proof of acoustic causality.
    if len(scores[0].events)!=len(scores[1].events) or scores[0].bar_chords!=scores[1].bar_chords:
        raise ValueError('Score event count or chords differ')
    pitch_changes=0
    for a,b in zip(scores[0].events,scores[1].events):
        if (a.voice,a.section,a.kind,a.bar,a.offset,a.duration,a.chord)!=(
                b.voice,b.section,b.kind,b.bar,b.offset,b.duration,b.chord):
            raise ValueError('A/B contains a structural or rhythmic difference')
        if a.raw != b.raw and (a.kind!='note' or a.pitch==b.pitch):
            raise ValueError('A/B has a non-pitch symbol change')
        if a.pitch!=b.pitch:
            if a.voice!='Vocal' or a.section.split('#')[0] in (
                    'chorus','intro','outro','interlude'):
                raise ValueError('A/B changes protected vocals or instrument')
            pitch_changes+=1
    if not pitch_changes:
        raise ValueError('No actual vocal pitch changes between A and B')
    if scores[0].counts != scores[1].counts or section_sequence(scores[0]) != section_sequence(scores[1]):
        raise ValueError('A and B score structures differ')
    lyric_groups=parse_lyrics(inputs['lyrics']['text'])
    for score in scores:
        problems=alignment(score,lyric_groups)
        if any(x.startswith('SECTION MISMATCH') for x in problems):
            raise ValueError('; '.join(problems))
    if not inputs['style']['text'].strip():
        raise ValueError('Style must not be empty')
    common={'music_source':{'kind':'local'},'title':title,
            'style':inputs['style']['text'].strip(),'lyrics':inputs['lyrics']['text'].strip(),
            'seed':seed,'lm_seed':seed,'lm_batch_size':1,'synth_batch_size':1,
            'abc_continue':False,'lyric_timing':True,'adapters':[],'companion_scale':0}
    requests={arm:dict(common,abc=inputs[arm]['text']) for arm in 'AB'}
    paths={arm:root/f'{arm}_song_create.json' for arm in 'AB'}
    for arm in 'AB':_write(paths[arm],requests[arm])
    manifest={'version':'0.6','reference_policy':'stock-balanced-cuda-q8-v1','status':'PREPARED_NO_JOBS','created_utc':_now(),
              'sections':section_sequence(scores[0]),'seed':seed,
              'inputs':{k:{'path':v['path'],'sha256':v['sha256']} for k,v in inputs.items()},
              'requests':{arm:_sha(paths[arm].read_bytes()) for arm in 'AB'},
              'caveats':['Same seed does not guarantee identical performance',
                         'Syllable alignment is not verified; this is section-level matching only']}
    _write(root/'manifest.json',manifest)
    return manifest


def _verify(root: Path,arm: str):
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('status')!='PREPARED_NO_JOBS':
        raise ValueError('Invalid experiment manifest')
    path=root/f'{arm}_song_create.json'
    if _sha(path.read_bytes())!=manifest['requests'][arm]:
        raise ValueError('Request changed after preparation')
    request=json.loads(path.read_text(encoding='utf-8'))
    for name in ('A','B','lyrics','style'):
        entry=manifest['inputs'][name]
        text,hashvalue=_read(Path(entry['path']), MAX_SOURCE if name in 'AB' else MAX_TEXT)
        if hashvalue!=entry['sha256']:
            raise ValueError(f'Source changed: {name}')
        if name==arm and text!=request['abc']:
            raise ValueError('Source score changed')
        if name in ('lyrics','style') and text.strip()!=request[name]:
            raise ValueError('Text source changed')
    if request.get('music_source')!={'kind':'local'} or request.get('abc_continue') is not False:
        raise ValueError('Unsafe song request')
    if request.get('lyric_timing') is not True:
        raise ValueError('Lyric timing must be enabled')
    return manifest,request


def _load_journal(root: Path,arm: str) -> dict:
    return json.loads((root/f'journal_{arm}.json').read_text(encoding='utf-8'))


def confirm_stock_backbone(client,status):
    # A missing field is not a null selection. Older summaries may omit it.
    # The same native service exposes the authoritative selection directly.
    summary_present="own_model" in status
    if summary_present and status["own_model"] is not None:
        raise ValueError("Studio reports an active own-model override; stock reference blocked")
    endpoint=urlsplit(configured_endpoint(client.url))
    if endpoint.path!="/mcp":
        raise ValueError("Stock verification requires the standard /mcp endpoint")
    target=urlunsplit((endpoint.scheme,endpoint.netloc,"/setup/own-model","",""))
    opener=build_opener(ProxyHandler({}),_NoRedirect())
    with opener.open(Request(target,headers={"Accept":"application/json"},method="GET"),timeout=15) as response:
        if response.headers.get_content_type()!="application/json":
            raise ValueError("Own-model endpoint did not return JSON")
        raw=response.read(2_097_153)
    if len(raw)>2_097_152:
        raise ValueError("Own-model response exceeded read limit")
    own=json.loads(raw)
    if not isinstance(own,dict) or "selected" not in own or "download" not in own:
        raise ValueError("Native own-model selection unknown; stock reference blocked")
    if own["selected"] is not None:
        raise ValueError("Native endpoint reports an active own-model override; stock reference blocked")
    if own.get("missing") is not False or own["download"] is not None:
        raise ValueError("Own-model missing/download status is not clear")
    return "summary_and_native" if summary_present else "native_selection"


def reference_configuration(client, status, request, defaults, capabilities):
    """Strict stock reference, not a claim of file-byte or waveform identity."""
    if request.get("adapters") != [] or type(request.get("companion_scale")) not in (int,float) or request["companion_scale"] != 0:
        raise ValueError("Reference request must explicitly disable adapters and companion")
    if request.get("lm_batch_size") != 1 or request.get("synth_batch_size") != 1:
        raise ValueError("Reference requires one composition and synthesis track")
    if _busy_keys(status):
        raise ValueError("Studio is not idle; do not discard existing work automatically")
    confirm_stock_backbone(client,status)
    models=unpack(client.call("models_status",{}))
    options=unpack(client.call("engine_options_get",{}))
    if not isinstance(models,dict) or not isinstance(options,dict):
        raise ValueError("Unrecognized model or engine status")
    if (models.get("ready") is not True or models.get("engine_ready") is not True
            or models.get("selected_profile_id")!="balanced"
            or "selected_component_ids" not in models or models["selected_component_ids"] not in (None,[])
            or "active" not in models or models["active"] is not None
            or "preset" not in models or models["preset"] is not None):
        raise ValueError("Stock profile check failed: "+", ".join(k for k,ok in {"ready":models.get("ready") is True,"engine_ready":models.get("engine_ready") is True,"balanced":models.get("selected_profile_id")=="balanced","stock_components":"selected_component_ids" in models and models["selected_component_ids"] in (None,[]),"no_download":"active" in models and models["active"] is None,"no_preset":"preset" in models and models["preset"] is None}.items() if not ok))
    installed=models.get("installed_components")
    if not isinstance(installed,list) or not {"backbone-q6","vae-f32"} <= set(installed):
        raise ValueError("Stock backbone and VAE installation not confirmed")
    opts=options.get("options")
    effective=options.get("in_effect")
    cache=options.get("kv_cache_now")
    if (not isinstance(opts,dict) or not isinstance(effective,dict) or not isinstance(cache,dict)
            or opts.get("backend")!="cuda" or opts.get("kv_cache")!="q8"
            or cache.get("q8") is not True or effective.get("flash_attention") is not True
            or not isinstance(status.get("engine"),dict)
            or any(effective.get(k)!=status["engine"].get(k) for k in
                   ("max_seq","max_seq_reason","flash_attention","nar_chunk_seconds"))
            or type(effective.get("max_seq")) is not int or effective["max_seq"]<=0
            or opts.get("extra_args") not in (None,"",[])
            or opts.get("engine_bin") not in (None,"")):
        raise ValueError("Expected consistent CUDA/Q8 reference engine, flash attention and no custom executable/flags")
    if not isinstance(defaults,dict) or not defaults or not isinstance(capabilities,dict) or not capabilities:
        raise ValueError("Unrecognized generation defaults or capabilities")
    # Only stable settings, not live free-memory estimates, process IDs, or jobs.
    return {"profile":"balanced","own_model":None,"engine_id":models.get("engine_id"),
            "backbone_component":"backbone-q6","vae_component":"vae-f32",
            "options":opts,"effective":{"max_seq":effective.get("max_seq"),
                "max_seq_reason":effective.get("max_seq_reason"),"flash_attention":True,
                "nar_chunk_seconds":effective.get("nar_chunk_seconds"),"q8":True},
            "defaults_sha":_sha(_canonical(defaults)),"capabilities_sha":_sha(_canonical(capabilities)),
            "adapters":[],"companion_scale":0,
            "actual_weight_bytes_verified":False}


def submit(root: Path,arm: str,url: str | None,confirm_idle: bool,confirm_a_complete=False,
           client_factory=Client) -> dict:
    if arm not in ('A','B'): raise ValueError('Invalid arm')
    if not confirm_idle:
        raise ValueError('Confirm Studio is idle explicitly using --confirm-idle')
    journal_file=root/f'journal_{arm}.json'
    if journal_file.exists():
        raise ValueError(f'{journal_file} already exists. Never repeat song_create')
    if arm=='B':
        if not confirm_a_complete:
            raise ValueError('Confirm A completed before B')
        if _load_journal(root,'A').get('state') not in ('COMPLETED_USER_CONFIRMED','COMPLETED'):
            raise ValueError('A not verified as completed')
    manifest,request=_verify(root,arm)
    client=client_factory(configured_endpoint(url))
    client.connect()
    tool_index={item.get('name'):item for item in client.tools()}
    names=set(tool_index)
    needed={'song_create','song_defaults','studio_status','studio_capabilities',
            'models_status','engine_options_get'}
    if not needed.issubset(names):
        raise ValueError('Missing Studio MCP tools: '+str(sorted(needed-names)))
    schema=tool_index['song_create'].get('inputSchema',{})
    properties=schema.get('properties',{})
    expected_fields={'music_source','style','lyrics','abc','abc_continue',
                     'lyric_timing','seed','lm_seed','lm_batch_size','synth_batch_size','adapters','companion_scale'}
    if not expected_fields.issubset(properties):
        raise ValueError('Studio song_create schema missing expected fields')
    defaults=unpack(client.call('song_defaults',{}))
    capabilities=unpack(client.call('studio_capabilities',{}))
    status=unpack(client.call('studio_status',{}))
    if manifest.get('reference_policy')!='stock-balanced-cuda-q8-v1':
        raise ValueError('Legacy manifest: prepare a new reference experiment; do not replay old jobs')
    reference=reference_configuration(client,status,request,defaults,capabilities)
    reference_sha=_sha(_canonical(reference))
    dh=_sha(_canonical(defaults))
    ch=_sha(_canonical(capabilities))
    if arm=='B':
        journal_a=_load_journal(root,'A')
        if (journal_a.get('defaults_sha')!=dh or journal_a.get('capabilities_sha')!=ch
                or journal_a.get('reference_configuration_sha')!=reference_sha):
            raise ValueError('Studio defaults or capabilities changed between A and B')
    journal={'arm':arm,'state':'SUBMISSION_ATTEMPTED','created_utc':_now(),
             'request_sha256':manifest['requests'][arm],
             'defaults_sha':dh,'capabilities_sha':ch,
             'reference_configuration_sha':reference_sha,'reference_configuration':reference,
             'status_sha':_sha(_canonical(status)),
             'warning':'Do not rerun submit on timeout or unknown outcome'}
    # Creation must fail if another process created the journal. O_EXCL prevents
    # concurrent submit calls from both proceeding.
    journal_file.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(journal_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(journal,f,indent=2)
        f.flush()
        os.fsync(f.fileno())
    try:
        response=client.call('song_create',request)
        try:
            job_id=extract_song_job_id(response)
            state='SUBMITTED' if job_id else 'UNKNOWN_RESPONSE'
        except AmbiguousJobReceipt:
            job_id=None
            state='UNKNOWN_RESPONSE'
        journal.update({'job_id':job_id,'state':state,'updated_utc':_now()})
        _write(journal_file,journal)
    except Exception:
        journal.update({'state':'UNKNOWN_AFTER_ATTEMPT','updated_utc':_now()})
        _write(journal_file,journal)
        raise
    return {'arm':arm,'state':state,'job_id':job_id}


def reconcile(root: Path,arm: str,confirm_complete=False):
    if not confirm_complete: raise ValueError('Explicit completion confirmation required')
    journal_file=root/f'journal_{arm}.json'
    journal=_load_journal(root,arm)
    if journal.get('state') not in ('SUBMITTED','UNKNOWN_RESPONSE','UNKNOWN_AFTER_ATTEMPT',
                                   'COMPLETED_USER_CONFIRMED'):
        raise ValueError('Journal state not eligible for manual reconciliation')
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if journal.get('request_sha256')!=manifest['requests'][arm]:
        raise ValueError('Journal does not match this experiment')
    journal['state']='COMPLETED_USER_CONFIRMED'
    journal['reconciled_utc']=_now()
    journal['recovery_basis']='user inspection of Studio; not independent verification'
    _write(journal_file,journal)
    return {'arm':arm,'state':journal['state'],'job_id':journal.get('job_id')}


def status(root: Path,arm: str,url: str | None=None,client_factory=Client):
    journal=_load_journal(root,arm)
    if journal.get('state')=='COMPLETED_USER_CONFIRMED':
        return {'arm':arm,'state':journal['state'],'verification':'user','job_id':journal.get('job_id')}
    job_id=journal.get('job_id')
    if not job_id:
        return {'arm':arm,'state':journal['state'],'warning':'No ID. Never resubmit.'}
    client=client_factory(configured_endpoint(url))
    client.connect()
    return {'arm':arm,'journal_state':journal['state'],
            'studio':unpack(client.call('song_job_get',{'job_id':job_id,'response_format':'concise'}))}
