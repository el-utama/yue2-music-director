# Development and validation

## Current phase: v0.6 beta

This is a **working local-first Python toolkit**, not a production-ready autonomous music director. Migrated and integrated components:

| Component | Ready | Main limitations |
|---|---|---|
| Strict YuE2 ABC parser | Offline tested | Supports limited notation grammar |
| Phrase-aware pitch candidates | Offline tested | Approximate lyric-line-to-bar allocation; no acoustic humanization |
| Lyric diagnostics | Offline tested | Rough English syllable count, not phoneme alignment |
| MIDI probe | Simulated MCP tested | Requires live local YuE2-Studio, no audio generated |
| A/B runner | Simulated MCP tested | Requires explicit confirm; live Studio not accessed by CI |
| Job receipt parser | Simulated live response shape tested | Historic v0.5 job IDs cannot be recovered |
| Windows and Linux CI | GitHub Actions | Does not run GPU/inference |

## Architecture

- `music.py`: strict notation parser, fixed-duration phrase variation and post-edit score safety
- `prosody.py`: bracketed lyric sections, estimated syllables, rough phrase density report
- `mcp.py`: modern and legacy MCP handshake, loopback-only transport, no automatic retries
- `midi.py`: score-to-MIDI probe and bounded MIDI header checks
- `job_receipt.py`: defensive ID discovery from structuredContent/text JSON
- `experiments.py`: offline preparation, hashed input fingerprints, journal-first one-shot job submission and manual reconciliation
- `cli.py`: single entrypoint for local operations

## Quality gates

- All unit tests and CLI smoke tests pass on Windows and Ubuntu for Python 3.11 and 3.13.
- Real score is validated by `yue2-director audit` **on the user's machine**.
- MIDI compatibility requires explicit local Studio `midi-probe`.
- Real audio requires human-confirmed Studio idle and explicit `ab-submit`; it is never run by CI.
- Human listening is essential. No pitch edit or identical seed proves a more natural or more expressive vocal.

## Porting note

Earlier v0.1/v0.5.2 stand-alone prototypes were developed and tested in another environment. This repository contains a **restructured implementation** of their key workflows, not a byte-for-byte import of every historical script. Keep old experiment journals and FLAC renders locally. Do not resubmit historical arms A/B or assume they can be imported automatically.

## Future work

- Verified lyric-to-note and phoneme alignment, to support safe rhythm changes.
- Bridge recomposition rather than recycling a pre-chorus.
- Instrument performance expression and optional audio analysis, based on robust objective + human ratings.
- More real-world scores across keys, meters, and unusual ABC tokens.
- Resource manager / resume-safe orchestration and optional LLM integrations.
