"""Unified command line for offline analysis and explicit YuE2 Studio workflows."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from .music import ScoreError,parse_score,section_sequence,humanize_pitch
from .prosody import parse_lyrics,alignment,phrase_diagnostics
from .midi import probe
from .midi_events import compare_files,MIDIEventError
from .pipeline import run as run_pipeline
from .experiments import prepare,submit,reconcile,status
from .mcp import MCPError,Client,configured_endpoint,unpack


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog='yue2-director')
    sub=parser.add_subparsers(dest='command',required=True)
    work=sub.add_parser('run',help='Audit, humanize and optionally prepare A/B in one local command')
    work.add_argument('abc',type=Path)
    work.add_argument('--lyrics',required=True,type=Path)
    work.add_argument('--style',type=Path)
    work.add_argument('--out',required=True,type=Path)
    work.add_argument('--seed',type=int,default=42)
    work.add_argument('--max-edits',type=int,default=12)
    work.add_argument('--midi',action='store_true',help='Run score_to_midi after offline stages; never song_create')
    work.add_argument('--url',help='Local Studio URL if --midi enabled')
    work.add_argument('--title',default='YuE2 A/B')

    aud=sub.add_parser('audit',help='Validate ABC without contacting Studio')
    aud.add_argument('abc',type=Path)
    aud.add_argument('--lyrics',type=Path)
    variation=sub.add_parser('humanize',help='Produce a new ABC with chord-aware phrase variation')
    variation.add_argument('abc',type=Path)
    variation.add_argument('--lyrics',type=Path,required=True)
    variation.add_argument('--out',type=Path,required=True)
    variation.add_argument('--seed',type=int,default=42)
    variation.add_argument('--max-edits',type=int,default=12)

    midi=sub.add_parser('midi-probe',help='Convert ABC to MIDI through local MCP; no audio generation')
    midi.add_argument('abc',type=Path,nargs='+')
    midi.add_argument('--out',type=Path,required=True)
    midi.add_argument('--url',help='Explicit local Studio MCP endpoint; or use YUE2_MCP_URL')

    comp=sub.add_parser('midi-audit',help='Compare MIDI note events offline, no Studio access')
    comp.add_argument('--original',type=Path,required=True)
    comp.add_argument('--candidate',type=Path,required=True)
    comp.add_argument('--out',type=Path,required=True)
    comp.add_argument('--allowed-pitch-track',type=int,action='append')
    comp.add_argument('--enforce-pitch-only',action='store_true')

    p=sub.add_parser('ab-prepare',help='Create A/B requests and manifest offline; no audio jobs')
    p.add_argument('--original',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--lyrics',type=Path,required=True)
    p.add_argument('--style',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--title',default='YuE2 Music Director A/B')

    for command in ('ab-submit','ab-status','ab-recover'):
        sp=sub.add_parser(command)
        sp.add_argument('--arm',choices=('A','B'),required=True)
        sp.add_argument('--out',type=Path,required=True)
        if command != 'ab-recover':
            sp.add_argument('--url',help='Explicit loopback MCP URL; or YUE2_MCP_URL')
        if command=='ab-submit':
            sp.add_argument('--confirm-idle',action='store_true')
            sp.add_argument('--confirm-a-complete',action='store_true')
        if command=='ab-recover':
            sp.add_argument('--confirm-complete',action='store_true')

    ping=sub.add_parser('studio-check',help='Read-only local Studio status')
    ping.add_argument('--url')
    args=parser.parse_args(argv)
    try:
        if args.command=='run':
            result=run_pipeline(args.abc,args.lyrics,args.out,style=args.style,
                                seed=args.seed,max_edits=args.max_edits,
                                midi=args.midi,url=args.url,title=args.title)
        elif args.command=='audit':
            score=parse_score(args.abc.read_text(encoding='utf-8-sig'))
            result={'bars':score.counts,'sections':section_sequence(score),
                    'warnings':score.warnings,'errors':[]}
            if args.lyrics:
                text=args.lyrics.read_text(encoding='utf-8-sig')
                groups=parse_lyrics(text)
                result['warnings']+=alignment(score,groups)
                if not any(w.startswith('SECTION MISMATCH') for w in result['warnings']):
                    result['phrases']=phrase_diagnostics(score,groups)
        elif args.command=='humanize':
            if not 0<=args.max_edits<=100:
                raise ValueError('max-edits must be 0 to 100')
            if args.abc.resolve()==args.out.resolve():
                raise ValueError('output must not overwrite the source ABC')
            if args.out.exists() or args.out.with_suffix('.report.json').exists():
                raise ValueError('output or report already exists; refusing overwrite')
            score=args.abc.read_text(encoding='utf-8-sig')
            lyrics=args.lyrics.read_text(encoding='utf-8-sig')
            candidate=humanize_pitch(score,lyrics,args.seed,args.max_edits)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(candidate['abc'],encoding='utf-8')
            report=args.out.with_suffix('.report.json')
            report.write_text(json.dumps(candidate['report'],indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            result={'abc':str(args.out),'report':str(report),
                    'changes':candidate['report']['change_count'],
                    'warnings':candidate['report']['warnings']}
        elif args.command=='midi-probe':
            result=probe(args.abc,args.out,args.url)
        elif args.command=='midi-audit':
            if args.out.exists():
                raise ValueError('MIDI audit report exists; refusing overwrite')
            result=compare_files(args.original,args.candidate,args.allowed_pitch_track)
            if args.enforce_pitch_only and (result['timing_changes'] or result['velocity_changes']):
                raise MIDIEventError('Non-pitch changes detected during pitch-only audit')
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        elif args.command=='ab-prepare':
            result=prepare(args.original,args.candidate,args.lyrics,args.style,
                           args.out,args.seed,args.title)
        elif args.command=='ab-submit':
            result=submit(args.out,args.arm,args.url,args.confirm_idle,args.confirm_a_complete)
        elif args.command=='ab-recover':
            result=reconcile(args.out,args.arm,args.confirm_complete)
        elif args.command=='ab-status':
            result=status(args.out,args.arm,args.url)
        elif args.command=='studio-check':
            client=Client(configured_endpoint(args.url)).connect()
            names={x.get('name') for x in client.tools()}
            if 'studio_status' not in names:
                raise ValueError('Connected server does not have studio_status')
            result={'protocol':client.version,'status':unpack(client.call('studio_status',{}))}
        else:
            raise ValueError('Unknown command')
        print(json.dumps(result,indent=2,ensure_ascii=False,default=str))
        return 0
    except (ScoreError,MIDIEventError,MCPError,ValueError,OSError,UnicodeError,KeyError,TypeError) as exc:
        print('ERROR:',str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
