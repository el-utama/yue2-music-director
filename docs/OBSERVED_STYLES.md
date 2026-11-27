# Observed style metadata pilot

R14: 100 actual references in each requested category, lyrics if available.
This batch is separate from the 1,000 original presets. It contains 203
distinct real track metadata candidates from a pinned third-party snapshot of
Kevin MacLeod's Incompetech catalog. Counts: blues 11, jazz 74, lofi 0, pop 18, indie 0, folk 0, backsound 100, hiphop 0, lofihop 0, trap 0.
The official catalog describes CC BY 4.0, but the individual track pages and
audio have not been independently checked. Treat every row as a candidate,
not an approved sample, lyric, audio analysis, or evidence of social-media
use. No copied descriptive prose, recordings or lyrics. Retain attribution
and direct track URL; see manifest. All BPM, instrumentation and mood fields
are reported catalog metadata, not measured features.

Source: https://incompetech.com/agent-section/ (official license and schema);
https://github.com/ryanaryapramudya/Incompetech-api/blob/52fab7e43006e528bce62d82b76d1b32f7c5914b/data/catalog_enriched.json (snapshot,
Git blob 2e8cd466866c33f748379bd9e2b2b43c54e36807). Soundtrack is mapped to backsound as a candidate use case.
Selection round-robins collections, not a claim of representative coverage.

MTG-Jamendo raw.tsv was successfully read from upstream Git blob
ceed27d242523964ed35e67b0de8175fca0ff0af. The pinned README explicitly restricts
the dataset to noncommercial research/academic use and requires prior written
authorization for other uses. Do not import into production.
FMA metadata CC BY 4.0 remains a candidate; original archive not accessible
in this environment. MusicCaps metadata CC BY-SA 4.0; audio rights separate.
Neither was imported here. Do not infer actual references from aggregate
counts, or assign lo-fi, trap, folk, or hip-hop labels without source evidence.
All real-reference acceptance quotas remain open until individual rights and
style evidence are reviewed; no lyrics supplied in this batch.

Offline Windows usage:
`music.cmd --references --build`
`music.cmd --references --genre jazz --limit 100`
`music.cmd --references --genre backsound --search piano`

Creates local/observed-style.sqlite. No network calls, GPU, inference, or
provider transmission. Autonomous integration remains open.
