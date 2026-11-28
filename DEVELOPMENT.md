# Development and validation

**Current policy:** follow the [active autonomous product roadmap](docs/AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md) and [generation-first architecture](docs/MUSIC_DIRECTOR_ARCHITECTURE.md) for new-song development and retain the [native-first audit and gates](docs/knowledge/DEVELOPMENT_AUDIT.md), [Studio capabilities](docs/knowledge/STUDIO_CAPABILITIES.md), and [community prior art](docs/knowledge/COMMUNITY_AND_EVALUATION.md). No new implementation without an identified gap and acceptance criteria. All technical documentation in English; README also includes Indonesian overview. The foundation and historical milestones below are not an active implementation backlog.

## Agent onboarding and current evidence

1. Read [AGENTS.md](AGENTS.md), [PROJECT_MEMORY.md](PROJECT_MEMORY.md), the active roadmap, [native audit](docs/NATIVE_AUDIT_CHECKPOINT.md) and [local release checkpoint](docs/LOCAL_RELEASE_CHECKPOINT.md).
2. Verify main, exact pending PR head, CI evidence, source code, and actual data inventory. Choose an open requirement, not an old historical milestone.
3. Read [operator guide](docs/OPERATOR_GUIDE.md) and the specific module contract. Keep supported confirmation semantics, private files, retained jobs and one short launcher intact.
4. Make a coherent bounded change, with tests for normal, failure and resume paths. Use Windows/Linux Python 3.11 PR CI (two jobs); local mock tests are not live Studio/provider validation. Run the full Python 3.11/3.13 matrix manually before releases and when changing dependencies or Python compatibility. No extra inference unless explicitly authorized.
5. Update the relevant user guide, README entry points when needed, changelog and PROJECT_MEMORY.md. Distinguish candidate metadata from approved references, implemented from tested, and technical from artistic acceptance.

Current evidence after PR #127: three offline SQLite/FTS5 indexes, explicit authored-style selection in autonomous Composer, local artist profiles and bounded release specialists are implemented and CI-tested. Historical knowledge production integration, approved corpus, live typed/preset generalization, process supervision and private production service are open. The current register is authoritative. See [offline workflow](docs/OFFLINE_KNOWLEDGE_WORKFLOW.md) and [active roadmap](docs/AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md).

The offline documentation regression gate (`tests/test_documentation.py`) checks tracked Markdown inline relative file/directory links, heading fragments and the operator guide's primary launcher route table. Run from a Git checkout. It deliberately does not fetch external URLs, validate arbitrary Markdown syntax, or execute historical examples. Windows CI additionally builds/browses all three bundled indexes and previews a selected-style job with no provider or Studio calls.

## Historical phase: post-alpha 8.post3 development (experimental)

See [research handbook](docs/RESEARCH_HANDBOOK.md) for current architecture, module status and decisions, and [changelog](CHANGELOG.md) for history. The foundation table below describes earlier v0.6.1 components. Current additions are listed separately.

| Current addition | Evidence |
|---|---|
| Native recognition and custom finishing | Real-song execution complete |
| Director-authored generation | Live MIDI, song synthesis, saved conditioning and resumed ASR verified; musical result rejected |
| Generation-first routing and expressive review | Design only; P1 offline policy and score descriptors are next |
| Native Naturalize and headroom continuation | Real-song execution complete; -1.05 dBTP; unchanged ASR |
| Selection and diagnosis | Real integrated retained-song review complete; no artistic winner |
| Temporal evidence | Real read-only partial native LRC lookup complete; not phonetic alignment |
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

The [active product roadmap](docs/AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md) and [project memory](PROJECT_MEMORY.md) are authoritative; the architecture roadmap is historical design context. P1 score evidence and hard/soft/unknown policy precede new generation; the following are longer-term research topics, not a queue to execute immediately.

- Verified lyric-to-note and phoneme alignment, to support safe rhythm changes.
- Bridge recomposition rather than recycling a pre-chorus.
- Instrument performance expression and optional audio analysis, based on robust objective + human ratings.
- More real-world scores across keys, meters, and unusual ABC tokens.
- Resource manager / resume-safe orchestration and optional LLM integrations.

## CI execution policy

Routine pull requests run the complete offline suite and existing smoke checks
on Windows and Ubuntu with Python 3.11. Push events do not start a second
workflow; updates to a PR cancel superseded runs. Direct pushes to main are
not a substitute for a tested PR. In GitHub Actions, select Python tests,
Run workflow, and leave full_matrix enabled for the four-job release or
runtime/dependency compatibility check. Disable it for a manual two-job
check. Check the current PR head before merging; prior four-job evidence
remains historical. CI still does not perform Studio inference.
