# Alpha 4 — Native recognition and ASR review

Use existing Studio CrisperWhisper via MCP, not a separate Whisper model. The observed recognition response contains text and provider only, without timestamps or confidence. Whole-song A/B ASR discrepancies were 23/180 and 44/180, respectively; fewer insertions but more substitutions on B. Human preference for B was based on a shorter listening scope. Do not infer that either is a better singer from these counts.

Offline review consumes existing recognition.json files and intended sectioned lyrics:

```powershell
py -3 -m yue2_music_director.cli asr-review --lyrics local/lyrics.txt --a local/A/recognition.json --b local/B/recognition.json --out results/asr-review.json
```

One minimum-edit alignment locates discrepancies by reference line, not audio time. Insertions between lines (including start/end) are retained separately. Repeated words can yield ambiguous edit locations. Review the audio against intended words; no automated acceptance, ranking, or score edits. Both inputs must have the same intended scope. Raw legacy JSON does not prove identical backend configuration. Private reports include lyric text; keep them local.

For future audio only, `native-recognise AUDIO --out NEW_DIR --url LOOPBACK_URL --confirm-recognition` checks local provider, installed model, ready state and idle Studio. Optional --language is passed through. No reference lyrics sent, no model download/settings changes, one inference call, no automatic retry. Keep Studio exclusively idle during inference; preflight is not an atomic server lock. Fresh output directory and submission marker prevent reuse of the same directory, not duplicates in other directories. On timeout or missing receipt inspect Studio and retained raw response before deciding next action. Existing A/B must not be recognized again just to use the new CLI.

Native karaoke/stems/process audio remain separate actions; do not overwrite derived assets or call processing automatically. Timing requires independently verified evidence; karaoke alignment alone cannot establish word fidelity.
