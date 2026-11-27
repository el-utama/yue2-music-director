# Style library and real-reference acquisition

Operator requirement (2026-11-27): 100 styles each for blues, jazz, lofi,
pop, indie, folk, backsound (TikTok/social media background), hip hop,
lofihop and trap; lyrics where legitimately available. Target 1,000.

## Current inventory

This catalog contains 1,000 **original design recipes**, not 1,000 observed
songs or transcribed source descriptions. Each genre has ten genre-specific
musical foundations and ten arrangement treatments (100 intentional
combinations). These are unrendered YuE2-style prompts, not audio evidence,
not verified engine controls, and not a proxy for the real corpus. Lyrics
and reference_track are null because no actual lyrics or recordings were
collected for these presets. No fake titles or made-up track IDs.

Lo-fi denotes primarily textural/ambient low-fidelity music; lofihop denotes
lo-fi hip-hop beat styles; backsound is an application category, not a genre.
Tempo ranges are creative recommendations (trap ranges are double-time grid).
English descriptors align with YuE2 style guidance. A separate request may
supply original lyrics; do not invent existing lyrics or scrape copyright text.

The real-reference target remains OPEN: 100 unique rights-reviewed observed
style records per category. Deduplicate within categories; cross-category
eligibility must be explicit and report distinct track totals separately.
Record source track ID, artist, title, source version, tag evidence, license
and whether lyrics exist/are eligible. No claim about exact tempo, instruments
or mood unless present in source/analysis. Do not substitute synthetic recipes
for this acceptance count.

## Candidate sources (not imported)

- MTG-Jamendo, pinned revision cafd8e20c265ed84f1e61f1c875327971f43a62f:
  https://github.com/MTG/mtg-jamendo-dataset — genre, mood/theme and instrument
  tags. Raw file 8.56 MB not retrievable through current connector. Source
  genre stats: blues 1,092, hiphop 2,670, lofi 246, trap only 64. No lyrics
  supplied; track audio licenses separate. Verify metadata license and
  per-track eligibility before copying any assets.
- FMA: https://github.com/mdeff/fma — metadata CC BY 4.0; recording licenses
  vary. Candidate supplemental source, especially legacy blues/jazz/pop/folk.
- Free Music Archive search: https://freemusicarchive.org/search — candidate
  for modern lo-fi, lo-fi hip-hop and trap; check per-track license.
- MusicCaps: https://huggingface.co/datasets/google/MusicCaps — 5,521
  audio descriptions, not necessarily a balanced genre dataset; verify
  annotation terms separately from audio rights.

No provider calls, model downloads, synthesis, or external transfer of private
material were made. Do not count any source-reported totals as imported rows.

## Windows offline usage

`music.cmd --styles --build`

`music.cmd --styles --genre blues --search shuffle --limit 10`

`music.cmd --styles --genre backsound --limit 100`

Build creates local/style-library.sqlite; existing knowledge-bank.sqlite remains separate.
