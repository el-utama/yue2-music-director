# Native Process Audio integration contract

Status: initial preview adapter implemented; live Studio contract and preview capture remain unverified. Reference: [pinned upstream MCP](https://github.com/timoncool/YuE2-Studio/blob/ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25/crates/music-server/src/mcp.rs), [processing implementation](https://github.com/timoncool/YuE2-Studio/blob/ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25/crates/music-server/src/processing.rs). Verify against installed Studio before writes.

| Tool | Audited contract |
|---|---|
| processing_start | song_id and optional stage objects denoise, lifter, naturalize, vst, master, normalize, optional region |
| processing_get | current run or finished preview; upstream UI consumes run.done and run.preview_ready |
| processing_keep | persists processed audio as a library track/version, optional label |
| processing_discard | destroys the pending processed audio |

Stages run in order: denoise, lifter, naturalize, VST, master, normalize. Omitted stages are skipped. The native preview is not the source file; the server hides the preview filename in serialized ProcessRun. The upstream UI uses /v1/processing/preview; it is not an advertised MCP file-export tool. Do not guess paths or bypass access controls. The initial adapter uses the upstream documented local media/processing workspace, requiring it to be empty initially and to contain exactly one new regular FLAC file after the matching run completes. It never guesses a preview filename or contacts an undocumented endpoint. Exclusive Studio use is required; the server does not return a preview path bound to the run ID. Keep/discard are writes and must not happen speculatively or affect an unrelated pending preview.

Native naturalize is full-mix band processing, not syllable/pitch repair. Native lifter supports denoise_strength, noise_floor, hf_mix, transient_boost and shimmer_reduction_db. Peak normalization can intentionally clip a configurable number of samples; do not equate it with true-peak headroom management. Native mastering requires a reference, and VST is user-specific. Do not invoke either without explicit supported configuration.

## Planned transaction

1. Read-only capability/schema and idle preflight; verify source identity and absence of any preexisting run/preview. If unknown, stop.
2. Select a single stage with explicit bounded settings and diagnostic rationale; journal source identity and request before submission.
3. Submit once; verify returned run identity, stage, request and source. Poll read-only with deadline; never retry on ambiguous response.
4. Retrieve the exact preview through a verified authorized local interface without committing it to the library. Measure duration, sample rate, peak, true peak, loudness and source integrity; compare native ASR once using same settings and reference. Preserve prior results and label unverified naturalness.
5. Return a provisional recommendation; keep/discard only after run ownership and semantics are verified. No automatic library mutations in first integration.

The next native experiment should isolate one effect rather than stack on the custom stem-delta candidate; the existing original is the comparator. No repeat generation, split, MIDI test or routine listening.


## Initial adapter

`native-process-preview --source ORIGINAL.flac --song-id SONG_ID --effect naturalize --amount 0.2 --out NEW_DIR`

Read-only preflight by default. Explicit loopback MCP endpoint required. With `--confirm-preview`, submit exactly one native preview, journal the request and receipt, poll the matching run, copy the preview to a new local directory, and measure acoustic QA. Supported stages are naturalize and lifter only (0.05–0.3 intensity, explicitly specified stage settings). Lifter requests transient boost only; upstream code may still perform additional STFT processing. No source overwrite, no generation, no keep/discard, no model/settings changes. An existing run or nonempty workspace blocks submission. Unknown source-file schema blocks submission. Native preview is left pending intentionally. No blind retry after submission.

Acoustic gate requires equal reported duration, true peak <= -1 dBTP and loudness difference <= 1 LU; these are conservative engineering limits, not an artistic judgment. Optional ASR screening is enabled by passing --lyrics, --baseline-asr, --language and --confirm-recognition together with --confirm-preview. After acoustic pass, the recognition guard exempts only the exact completed matching processing record, checked before and after recognition. No other busy-state exception is added. The installed server may still reject recognition while a preview is pending; the report records a blocked result without retry. A regression provisionally retains the source, non-regression is not acceptance. The acoustic report is retained separately from evaluation.json. Sample rate and channel count must also match. No automatic acceptance. Mock tests cover the transaction; actual Studio response schema and preview location are not yet confirmed. Do not run this on an occupied Studio or assume a failed receipt means no preview was created.

## Interrupted run inspection

`native-process-inspect --source ORIGINAL.flac --out EXISTING_DIR` reads local journal/report evidence and checks source and preview hashes, run identity and recognition receipt where available. It never connects to Studio, submits work, or modifies files. The observed run ID is journaled before polling continues. Recognition readiness is checked before confirmed processing if screening is requested. Incomplete evidence is reported as unverified, with the original retained provisionally. The command is an inspection, not a resume/retry operation; it cannot recover an unknown server outcome or authenticate tampered local journals. Never delete journals to force a retry.

## Headroom-only continuation

Real native Naturalize preview captured successfully: same 48 kHz stereo, duration and LRA; loudness -16.60 to -17.07 LUFS, true peak 0 to -0.45 dBTP. It was blocked by -1 dBTP threshold before ASR. Do not rerun the effect. Use `native-process-continue --source ORIGINAL.flac --out EXISTING_PREVIEW_DIR --lyrics LYRICS.txt --baseline-asr BASELINE.json --language en --confirm-recognition` with the existing loopback endpoint. Validates original transaction fingerprints and remeasures saved preview. Only peak-only failure is eligible (raw effect loudness delta <=1 LU, raw true peak between -1 and 0 dBTP, same format/duration). Applies one fixed attenuation to -1.05 dBTP target with 0.05 dB margin, at most 1.5 dB. Remeasure final audio, require true peak <=-1, unchanged format/duration, gain-consistent loudness within 0.15 LU and final loudness delta <=2.5 LU including gain. These are engineering bounds, not quality evidence. No limiter, no repeat native processing or library mutation. One ASR call only after pass; reject changed screening inputs or unrelated pending run. Save all continuation evidence in headroom-continuation; never overwrite or automatically retry. New explicitly screened previews use this continuation automatically if eligible. Offline inspect reports continuation evidence presence, not a verified final selection. Live continuation ASR remains unverified.
