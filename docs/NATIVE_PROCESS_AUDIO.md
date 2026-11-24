# Native Process Audio integration contract

Status: source audit completed, live adapter not implemented. Reference: [pinned upstream MCP](https://github.com/timoncool/YuE2-Studio/blob/ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25/crates/music-server/src/mcp.rs), [processing implementation](https://github.com/timoncool/YuE2-Studio/blob/ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25/crates/music-server/src/processing.rs). Verify against installed Studio before writes.

| Tool | Audited contract |
|---|---|
| processing_start | song_id and optional stage objects denoise, lifter, naturalize, vst, master, normalize, optional region |
| processing_get | current run or finished preview; upstream UI consumes run.done and run.preview_ready |
| processing_keep | persists processed audio as a library track/version, optional label |
| processing_discard | destroys the pending processed audio |

Stages run in order: denoise, lifter, naturalize, VST, master, normalize. Omitted stages are skipped. The native preview is not the source file; the server hides the preview filename in serialized ProcessRun. The upstream UI uses /v1/processing/preview; it is not an advertised MCP file-export tool. Do not guess paths or bypass access controls. Validate an authorized local preview retrieval contract before evaluation. Keep/discard are writes and must not happen speculatively or affect an unrelated pending preview.

Native naturalize is full-mix band processing, not syllable/pitch repair. Native lifter supports denoise_strength, noise_floor, hf_mix, transient_boost and shimmer_reduction_db. Peak normalization can intentionally clip a configurable number of samples; do not equate it with true-peak headroom management. Native mastering requires a reference, and VST is user-specific. Do not invoke either without explicit supported configuration.

## Planned transaction

1. Read-only capability/schema and idle preflight; verify source identity and absence of any preexisting run/preview. If unknown, stop.
2. Select a single stage with explicit bounded settings and diagnostic rationale; journal source identity and request before submission.
3. Submit once; verify returned run identity, stage, request and source. Poll read-only with deadline; never retry on ambiguous response.
4. Retrieve the exact preview through a verified authorized local interface without committing it to the library. Measure duration, sample rate, peak, true peak, loudness and source integrity; compare native ASR once using same settings and reference. Preserve prior results and label unverified naturalness.
5. Return a provisional recommendation; keep/discard only after run ownership and semantics are verified. No automatic library mutations in first integration.

The next native experiment should isolate one effect rather than stack on the custom stem-delta candidate; the existing original is the comparator. No repeat generation, split, MIDI test or routine listening.
