# Offline musical review (experimental, generation-first P1)

Use the existing unified CLI. This is an offline read-only evidence stage, not a score editor or generation command.

```powershell
py -3 -m yue2_music_director.cli score-review local/song.abc --lyrics local/lyrics.txt --out results/score-review.json
```

Optional `--constraints local/constraints.json` accepts a mapping of key, tempo_bpm, section_order and sung_sections to mode/value records. Example (original synthetic requirements):

```json
{
  "key": {"mode": "prefer", "value": "Am"},
  "tempo_bpm": {"mode": "free", "value": null},
  "section_order": {"mode": "prefer", "value": ["intro#1", "verse#1", "chorus#1"]},
  "sung_sections": {"mode": "must", "value": ["verse#1", "chorus#1"]}
}
```

Section lists use normalized occurrence IDs. Final/last chorus is normalized to another chorus occurrence in this review only. Sung_sections means note-bearing (including sustained vocal) sections in ABC, not actual sung text. Whole-line parenthetical directions are excluded from expected sung sections as an explicitly limited heuristic; mixed directions and lyric text remain unresolved. `--max-seconds` is an optional absolute **score-clock** cap, not an actual rendered-duration guarantee. All inputs and the report stay local. Existing output is not overwritten. Exit 0 means a report was successfully written, not permission to render. Exit 2 indicates input/IO errors.

## Review output

- Schema native-musical-review-v1; local score/lyric fingerprints, constraint policy, score clock and normalized section occurrences.
- Fixed-grid native major/minor key, integer note lengths, 2/4 and 4/4 among supported meters, native paired voice header/groups, Z through Z4, tie-aware note spans, letter-wide accidentals and carried tied pitches. Source: [pinned native parser](https://github.com/timoncool/YuE2-Studio/blob/192363f16feae73a70c9ef5de79ca3d435c9b84d/crates/music-server/src/score/abc.rs).
- Per-section and whole-score descriptors: attacks and attacks/second, pitch range, sounding fraction, adjacent attack leap histogram, repeated-attack fraction, gap count and longest/leading/trailing rest, chord spellings, and chorus shared-bar vocal-event identity plus lengths. These are descriptive, not an inferred melody quality score, syllable map, performed tempo, or actual accompaniment arrangement.
- Hard violations: detected local structural invalidity, mandatory mismatch, score-clock cap exceeded, or a mandatory constraint not assessable. Soft flags: notated sung/section differences, exact repeated chorus and preference mismatch. Unknowns: unsupported local notation or unverified acoustic/lyric performance. Local status: blocked, unassessable, artistic_review_required or local_review_ready. No automatic rendering or acceptance; native MIDI remains necessary for any future supplied-score render.

## Scope and limitations

The opt-in native review profile reuses the existing parser; legacy audit, humanizer and historical generation-control gates remain unchanged. The native review is a bounded fixed-key/fixed-meter subset, not a complete port: inline or per-voice key/meter changes and other unsupported notation are unassessable, not proof the engine cannot render them. Native grammar is stricter than the legacy parser; local pass alone cannot replace live native MIDI. A reference's score deviation is not automatically a fault. No musical threshold is calibrated, no full-score rewriting or note perturbation, no automatic decision about hooks or artistic quality, no Studio calls or GPU work. The integrated reviewed-native route, intent schema and render authorization are future P2/P3 work.

CI tests use original synthetic data, not private user assets. See the [architecture roadmap](MUSIC_DIRECTOR_ARCHITECTURE.md) and [retained evidence](GENERATION_CONTROL_STUDY.md).
