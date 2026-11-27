# MusicCaps annotation subset — CC BY-SA 4.0

Source: [Google Research MusicCaps](https://huggingface.co/datasets/google/MusicCaps),
Agostinelli et al., MusicLM: Generating Music From Text (2023).
[License](https://creativecommons.org/licenses/by-sa/4.0/).
Pinned mirror: https://github.com/simonw/musiccaps-datasette/blob/ecbb5a1f52e52cf09a38dd7698578ccca7cef353/data/musiccaps-public.csv
(Git blob 7982a549b8f2e244f2ada7227cf1076491b1725c). All adapted annotation data in musiccaps.jsonl is distributed
under CC BY-SA 4.0, with attribution to MusicCaps contributors and modifications
documented in musiccaps-manifest.json. This license does not cover underlying
YouTube recordings or lyrics.

517 distinct 10-second annotated clip IDs, selected from 5,521
source examples. Category assignment uses explicit AudioSet genre labels and/or
genre keyword mentions in source annotations, not independent listening.
A keyword can refer to an influence rather than a primary genre; manual review
still required. Normalized musical tags extracted from the aspect list, not
full captions. No titles or artist identities invented. Rare categories first;
100 combined candidates per category maximum. One category per clip ID.
Combined Incompetech/MusicCaps counts: {"blues":100,"jazz":100,"lofi":5,"pop":100,"indie":100,"folk":100,"backsound":100,"hiphop":100,"lofihop":0,"trap":15}.
Clip IDs and ISRCs are distinct identifier types; recording overlap across
sources is not established. Not a count of unique full songs or approved
recordings. No lyrics or audio downloaded. The original Incompetech manifest
continues to report its own 203 records. Rebuild the disposable v2 index via
music.cmd --references --build. No network or GPU at runtime.
