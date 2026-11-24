# Offline finishing selection

`finishing-select --source ORIGINAL.flac --lyrics LYRICS.txt --baseline-asr BASELINE.json --language en --custom CUSTOM_RUN_DIR --native NATIVE_RUN_DIR --out NEW_SELECTION.json`

Supply either or both completed experiment directories. Native currently supports the headroom continuation shape only. The selector verifies source/reference/baseline hashes, candidate hashes, recorded acoustic measurements, transaction identity and recognition receipts, and recomputes multilingual text scores from saved native recognition. No Studio access, new ASR, audio generation, processing or library mutation. Reports are local trusted evidence, not signed records; no fresh acoustic measurement.

Eligibility: compatible source/format/duration, completed ASR non-regression, original effect-specific loudness guards and measured final true peak <= -1 dBTP. The headroom policy is now common to both methods. Rank eligible candidates only by primary text disagreement count, not naturalness. A unique eligible best is provisional, ties and no eligible candidate retain original; original fallback is not necessarily release-ready. No automatic final acceptance. Do not automatically rerender or re-recognize rejected candidates.

Real experiment evidence: custom stem-delta had 42/180 word edits and near-full-scale sample peak; use its saved actual true-peak measurement before deciding eligibility. Native Naturalize + fixed -0.60 dB gain measured -1.05 dBTP, -17.67 LUFS, unchanged duration and LRA, unchanged 44/180 WER and 141/712 CER. Native continuation with pending preview worked locally. Neither result proves improved musical naturalness. The selector is not yet a full diagnosis/correction or orchestration loop.
