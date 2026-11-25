# Development and validation

**Current policy (2026-11-25):** follow [native-first audit and gates](docs/knowledge/DEVELOPMENT_AUDIT.md), [Studio capabilities](docs/knowledge/STUDIO_CAPABILITIES.md), and [community prior art](docs/knowledge/COMMUNITY_AND_EVALUATION.md). No new implementation without an identified gap and acceptance criteria. All technical documentation in English; README also includes Indonesian overview. The foundation and historical milestones below are not an active implementation backlog.

## Current phase: post-alpha 8.post3 development (experimental)

See [research handbook](docs/RESEARCH_HANDBOOK.md) for current architecture, module status and decisions, and [changelog](CHANGELOG.md) for history. The foundation table below describes earlier v0.6.1 components. Current additions are listed separately.

| Current addition | Evidence |
|---|---|
| Native recognition and custom finishing | Real-song execution complete |
| Native Naturalize and headroom continuation | Real-song execution complete; -1.05 dBTP; unchanged ASR |
| Selection and diagnosis | Offline fixtures, integrated real-song run pending |
| Temporal evidence | Read-only LRC inspection; live metadata lookup pending |
| Optional alignment | Discovery only; no engine or model validated |

Unreleased development commits share package version 0.7.0a8.post3; record the Git commit for reproducibility. No production release claim.

This is a **working local-first Python toolkit**, not a production-ready autonomous music director. Migrated and integrated components:

| Component | Ready | Main limitations |
|---|---|---|
| Strict YuE2 ABC parser | Offline tested | Supports limited notation grammar |
| Phrase-aware pitch candidates | Offline tested | Approximate lyric-line-to-bar allocation; no acoustic humanization |
| Lyric diagnostics | Offline tested | Rough English syllable count, not phoneme alignment |
| MIDI probe | Simulated MCP tested | Requires live local YuE2-Studio, no audio generated |
| MIDI event A/B audit | Offline tested | SMF 0/1 PPQN only; no audio evaluation |
| A/B runner | Simulated MCP tested | Requires explicit confirm; live Studio not accessed by CI |
| Job receipt parser | Simulated live response shape tested | Historic v0.5 job IDs cannot be recovered |
| Windows and Linux CI | GitHub Actions | Does not run GPU/inference |

## Architecture

- `music.py`: strict notation parser, fixed-duration phrase variation and post-edit score safety, with configurable conservative/legacy contour screening
- `prosody.py`: bracketed lyric sections, estimated syllables, rough phrase density report
- `mcp.py`: modern and legacy MCP handshake, loopback-only transport, no automatic retries
- `midi.py`: score-to-MIDI probe and bounded MIDI header checks
- `midi_events.py`: offline note-event comparison, pitch/timing/velocity deltas
- `job_receipt.py`: defensive ID discovery from structuredContent/text JSON
- `experiments.py`: offline preparation, hashed input fingerprints, journal-first one-shot job submission and manual reconciliation
- `cli.py`: single entrypoint for local operations

## v0.6.1 conservative screening

- Default `conservative` profile screens proposals from the reproducible `legacy` selection; it does not refill a rejected phrase with weaker alternate proposals.
- Reject candidate edits larger than 3 semitones; additionally reject a newly worsened neighboring leap above 5 semitones.
- Preserve unchanged timing, chords, phrase and section structure, chorus and instrumental voices; diagnostics explicitly record deferred proposals.
- **Not** a substitute for real lyric-to-note alignment, verified vocal stress, or listening tests.

## Quality gates

- All unit tests and CLI smoke tests pass on Windows and Ubuntu for Python 3.11 and 3.13.
- Real score is validated by `yue2-director audit` **on the user's machine**.
- MIDI compatibility requires explicit local Studio `midi-probe`.
- Real audio requires human-confirmed Studio idle and explicit `ab-submit`; it is never run by CI.
- No pitch edit or identical seed proves a more natural or more expressive vocal. Routine QA is ASR-led and technical; human listening is optional for musical preference, not a repetitive required step.

## Porting note

Earlier v0.1/v0.5.2 stand-alone prototypes were developed and tested in another environment. This repository contains a **restructured implementation** of their key workflows, not a byte-for-byte import of every historical script. Keep old experiment journals and FLAC renders locally. Do not resubmit historical arms A/B or assume they can be imported automatically.

## Future work

- Verified lyric-to-note and phoneme alignment, to support safe rhythm changes.
- Bridge recomposition rather than recycling a pre-chorus.
- Instrument performance expression and optional audio analysis, based on robust objective + human ratings.
- More real-world scores across keys, meters, and unusual ABC tokens.
- Resource manager / resume-safe orchestration and optional LLM integrations.
