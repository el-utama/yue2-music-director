# v0.7 alpha 3 — acoustic evaluation (first stage)

Alpha 2 passed local score review and is merged. B remains the provisional baseline, not a fully validated production winner. Existing A/B renders are sufficient; no automatic audio jobs or old MIDI revalidation.

## Offline measurement

Requires an existing local FFmpeg installation with ffmpeg and ffprobe on PATH; no Python runtime dependency, model download, or GPU required. Use a fresh output path.

```powershell
py -3 -m yue2_music_director.cli acoustic-compare --a "local/A.flac" --b "local/B.flac" --out results/acoustic.json
```

Supported inputs: local mono/stereo FLAC or WAV, one audio stream, duration up to 30 minutes, sample rates 8–192 kHz. Embedded cover art is ignored. The command fingerprints original bytes, records tool versions, reads stream metadata and input integrated loudness, true peak and loudness range using loudnorm. The normalization filter's output is discarded; no audio file is written. Nonfinite values are null, and silence or below-gate loudness disables playback recommendations. B-minus-A deltas are descriptive. For comparable channel counts and measurable loudness, recommended gains attenuate to a common level while targeting at least 1 dB true peak headroom. Apply only during playback. Retain the original FLACs.

The report is not a vocal-quality score. Loudness and timing differences may originate anywhere in the mix. Keep reports and private audio local.

## Evidence from existing renders

Direct FFmpeg 7.1.5 measurement of the private A/B files: durations 188.519/185.439 s; integrated loudness -14.97/-16.60 LUFS, true peak +0.09/0.00 dBTP, LRA 8.90/7.10 LU (loudnorm method). Earlier ebur128 summary values differ slightly; record tool/filter provenance rather than assume equivalence. These measurements establish acoustic differences but not causal effects of pitch changes.

## Prosody acceptance still pending

Use the alpha 2 phrase-rhythm command with reviewed paired timing/transcript annotations to quantify actual word errors and delivery rates. The present implementation does not perform source separation, singing ASR, forced alignment, or pronunciation scoring. Investigate those capabilities separately and validate on sung material before treating results as reliable; never infer timestamps from bar numbers alone. Automatic expression correction remains gated on validated alignment and backend capability. No new score edits or renders are necessary for this stage.
