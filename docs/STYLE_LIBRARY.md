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

## Source acquisition status

Current observed index contains 853 candidate IDs; 147 metadata slots remain. See [observed references](OBSERVED_STYLES.md) and [offline workflow](OFFLINE_KNOWLEDGE_WORKFLOW.md) for current counts. No observed-source lyrics or individual recording rights approval.

- MTG-Jamendo, pinned revision cafd8e20c265ed84f1e61f1c875327971f43a62f:
  https://github.com/MTG/mtg-jamendo-dataset — genre, mood/theme and instrument
  tags. Raw file 8.56 MB was successfully retrieved via the Git blob API in PR #122; the source explicitly restricts use to noncommercial research/academic purposes without written authorization. Excluded from production corpus. Source
  genre stats: blues 1,092, hiphop 2,670, lofi 246, trap only 64. No lyrics
  supplied; track audio licenses separate. Verify metadata license and
  per-track eligibility before copying any assets.
- FMA: https://github.com/mdeff/fma — metadata CC BY 4.0; recording licenses
  vary. Bulk archive access blocked; selected factual playlist and FMA album metadata separately imported, individual rights review pending.
- Free Music Archive search: https://freemusicarchive.org/search — candidate
  for modern lo-fi, lo-fi hip-hop and trap; check per-track license.
- MusicCaps: https://huggingface.co/datasets/google/MusicCaps — 5,521
  audio descriptions; 517 adapted annotation candidates imported under CC BY-SA 4.0 in PR #123, audio rights separate.

No provider calls, model downloads, synthesis, or external transfer of private
material were made. Do not count any source-reported totals as imported rows.

## Windows offline usage

`music.cmd --styles --build`

`music.cmd --styles --genre blues --search shuffle --limit 10`

`music.cmd --styles --genre backsound --limit 100`

Build creates local/style-library.sqlite; existing knowledge-bank.sqlite remains separate.

## Use a selected style in autonomous production

`music.cmd --styles --build` indexes the original recipes for local browsing.
`music.cmd --styles --genre folk --limit 10` lists IDs and style descriptions.

`music.cmd --job new-folk --request "A quiet goodbye" --style-id folk-001`

This previews the exact original recipe with zero provider or Studio calls; no database build is required for selection itself. Only an explicit `--confirm-run` authorizes the usual production budget and sends the selected authored style (not unreviewed observed track metadata) as optional Composer guidance. The operator's request and typed requirements take precedence. Resume with the existing job ID and confirmation; the saved style remains frozen even if the library changes. Changing the recipe requires a new job. This is advisory text, not a verified native tempo or arrangement control. No live generation has been run for this feature.
