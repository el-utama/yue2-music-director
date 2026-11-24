"""Safe local command line: no live generation commands in this milestone."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .music import ScoreError, parse_score, section_sequence, humanize_pitch
from .prosody import parse_lyrics, alignment


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog='yue2-director')
    sub=parser.add_subparsers(dest='command',required=True)
    audit=sub.add_parser('audit',help='Read-only score validation')
    audit.add_argument('abc',type=Path)
    audit.add_argument('--lyrics',type=Path)
    vary=sub.add_parser('humanize',help='Generate a separate ABC with phrase-aware pitch edits')
    vary.add_argument('abc',type=Path)
    vary.add_argument('--lyrics',required=True,type=Path)
    vary.add_argument('--out',required=True,type=Path)
    vary.add_argument('--seed',type=int,default=42)
    vary.add_argument('--max-edits',type=int,default=12)
    args=parser.parse_args(argv)
    try:
        text=args.abc.read_text(encoding='utf-8-sig')
        score=parse_score(text)
        if args.command=='audit':
            result={'bars':score.counts,'sections':section_sequence(score),
                    'warnings':score.warnings,'errors':[]}
            if args.lyrics:
                result['warnings']+=alignment(score,parse_lyrics(args.lyrics.read_text(encoding='utf-8-sig')))
        else:
            if not 0<=args.max_edits<=100:
                raise ValueError('--max-edits must be between 0 and 100')
            if args.out.resolve()==args.abc.resolve():
                raise ValueError('output must differ from original source')
            lyrics=args.lyrics.read_text(encoding='utf-8-sig')
            generated=humanize_pitch(text,lyrics,args.seed,args.max_edits)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            if args.out.exists():
                raise ValueError('output already exists; refusing overwrite')
            args.out.write_text(generated['abc'],encoding='utf-8')
            report_path=args.out.with_suffix('.report.json')
            report_path.write_text(json.dumps(generated['report'],indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            result={'output':str(args.out),'report':str(report_path),
                    'changes':generated['report']['change_count'],
                    'warnings':generated['report']['warnings']}
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 0
    except (ScoreError,ValueError,OSError) as exc:
        parser.exit(2,f'ERROR: {exc}\n')


if __name__=='__main__':
    raise SystemExit(main())
