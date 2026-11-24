"""Unified command line for offline analysis and explicit YuE2 Studio workflows."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from .music import ScoreError,parse_score,section_sequence,humanize_pitch
from .prosody import parse_lyrics,alignment,phrase_diagnostics
from .midi import probe
from .instrument_velocity import write as humanize_instruments
from .instrument_render import run as render_instruments
from .instrument_dynamics import process as process_dynamics
from .finish import finish as finish_existing
from .native_process import preview as native_preview
from .multilingual_fidelity import assess as assess_multilingual
from .midi_events import compare_files,MIDIEventError
from .pipeline import run as run_pipeline
from .experiments import prepare,submit,reconcile,status
from .expression import plan as expression_plan
from .lyric_fidelity import compare_lyrics
from .phrase_rhythm import analyze as analyze_rhythm
from .acoustic import compare as compare_audio
from .native_recognition import capture as capture_recognition, review as review_recognition
from .fidelity_gate import diagnose as diagnose_fidelity
from .human_selection import compare as compare_human
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
    work.add_argument('--profile',choices=('conservative','legacy'),default='conservative')
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
    variation.add_argument('--profile',choices=('conservative','legacy'),default='conservative')

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

    ex=sub.add_parser('expression',help='Offline experimental expression preview; no Studio calls')
    ex.add_argument('abc',type=Path)
    ex.add_argument('--lyrics',required=True,type=Path)
    ex.add_argument('--out',required=True,type=Path,help='New output directory')
    ex.add_argument('--max-edits',type=int,default=4)
    ex.add_argument('--protect-bar',type=int,action='append',default=[])

    fidelity=sub.add_parser('lyric-compare',help='Compare intended lyrics with a complete human-reviewed transcript')
    fidelity.add_argument('--lyrics',required=True,type=Path)
    fidelity.add_argument('--transcript',required=True,type=Path)
    fidelity.add_argument('--out',required=True,type=Path)

    rhythm=sub.add_parser('phrase-rhythm',help='Read-only score density and optional reviewed A/B timing analysis')
    rhythm.add_argument('abc',type=Path)
    rhythm.add_argument('--lyrics',required=True,type=Path)
    rhythm.add_argument('--timings',type=Path,help='Optional reviewed A/B phrase timing JSON')
    rhythm.add_argument('--out',required=True,type=Path)

    ac=sub.add_parser('acoustic-compare',help='Measure existing local FLAC/WAV mixes using FFmpeg')
    ac.add_argument('--a',required=True,type=Path)
    ac.add_argument('--b',required=True,type=Path)
    ac.add_argument('--out',required=True,type=Path)

    nr=sub.add_parser('native-recognise',help='Explicit local Studio recognition of existing audio')
    nr.add_argument('audio',type=Path)
    nr.add_argument('--out',required=True,type=Path)
    nr.add_argument('--url')
    nr.add_argument('--language')
    nr.add_argument('--confirm-recognition',action='store_true')

    ar=sub.add_parser('asr-review',help='Offline review of existing native recognition JSONs')
    ar.add_argument('--lyrics',required=True,type=Path)
    ar.add_argument('--a',required=True,type=Path)
    ar.add_argument('--b',required=True,type=Path)
    ar.add_argument('--out',required=True,type=Path)

    fg=sub.add_parser('fidelity-audit',help='Offline human-led fidelity gate and score diagnostics')
    fg.add_argument('abc',type=Path)
    fg.add_argument('--lyrics',required=True,type=Path)
    fg.add_argument('--asr-review',required=True,type=Path)
    fg.add_argument('--observations',required=True,type=Path)
    fg.add_argument('--native-syllables',type=Path)
    fg.add_argument('--out',required=True,type=Path)

    hs=sub.add_parser('human-select',help='Offline paired human preference and ASR conflict review')
    hs.add_argument('--asr-review',required=True,type=Path)
    hs.add_argument('--preferences',required=True,type=Path)
    hs.add_argument('--out',required=True,type=Path)

    iv=sub.add_parser('instrument-velocity',help='Humanize named accompaniment MIDI tracks for DAW export')
    iv.add_argument('midi',type=Path)
    iv.add_argument('--out',required=True,type=Path)
    iv.add_argument('--strength',type=int,default=12)

    iq=sub.add_parser('instrument-render-qa',help='Render and compare velocity-only accompaniment MIDI with FluidSynth')
    iq.add_argument('source',type=Path)
    iq.add_argument('candidate',type=Path)
    iq.add_argument('--soundfont',required=True,type=Path)
    iq.add_argument('--out',required=True,type=Path)
    iq.add_argument('--renderer',default='fluidsynth')

    dy=sub.add_parser('instrument-dynamics',help='Process existing aligned instrumental stem without regenerating song')
    dy.add_argument('--mix',required=True,type=Path)
    dy.add_argument('--instrumental',required=True,type=Path)
    dy.add_argument('--vocals',required=True,type=Path)
    dy.add_argument('--out',required=True,type=Path)
    dy.add_argument('--max-db',type=float,default=2.0)

    fin=sub.add_parser('finish-existing',help='One bounded existing-song dynamics and native ASR workflow')
    for key in ('mix','instrumental','vocals','lyrics','baseline-asr','out'):
        fin.add_argument('--'+key,type=Path,required=True)
    fin.add_argument('--language',required=True,help='Reference scoring language (e.g. en, id, ja)')
    fin.add_argument('--url')
    fin.add_argument('--confirm-recognition',action='store_true')
    fin.add_argument('--max-db',type=float,default=2.0)

    ml=sub.add_parser('multilingual-score',help='Score existing transcript text offline')
    ml.add_argument('--lyrics',type=Path,required=True)
    ml.add_argument('--transcript',type=Path,required=True)
    ml.add_argument('--language',required=True)

    np=sub.add_parser('native-process-preview',help='Read-only preflight or one explicitly confirmed native audio preview')
    np.add_argument('--source',type=Path,required=True)
    np.add_argument('--song-id',required=True)
    np.add_argument('--effect',choices=('naturalize','lifter'),required=True)
    np.add_argument('--amount',type=float,default=0.2)
    np.add_argument('--out',type=Path,required=True)
    np.add_argument('--url')
    np.add_argument('--confirm-preview',action='store_true')
    np.add_argument('--lyrics',type=Path)
    np.add_argument('--baseline-asr',type=Path)
    np.add_argument('--language')
    np.add_argument('--confirm-recognition',action='store_true')

    ping=sub.add_parser('studio-check',help='Read-only local Studio status')
    ping.add_argument('--url')
    args=parser.parse_args(argv)
    try:
        if args.command=='run':
            result=run_pipeline(args.abc,args.lyrics,args.out,style=args.style,
                                seed=args.seed,max_edits=args.max_edits,
                                midi=args.midi,url=args.url,title=args.title,profile=args.profile)
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
            candidate=humanize_pitch(score,lyrics,args.seed,args.max_edits,profile=args.profile)
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
        elif args.command=='expression':
            planned=expression_plan(args.abc.read_text(encoding='utf-8-sig'),
                                    args.lyrics.read_text(encoding='utf-8-sig'),
                                    args.max_edits,args.protect_bar)
            args.out.mkdir(parents=True,exist_ok=False)
            report=args.out/'expression_report.json'
            with report.open('x',encoding='utf-8') as f:
                json.dump(planned['report'],f,indent=2,ensure_ascii=False)
                f.write('\n')
            result={'status':planned['report']['status'],'report':str(report),
                    'changes':planned['report']['change_count'],'audio_jobs_created':0}
            if result['changes']:
                candidate=args.out/'candidate_expression.abc'
                with candidate.open('x',encoding='utf-8',newline='') as f:
                    f.write(planned['abc'])
                result['candidate']=str(candidate)
        elif args.command=='lyric-compare':
            result=compare_lyrics(args.lyrics.read_text(encoding='utf-8-sig'),
                                  args.transcript.read_text(encoding='utf-8-sig'))
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x',encoding='utf-8') as f:
                json.dump(result,f,indent=2,ensure_ascii=False)
                f.write('\n')
        elif args.command=='phrase-rhythm':
            timings=json.loads(args.timings.read_text(encoding='utf-8-sig')) if args.timings else None
            report=analyze_rhythm(args.abc.read_text(encoding='utf-8-sig'),
                                  args.lyrics.read_text(encoding='utf-8-sig'),timings)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x',encoding='utf-8') as f:
                json.dump(report,f,indent=2,ensure_ascii=False)
                f.write('\n')
            result={'report':str(args.out),'phrase_count':report['phrase_count'],
                    'paired_timing_count':report['paired_timing_count'],'audio_jobs_created':0}
        elif args.command=='acoustic-compare':
            if args.out.exists():
                raise ValueError('Acoustic report already exists')
            report=compare_audio(args.a,args.b)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x',encoding='utf-8') as f:
                json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
                f.write('\n')
            result={'report':str(args.out),'B_minus_A':report['B_minus_A'],
                    'suggested_playback_gain_db':report['suggested_playback_gain_db'],
                    'audio_jobs_created':0}
        elif args.command=='native-recognise':
            result=capture_recognition(args.audio,args.out,args.url,
                                       confirm=args.confirm_recognition,language=args.language)
        elif args.command=='asr-review':
            report=review_recognition(args.lyrics.read_text(encoding='utf-8-sig'),
                                      json.loads(args.a.read_text(encoding='utf-8-sig')),
                                      json.loads(args.b.read_text(encoding='utf-8-sig')))
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x',encoding='utf-8') as f:
                json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
                f.write('\n')
            result={'report':str(args.out),'arms':report['arms'],
                    'quality_decision':report['quality_decision'],
                    'human_verified':False,'audio_jobs_created':0,'recognition_calls':0}
        elif args.command=='fidelity-audit':
            report=diagnose_fidelity(args.abc.read_text(encoding='utf-8-sig'),
                                     args.lyrics.read_text(encoding='utf-8-sig'),
                                     json.loads(args.asr_review.read_text(encoding='utf-8-sig')),
                                     json.loads(args.observations.read_text(encoding='utf-8-sig')),
                                     native_syllables=json.loads(args.native_syllables.read_text(encoding='utf-8-sig')) if args.native_syllables else None)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x',encoding='utf-8') as f:
                json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
                f.write('\n')
            result={'report':str(args.out),**{k:report[k] for k in (
                'gate','confirmed_issue_lines','confirmed_issue_transitions',
                'reviewed_line_observations','total_lines','audio_jobs_created',
                'recognition_calls','score_edits','native_syllable_lines',
                'native_syllable_total','rough_syllable_total','syllable_count_disagreements')}}
        elif args.command=='human-select':
            report=compare_human(json.loads(args.asr_review.read_text(encoding='utf-8-sig')),
                                 json.loads(args.preferences.read_text(encoding='utf-8-sig')))
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x',encoding='utf-8') as f:
                json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
                f.write('\n')
            result={'report':str(args.out),**{k:report[k] for k in (
                'human_preference_counts','asr_comparison_counts','asr_edit_totals',
                'lyric_evidence_policy','asr_lyric_preferred','human_music_preferred',
                'provisional_lyric_preferred','provisional_preferred','selection_status','absolute_fidelity_status',
                'automatic_acceptance','automatic_regeneration','audio_jobs_created',
                'recognition_calls','score_edits')}}
        elif args.command=='instrument-velocity':
            report=humanize_instruments(args.midi,args.out,args.strength)
            result={'output':str(args.out),**{k:v for k,v in report.items() if k!='changes'}}
        elif args.command=='instrument-render-qa':
            result=render_instruments(args.source,args.candidate,args.soundfont,args.out,args.renderer)
        elif args.command=='instrument-dynamics':
            report=process_dynamics(args.mix,args.instrumental,args.vocals,args.out,args.max_db)
            result={'report':str(args.out/'report.json'),**{k:v for k,v in report.items() if k not in ('edits','acoustic','source_sha256')}}
        elif args.command=='finish-existing':
            result=finish_existing(args.mix,args.instrumental,args.vocals,args.lyrics,
                                   args.baseline_asr,args.out,args.language,url=args.url,
                                   confirm=args.confirm_recognition,max_db=args.max_db)
        elif args.command=='multilingual-score':
            result=assess_multilingual(args.lyrics.read_text(encoding='utf-8-sig'),
                                       args.transcript.read_text(encoding='utf-8-sig'),args.language)
        elif args.command=='native-process-preview':
            result=native_preview(args.source,args.song_id,args.effect,args.amount,args.out,args.url,
                                  confirm=args.confirm_preview,lyrics=args.lyrics,baseline_asr=args.baseline_asr,
                                  language=args.language,confirm_recognition=args.confirm_recognition)
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
