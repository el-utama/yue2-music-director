# Explicit typed creative requirements (opt-in)

The normal autonomous CLI retains its reviewed-score-v3 default and all prior
job identities. For a new job with precise requirements, explicitly supply a
private JSON file using `music.cmd --creative-spec path-to-spec.json`.
Review the plan, then confirm a new production job only when authorized.
A typed job uses reviewed-score-v4-typed. Its spec is frozen; subsequent
resume by job ID reads the original spec, not a modified file.

Example synthetic specification:

```json
{
  "schema": "creative-spec-v1",
  "opening": "direct_vocal",
  "vocal": "female",
  "narrator": "first person",
  "style": null,
  "lyrics": "[Verse]\nThe key is on the table\n",
  "section_purposes": {"verse#1": "Introduce departure"},
  "score_constraints": {
    "tempo_bpm": {"mode": "prefer", "value": 80}
  }
}
```

Optional fields default to null or empty mappings. Opening choices are
instrumental_intro/direct_vocal; vocalist choices male/female/duet/mixed/
androgynous. Narrator and vocal identity are independent. Explicit values
are requirements; unspecified values are model-selected, not inferred user
preferences. Style, if supplied, is preserved exactly and must have a
compatible literal vocal cue. The Composer response uses a versioned typed
direction object and ordered section plan, not magic performance headers.
Section IDs are normalized occurrences (verse#1, chorus#2); explicit
purposes must be preserved, other purposes are model proposals. Literal
style cue checks are conservative, not complete semantic or acoustic
verification. Arbitrary prose requirements are not automatically converted
into mandatory constraints.

A supplied lyrics string is preserved byte-for-byte in UTF-8 conditioning
and TXT export, including whitespace and line endings. It must have valid
section tags and a compatible opening; no Lyricist provider call is made.
A separate local operator-lyrics receipt proves origin and zero provider
calls for that stage. Composer and Reviewer may receive these private
lyrics as authorized by the explicit production confirmation. A generated
lyrics response must match the typed section plan before success receipt;
one explicit failed-stage retry remains bounded.

Only key, tempo_bpm, section_order and sung_sections score requirements
are accepted, with must/prefer/free semantics. Opening is separately typed
and screened by the existing versioned opening timing evidence. Hard
constraints block native synthesis when unmet; a mismatched preference
requires review under the existing soft-flag policy. All native request
fields remain unchanged: style, lyrics, supported seed/steering and
existing native settings. Section purposes inform text roles and retained
intent; they are not unsupported native API fields or guarantees of audio
arrangement. Speaker/narrator/vocal timbre cannot be proven by score gate.

Synthetic regression tests cover exact local lyrics, typed section and vocal
conflicts, one bounded retry, retained continuation lookup, native request
shape and exact TXT export. No new live provider or music inference is
authorized. Typed wire schema requires a separate live compatibility check
before claiming hosted-model support; the validated v3 route remains default.
