# Audio Finishing Specialist — conservative whole-mix headroom

The standalone Windows command uses the verified retained source (parent or
continuation), never a new Studio job. It is separate from historical native
stem/effect/recognition experiments.

```powershell
.\music.cmd --finish JOB
.\music.cmd --finish JOB --confirm-run
```

The first command is a plan/status view. It reads the retained source and
estimated gain; it does not render or mutate the song. The launcher may write
its standard local text log. Confirmation remeasures the source with local
FFmpeg/ffprobe. The policy is fixed attenuation only: leave a source already at
or below -1 dBTP unchanged; for an otherwise finite, non-silent input with
true peak above -1 and at most 0 dBTP, target -1.05 dBTP with downward hundredth
dB rounding, at most 1.5 dB attenuation. Positive true peak, nonfinite or
unreliable loudness, unsupported geometry or a failed measurement stop safely.
This is an internal headroom policy, not a universal mastering target.

Input must be mono/stereo 16/24-bit FLAC, 8–192 kHz, 1–210 seconds. The source
SHA-256, actual decoded sample count per channel, exact duration, sample rate,
channels, codec and bit depth are verified. The candidate is 24-bit FLAC
(16-bit input is widened to minimize new quantization; no added musical
detail). Only a constant volume filter is applied, without resampling, fades,
EQ, compression, limiter, stems or clipping repair. A second PCM hash check
verifies the exact 24-bit decoded samples against the planned constant gain
on the source. A post-render acoustic measurement must have true peak <= -1
dBTP, expected TP and integrated loudness delta within 0.15 dB/LU, LRA within
0.5 LU, and identical decoded timeline/rate/channels. The source hash remains
unchanged. Metadata/chapters are not carried into the candidate; later
packaging must attach the intended release metadata explicitly.

Private output: `results/audio-finishing/JOB/gain-v1/`. Plan and report bind
the source result and audio hashes. A safe original receives a no-change
receipt and no duplicate FLAC. A verified candidate is a separate
`candidate.flac` with its own hash. Existing completed output is verified
without FFmpeg or another render. If interrupted, an existing staged
candidate is verified before any promotion; a corrupt/incomplete candidate
is preserved and refused, never overwritten. A different explicitly selected
`--finish-id NAME` creates a separate variant and keeps earlier evidence.
An incomplete plan requires the same tool versions; do not remove evidence
or bypass a stale lock blindly.

No provider, Studio, ASR, MOSS or GPU calls; no library mutation. A
candidate is not automatically preferred, artistically improved, release
approved, or published. Original remains the preferred variant. The
constant-gain PCM proof establishes the unchanged sample timeline, not
acoustic accuracy of existing LRC/SRT. Export still packages the original. The separate [release assembly](RELEASE_ASSEMBLY.md) command can package an explicitly listened-to and approved candidate from existing export assets.

Regression tests generate synthetic mono/stereo FLAC with actual FFmpeg,
including gain and waveform checks, safe no-change, silence, interrupted
output, input mutation, preserved receipts and no repeated rendering.
Windows and Linux CI must have FFmpeg/ffprobe; synthetic test evidence is
distinct from a new live check on an operator's retained recording.
