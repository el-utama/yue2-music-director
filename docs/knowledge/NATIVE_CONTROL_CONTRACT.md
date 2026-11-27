# Native control contract audit — 2026-11-27

## Scope and evidence levels

Target: timoncool/YuE2-Studio v5.0 Portable, not generic ABC, original YuE
or another engine offered by Studio. Operator screenshots confirm the
Create score card's Edit button and Score editor's Vocal, Ins, Chords,
Velocity, Pitch Bend, Volume, Panpot, Expression, Hold Pedal, Modulation,
Arrange and Tempo controls. The screenshot proves UI exposure only.
Source review compares the earlier pinned audit ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25
with upstream main 40a4631dcb5203625551b0be37d097c2afb194d1.
The installed executable's exact build is not independently verified.

Keep separate evidence levels: UI exposure; request schema; handler and
conversion data flow; actual engine payload; offline executable test;
installed live behavior; human listening. Never promote one to another.
No inference, installation, settings change, training or new reference
render was performed. This is a targeted source audit, not exhaustive
review of all upstream subsystems.

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
| Acoustic solver / steps / CFG / companion | explicit synthesis controls in native schema | Not musical velocity or validated artistic tuning; retain current approved configuration |
| LoRA | installed adapters and per-slot strength | Role/model-dependent; no automatic download/training or voice identity guarantee |
| MIDI editor new/track mode | native MIDI/audio rendering or MIDI storage | SoundFont preview/render is not YuE2 native synthesis |
| Native song_export | new WAV/FLAC/MP3, rate/depth, loudness target + true peak ceiling, one gain | No limiter; native route is separate from our verified offline gain-only candidate; don't re-export historical success |

## Native-first review backlog (not finished)

1. Trace actual engine-side score/semantic/acoustic request handling for
   the installed native YuE2 engine, including sampling, lyric timing,
   continuation, model context/length and completion signals; compare
   exact installed schema to pinned sources before changing defaults.
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
6. If a runtime question remains, design a synthetic read-only or zero-GPU
   fixture first (e.g. two otherwise identical MIDI files with different
   velocities through score_from_midi); compare ABC and re-exported MIDI.
   This is proposed, not executed. Only ask for an installed test if it
   resolves a remaining material uncertainty, not for evidence already
   established. Preserve the successful reference and its gain-only
   candidate; do not rerender, mutate, or publish.

This audit corrects the prior inference that absence of velocity in the
song schema meant absence of an editor feature. It also prevents the
opposite error of inferring acoustic control from a visible editor.
Do not begin a new Performance/Humanization Specialist or finalize a new
generation policy before the relevant control path is understood.
