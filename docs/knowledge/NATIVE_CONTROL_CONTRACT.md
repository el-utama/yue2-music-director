# Native control contract audit — 2026-11-27

Model/runtime portability follow-up is tracked in [Hardware Advisor](../HARDWARE_ADVISOR.md). Keep installed/effective distinctions and historical reference policies; alternative production profiles are not validated.

## Scope and evidence levels

Target: timoncool/YuE2-Studio v5.0 Portable, not generic ABC, original YuE
or another engine offered by Studio. Operator screenshots confirm the
Create score card's Edit button and Score editor's Vocal, Ins, Chords,
Velocity, Pitch Bend, Volume, Panpot, Expression, Hold Pedal, Modulation,
Arrange and Tempo controls. The screenshot proves UI exposure only.
Source review compares the earlier pinned audit ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25
with upstream main 40a4631dcb5203625551b0be37d097c2afb194d1.
A live restricted bridge identified the installed MCP server as music-server
5.0.0 on 2026-11-27. The exact executable build and source SHA remain unverified.

Keep separate evidence levels: UI exposure; request schema; handler and
conversion data flow; actual engine payload; offline executable test;
installed live behavior; human listening. Never promote one to another.
No inference, Studio installation, Studio settings change, training or new
reference render was performed by the audit. A private audit bridge was used
for native read-only/synthetic conversion calls. This remains a targeted audit,
not an exhaustive review of every subsystem.

## Score editor: the velocity finding

The score-mode editor opens an ABC score as MIDI. Apply obtains the
editor MIDI bytes, calls scoreFromMidi, optionally marks the resulting
ABC for the original style/words/cot and returns ABC and lyrics through
onApply. It does not pass the edited MIDI to the synthesizer.

- [Editor Apply](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/app/components/midi/MidiEditor.tsx)
- [Client conversion](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/app/services/midiEditor.ts): POST /v1/score/from-midi, automatic vocal/instrument selection, section markers, full/melody mode.
- [SMF reader](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/crates/music-server/src/score/smf.rs) reads note-on velocity. This is not a loss at MIDI parsing.
- [Importer](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/crates/music-server/src/score/import/mod.rs) snaps note start/end to grid, chooses single melody lines, builds (start, end, pitch, voice) rows; chord inference uses pitch/time and role weights, not velocity. [Rebuild](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/crates/music-server/src/score/rebuild.rs) exposes those same four fields. The reviewed Apply path loses per-note velocity and has no demonstrated path for CC automation or pitch bend.
- [MIDI exporter](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/crates/music-server/src/score/export.rs) generates fixed note-on velocities Vocal 100, Ins 90, Chords 64; the MIDI programs are preview/export choices, not proof of actual generated instrumentation. Ins is a melodic line, not a full-band orchestration.
- [Earlier importer](https://github.com/timoncool/YuE2-Studio/blob/ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25/crates/music-server/src/score/import/mod.rs) and [earlier exporter](https://github.com/timoncool/YuE2-Studio/blob/ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25/crates/music-server/src/score/export.rs) show the same relevant data loss and defaults.

A velocity-only edit must not be advertised as native YuE2 humanization.
The existing MIDI humanizer and FluidSynth QA are legitimate for separate
MIDI accompaniment rendering, not the native full-band output. Library
midi_set replaces the stored transcription MIDI, not the FLAC. An editor
round trip may also change note geometry, harmony spelling, sections or
tempo: import uses 16/32 grid, single-line selection, key/section rebuilding
and average BPM for variable tempo. Never use it as a lossless no-op.

## Installed velocity verification — 2026-11-27

Actual native MCP server: music-server 5.0.0. A restricted bridge v0.2.0
submitted two synthetic MIDI inputs through the native score import and
MIDI export endpoints. Both contained eight identical Vocal notes at
velocity 100 and eight Ins notes with the same pitches, timing and tempo.
Baseline Ins velocities were all 90. The varied Ins velocities were
30, 60, 120, 45, 105, 70, 115, 50.

| Evidence | Observed result |
|---|---|
| Native import | Baseline and varied ABC strings identical |
| Native export | Both Vocal tracks at 100; both Ins tracks at 90 |
| Operator UI check | Operator reported edits were not saved and were only for MIDI export after the requested Apply/reopen check |

The first two rows are direct tool observations, not a simulation or an
inference from source. The third is operator-reported, not an automated
UI trace or independently captured screenshots. No acoustic synthesis
comparison was run. The result is scoped to score-mode MIDI -> ABC -> MIDI;
it does not establish identical behavior in standalone MIDI editing or
every engine. Do not repeat this successful conversion test merely for
confirmation. No song, existing score, library record or reference audio
was modified. No credentials, private network locators or tunnel IDs
belong in the repository.

## Native request boundary — source audit increment

[Studio request builder and dispatcher](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/crates/music-server/src/lib.rs)
(`yue_request_from`, `dispatch_music_job`) distinguish input controls from
the body actually submitted to yue-server:

- A supplied nonempty complete ABC is transposed if requested, stripped of
  editor metadata and forwarded with a trailing newline; edit-word mismatch
  can reject it. Opening continuation uses `score::opening::sung` instead.
  A recognized chord bed with sung words becomes a header plus harmony
  follow/chord constraints and requests continuation. A complete supplied
  score is therefore not interchangeable with an opening or chord bed.
- Lyrics CRLF is normalized to LF at the engine boundary. Do not claim
  byte-identical operator lyrics at inference just because the retained
  creative artifact preserves those bytes. Director saved-lyrics checks
  accept exact text or that one documented transform, not arbitrary
  whitespace changes. Retained brief, request and operator lyrics remain
  unchanged, with their original hashes.
- Nonnegative explicit lm_seed and seed are retained; missing/negative
  seeds are drawn separately. ABC and semantic sampling are separate
  validated presets. Harmony is passed only when the engine writes a score.
- Steps 1..200, synth batch 1..9, companion scale 0..1; solver midpoint or
  ab2. A negative CFG is omitted, finite CFG above 10 rejected. LM batch
  depends on configured/memory limits. These are request controls, not
  verified artistic recommendations.
- Before submission, trained style can replace requested style; absent
  companion scale is resolved according to backbone/adapters. The complete
  score route can run layout and lyric_schedule (unless explicitly disabled);
  opening continuation skips both at this boundary. The saved
  generation_settings is the constructed body, distinct from stored request.
- Long-duration requests can increase score/semantic token budgets when
  explicit limits are absent. Duration remains a ceiling, not proof of
  completed sung structure.
- [Alternate audio.cpp YuE2](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/crates/music-server/src/audio_cpp_yue2.rs)
  has a different task builder and bounds: 1..100 steps, 1..300 seconds,
  rejects adapters/cover/ABC continuation, maps semantic prefix and sampling
  into options. Do not transfer native yue-server parameters blindly.

Live installed writing_guide(score) was read directly: it confirms
monophonic Vocal and Ins; quoted chord symbols in Vocal for full mode only;
native chord suffixes (major, m, dim, aug, 7, maj7, m7, dim7, m7b5, sus4,
sus2, 6, m6, 7sus4, m(maj7), optional slash bass); the enumerated duration
units 1,2,3,4,6,8,12,16,24,32,48; ties for other note lengths, not rests;
bar sums and accidental scope; no generic dynamics decorations, slurs,
tuplets, stacked notes or lyric w: lines. This is an installed guide
contract, not exhaustive parser/tokenizer proof. Preserve unrelated bars
when editing. Match Q tempo to style BPM.

This increment reaches Studio's engine submission boundary. The following
section extends source review into the pinned engine; neither is live engine
payload capture. Do not invoke a generation just to test a schema.

## Pinned native engine conditioning audit — 2026-11-27

The reviewed Studio revision pins [yue2.cpp 892b9b0311512a1c45e42d6403881d17a991b87c](https://github.com/timoncool/yue2.cpp/tree/892b9b0311512a1c45e42d6403881d17a991b87c)
in [engines/yue2-cpp-source.json](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/engines/yue2-cpp-source.json).
This establishes the reviewed source relationship, not the installed
engine executable hash, backend, weights, or effective runtime settings.

### Composition, semantic stream and acoustic rendering

- [prompt.h](https://github.com/timoncool/yue2.cpp/blob/892b9b0311512a1c45e42d6403881d17a991b87c/src/prompt.h):
  BPE-encoded instruction, Tags/style and Lyrics text, followed by special
  ABC and music delimiters. Full mode requests chord-annotated ABC,
  melody mode requests no chord symbols, off skips score planning.
  Provided ABC is encoded as text, not MIDI bytes or CC/velocity events.
  The checkpoint context constant is 24576; the actual runtime capacity
  is configurable. The engine does not itself normalize lyrics in prompt
  assembly; Studio's earlier CRLF normalization still applies.
- [pipeline.h](https://github.com/timoncool/yue2.cpp/blob/892b9b0311512a1c45e42d6403881d17a991b87c/src/pipeline.h):
  complete supplied ABC is encoded and copied into each plan slot;
  missing ABC or abc_continue enters planning (opening prefix without
  its closing token). With supplied ABC, sampling another semantic stream
  still changes interpretation. The engine score checker for model-made
  plans is a basic structural screen, not a complete native notation or
  musical-quality validator; missing headers can be filled and bad plans
  can be retried. Keep the Director's stricter preflight and evidence gates.
- [sampling.h](https://github.com/timoncool/yue2.cpp/blob/892b9b0311512a1c45e42d6403881d17a991b87c/src/sampling.h):
  separate sampling presets, with source defaults below. These are not
  recommended tuning values or confirmed installed effective defaults.

| Source default | ABC planning | Semantic generation |
|---|---:|---:|
| Temperature | 0.7 | 1.0 |
| Top-p | 0.9 | 0.95 |
| Top-k | 30 | 100 |
| Repetition penalty | 1.005 | 1.2 |
| Penalty window | 100 | 50 |
| Minimum tokens | 32 | 200 |
| Maximum tokens | 4096 | 9000 |

- [generate.h](https://github.com/timoncool/yue2.cpp/blob/892b9b0311512a1c45e42d6403881d17a991b87c/src/generate.h):
  CFG combines conditional and unconditional logits in AR generation;
  the negative prompt removes style/lyrics but retains the score for
  score modes. Source default guidance is 1.0 in full/melody and 1.01
  off. This is **not** a NAR loudness, expression or effects control.
  The actual lyric_schedule path requires guidance 1 and a supplied
  score. Do not tune CFG independently of lyric timing compatibility.
- Semantic replay supplies code IDs directly rather than drawing a new
  semantic stream; continuation carries the previous codes as prefix
  and draws additional codes. Replay still needs acoustic conditioning
  prefill and flow matching. Changing the score/style/lyrics or adapters
  is not a certified transparent replay. Do not equate same codes to
  identical waveform or artistic quality.
- Noise is drawn per acoustic variation using seed+j; the AR draw uses
  lm_seed+i per song; model-made plan retries use separate seed offsets.
  For a fixed semantic stream, acoustic variants share the stream but
  use different noise. The pipeline solves latent chunks with steps and
  solver, overlapping/crossfading latent frames for long songs, then VAE
  decodes. AR and NAR adapter slots are distinct. No proof of arbitrary
  note dynamics or exact timbre control arises from any of these knobs.
- [request.cpp](https://github.com/timoncool/yue2.cpp/blob/892b9b0311512a1c45e42d6403881d17a991b87c/src/request.cpp)
  builds a per-track replay request with ABC, codes, resolved song/variation
  seeds, batch sizes reset to one. This is evidence of intended replay
  provenance, not a guarantee of bitwise equality across environments.

### Completion evidence and safeguards

Semantic generation caps its token budget by requested duration and
remaining context after prompt/score; min_tokens can be clamped to the
duration cap, and insufficient room for the minimum can fail. Acoustic
context includes the prompt and two frame-related blocks, so it can
require chunks even if AR generation fits. No automatic increase of
duration, context, GPU settings or sampling budget is justified by this
audit. End token versus token cap is a distinct completion condition;
the pipeline records truncation if the planned score or semantic
generation truncated. [tools/yue-server.cpp](https://github.com/timoncool/yue2.cpp/blob/892b9b0311512a1c45e42d6403881d17a991b87c/tools/yue-server.cpp)
serializes that flag in track JSON. Absence of truncation is not proof
of lyrical/section completeness or musical ending quality. Preserve
engine provenance, separate observed truncation from human ending
judgment, and do not invent missing signals when historical records
lack them. Studio imports the engine replay request into the stored track; the library
list adds cut_short (length/memory) from its frame-budget heuristic. The
Director reads the full song record, validates song/job identity, and uses
native_completion to block provisional status for flagged or unknown
completion in the autonomous artist path. The existing gate is retained.
The memory label is not a measured out-of-memory diagnosis: the engine
combines score and semantic truncation, while Studio classifies by frame
count. New malformed flags or invalid semantic streams are treated as
unknown, not as unflagged completion; retained receipts are not rewritten.

Scope: source review of pinned prompt assembly, request parsing,
sampling, pipeline and server track output, not compiled engine tests,
full BPE vocabulary audit, or installed inference observation. No
reference generation, replay, GPU call or settings change was made.

## Installed artistic guides and lyric schedule evidence

Live writing_guide(lyrics/style/sections) was read from the installed Studio.
Its new-song advice uses standalone English tags, ordinary spelling,
nearby lines of similar syllable count, roughly 2–3 sung words per second
as a planning heuristic (not a universal acceptance limit), and no singer
cues in lyrics. Duet voices are style descriptors, not dedicated singer
routing. Style places vocal language first, concrete genre/vocal/instruments,
mood and BPM last. Dataset-caption advice is a separate route with different
length requirements. Do not silently change historical creative prompts,
operator-authored lyrics or receipt identities.

[Studio schedule](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/crates/music-server/src/score/schedule.rs)
matches sung tags to score sections in order and schedules their first
Vocal note. It skips instrumental blocks and can omit unmatched sections.
Its spans index Unicode codepoints in the actual engine lyrics, not UTF-8
bytes. Studio uses bias -4, a soft constraint; the engine maps those spans
to BPE prompt rows. Neither the request flag nor schedule coverage proves
actual timing, diction, stress or singer identity.

New artist draft reports include optional native_lyric_schedule evidence
from saved generation_settings and pass it to Director only when present.
The report distinguishes absent metadata, partial/full recognized sung
block coverage and invalid/unrecognized shapes. This is an advisory
coverage check against saved text, not a recreation of native score
matching or verification of the engine mask. No new acceptance gate,
automatic repair, extra inference, or historical report migration is
introduced. Actual acoustic section timing remains unverified.

## Production route and control matrix

[Native MCP schemas](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/crates/music-server/src/mcp.rs),
[official skill](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/docs/mcp-skill.md),
[writing contract](https://github.com/timoncool/YuE2-Studio/blob/40a4631dcb5203625551b0be37d097c2afb194d1/crates/music-server/src/assistant.rs).
The table distinguishes supported input contract from acoustic fidelity.

| Control / route | Verified source contract | Limitation / action |
|---|---|---|
| Style | English descriptors, concrete instruments, vocal, genre, mood, BPM; assistant guide specifies 12–50 words | Soft conditioning, no exact instrument identity, velocity or timbre guarantee; reconcile guide versions |
| Lyrics | Section labels, line/stanza structure, sung word density, language/stress guidance | Actual sung words need listening/recognition; not exact phoneme timing |
| Native score | Vocal/Ins monophonic lines; chords in Vocal; valid duration grid, key/meter, sections | No stacked chord notes, grace notes, decorations or generic ABC dynamics symbols in writing contract; unsupported syntax must not be invented |
| Native score planning | score_compose returns candidate ABC and seed | Review before synthesis; budget plans separately |
| Harmony sampling | strength, root/spelling identity, window, hold_limit, outside_bonus, section_strength, follow_lyrics | Affects model-written plan, not a supplied complete ABC; do not double-apply |
| Complete ABC | song_create abc, cot full or melody, optional lyric_timing | Precise score input, not exact generated performance proof |
| Opening continuation | abc_continue; opening ABC becomes seed for new composition | Not same as replaying a complete score or preserving every downstream bar |
| Chord bed | deterministic chords over rests, bpm/key/meter, sections; lyrics allow model to plan melody | Not preservation of a pre-existing melody |
| Transpose | supplied ABC, -24..24, cot full/melody, no semantic_tokens | New score conditioning, not a postproduction pitch shift |
| Velocity/CC/pitch bend | Score editor MIDI features, loss at Apply conversion | Separate MIDI rendering only unless another actual conditioning route is proven |
| Timing/duration | score-grid note starts/ends, explicit rests/ties, section changes | No arbitrary microtiming guarantee; grid may quantize imports |
| Tempo | ABC Q and matching style BPM; importer can average tempo map | Do not promise arbitrary rubato or exact MIDI tempo-map preservation |
| Backing audio | backing_song_id requires native YuE2, matching chord bed, lyrics, ready vocal separator; mixed WAV | Different generation route, not transparent reuse of full-band song |
| Cover | score_transcribe SheetSage2 and score_match_sections, then new style/lyrics/ABC | Melody/chord estimates and uncertain sections; not exact identity or velocity extraction |
| Semantic tokens | explicit engine-specific conditioning/replay | Not raw MIDI controls, no assumption of editable note mapping; no mixing with unsupported transpose |
| Seeds and batches | lm_seed and seed; planning and performance batches separate | New performance can vary; cap duration is a ceiling, not guaranteed completion |
| AR CFG / NAR solver, steps, companion | CFG changes semantic AR logits; steps/solver and companion affect acoustic path | Not musical velocity or validated artistic tuning; retain current approved configuration |
| LoRA | installed adapters and per-slot strength | Role/model-dependent; no automatic download/training or voice identity guarantee |
| MIDI editor new/track mode | native MIDI/audio rendering or MIDI storage | SoundFont preview/render is not YuE2 native synthesis |
| Native song_export | new WAV/FLAC/MP3, rate/depth, loudness target + true peak ceiling, one gain | No limiter; native route is separate from our verified offline gain-only candidate; don't re-export historical success |

## Native-first review backlog (not finished)

1. Pinned engine-side prompt, sampling, pipeline and track truncation source
   reviewed above, including truncation through Studio storage to Director
   acceptance and section schedule evidence. Review remaining notation/BPE
   vocabulary and lyric mask semantics, and compare installed runtime
   identity/settings to pinned sources before changing defaults.
2. Audit composer/lyricist against writing_guide topics and actual ABC
   parser/token vocabulary; inspect permitted score edits and evidence
   gates. Distinguish hard syntax/score constraints from stylistic intent.
3. Audit all editor modes and cover/backing/reference/replay routes through
   their respective handlers; prove which fields survive into which engine.
4. Audit analysis and postproduction: native MIDI/transcription, karaoke
   provenance, stems, effects, song_export, DAW export and library recovery.
   Do not duplicate native features; no assumption of independent stems,
   exact timing or artist quality.
5. Audit model/runtime variants, adapter slots, memory limits, training,
   local security/remote controls, and data ownership. Other music models
   offered by Studio are not interchangeable with YuE2.
6. The synthetic velocity conversion fixture is completed as recorded above.
   For other unresolved runtime questions, design a narrowly scoped
   read-only or zero-GPU fixture first. Only ask for an installed test if it
   resolves a remaining material uncertainty, not for evidence already
   established. Preserve the successful reference and its gain-only
   candidate; do not rerender, mutate, or publish.

This audit corrects the prior inference that absence of velocity in the
song schema meant absence of an editor feature. It also prevents the
opposite error of inferring acoustic control from a visible editor.
Do not begin a new Performance/Humanization Specialist or finalize a new
generation policy before the relevant control path is understood.
