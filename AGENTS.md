# Repository agent instructions

Read [the active autonomous product roadmap](docs/AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md) first. The [generation-first architecture](docs/MUSIC_DIRECTOR_ARCHITECTURE.md) defines native execution, evidence and recovery rules. Existing historical experiment gates remain in force.

- Prioritize the P0 natural-language-to-song autonomous CLI on the Windows Studio host; Composer, Lyricist and configurable Nemotron provider are critical path. Do not require web UI, thousands of songs, Artist Memory or additional experiments for P0.
- Inspect actual source and native capabilities before implementing. Follow [the native control contract audit](docs/knowledge/NATIVE_CONTROL_CONTRACT.md): trace UI → schema → handler → conversion → engine input; distinguish native MIDI playback, score conditioning, and acoustic generation. Do not infer model control from UI or schema alone. Complete the relevant audit before adding performance or humanization specialists. Preserve prior evidence and local journals; never retry ambiguous external mutations or repeat completed inference. Keep Studio loopback and GPU jobs sequential. No model download, training, settings changes, new generation outside explicit budget, or publication without authorization.
- All private audio, unpublished lyrics, personal artist profiles, credentials, and local logs stay local and Git-ignored. Only use rights-compatible reference data; no detector evasion.
- Test offline with mock providers and failure injection; executable changes require green Windows/Linux CI before merge. Distinguish CI success from live execution and artistic quality. Use one short Windows launcher and a concise TXT report; operator is on another device.
- Keep technical documentation in English, current roadmap and evidence status accurate. Do not claim a role/service or dataset is built when it is only designed.

## Modular failure isolation

Separate provider, Composer, Lyricist, editorial review, native adapter, audio critic, persistence and interfaces. Keep role contracts independently testable. Save immutable per-stage inputs and receipts; failure must not replay completed upstream stages or trigger downstream work. Resume only validated matching identities; ambiguous mutations require explicit recovery. Test stage failures, cache integrity and non-duplication. Modular code in one process is not process-level fault isolation; persistent worker supervision is a later requirement.
