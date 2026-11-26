# Artistic generation runner (experimental P2/P3)

The generation-first runner reuses the existing native draft transaction and the P1 offline review. It is a deterministic bounded director policy with a human/assistant-authored artistic intent, not yet a self-directed language-model composer or a calibrated musical judge.

From the repository root on Windows:

```powershell
.\draft.cmd --artist-demo
.\draft.cmd --artist-demo --confirm-run
```

The first command is offline plan-only, with zero Studio calls; the second explicitly permits at most one native score plan, one full song and one local ASR. The bundled original English blues-soul ballad brief is a new research fixture, not a copy of a reference song or a replacement for the operator's private brief. It uses the reviewed-native route, fixed seed 137, 210-second cap, no additional adapters or settings changes, and no section steering. It lets YuE2 decide melody, actual key/tempo, harmony, phrasing and form. The intent includes a desired emotional arc and performance direction, reflected in the supplied style and lyrics; the narrative fields are not unsupported extra Studio request parameters.

For a private song, keep the existing six-field `local/brief.json` and put a separate `local/intent.json` using the bundled intent as schema example. Run `draft.cmd --artist` (offline) or `draft.cmd --artist --confirm-run` (bounded execution). Intent schema artist-intent-v1 includes:
- route auto, reviewed_native or explicit_score. Auto chooses reviewed_native when any mandatory score constraint or follow_lyrics is requested; otherwise direct_native. Explicit_score requires local/score.abc; no planning job.
- Concept, emotional arc, performance direction, section purposes, constraints (see [musical review](MUSICAL_REVIEW.md)), a map from known soft flag codes to predeclared retention rationales, explicit follow_lyrics boolean, and exact budget matching route. Only 0/1 planning, one synthesis and one recognition are supported. The brief duration is the hard score-clock limit on supplied plans, and the existing audio duration screen after synthesis. No guaranteed audio length.
- Soft flags without a predeclared rationale stop the reviewed/explicit route. Known flags may be retained with documented rationale, never overriding a hard violation or unassessable score. This is a policy decision, not proof of quality. No automatic score edits, retry, fallback, or new seeds. The direct route reviews the saved score after synthesis; it cannot guarantee preferences or an exact musical form beforehand.

## Terminal failure inspection

If the artist demo reaches a failed song job, use `draft.cmd --artist-demo --inspect` to retrieve the retained job's native phase/message and score clock. This read-only Studio operation writes local `job-inspection.json` and the existing TXT transcript; it never submits a plan, song or ASR. A terminal failed job is not a timeout. The 2026-11-26 first live run passed planning and native MIDI but failed synthesis; root cause pending the native error, not a musical result. Do not resubmit.

## Local artifacts and recovery

The run identity is fixed by the brief, with intent and optional explicit score hash frozen in the manifest under results/drafts/artist-<brief digest>. Changing the intent/route under the same run is refused. Native planning uses a durable attempt marker and known job ID, bounded polling, raw retained plan and verified SHA, then an independent review decision. The native draft transaction rechecks configuration and native MIDI compatibility before supplied-score synthesis; the planned route must match the effective planner configuration. A plan stopped at review does not start synthesis. Cached reports, completed audio and recognition receipts are reused. If a known job is pending or ASR was blocked before submission by Studio activity, rerun the **identical** confirmed command only to resume; never delete a journal, retry an unknown submission, change the model or cancel unrelated work. The shared lock covers planning through evaluation.

The transcript is results/draft-output.txt; it reports route, budget, stop reason or completed local audio and report location. Private manifest, receipts and score/audio fingerprints remain local. The runner retains actual saved ABC when available, verifies song/job and lyric conditioning, and checks a supplied score's semantic identity. Native MIDI compatibility is mandatory before supplied-score synthesis. Direct-route missing ABC is explicitly unassessable; no pre-review claim. Existing demo and study commands are unchanged.

Technical peak/duration and local ASR text screens remain diagnostic; lyric conditioning is not proof of actual singing, and the existing ASR reference counts all tagged lyric text including directions. The bundled demo avoids whole-line instrumental directions in lyrics, using style for those instead. Custom cue-aware ASR reference handling and a separate exact sung-text contract are still open. Listening verdict remains unrated; automatic acceptance and naturalness/phonetic verification are false. No finishing, export, model change or GPU sweep. CI uses mocked transactions, not live inference. The revised artistic runner requires a real local validation before claiming it works on Studio.

See [architecture and roadmap](MUSIC_DIRECTOR_ARCHITECTURE.md). Next gate is the one authorized original-song live experiment, followed by listening and controlled comparison only if useful.

### Verified first live failure and bounded recovery (2026-11-26)

Read-only inspection established terminal native `failed` status and the explicit engine-loading GPU out-of-memory message. Retained score clock 200.281690 s, below 210 s cap; native MIDI passed. The message mentions a managed writing assistant as a possible competing workload, not proof it was running. Check GPU use (`nvidia-smi`) and unload a running managed writing assistant or close other GPU applications before retrying; do not lower quantization, change the engine configuration, cancel unrelated jobs or delete the original journal. Native Studio exposes `assistant_runtime`, `assistant_stop`, `studio_system` and `engine_logs`; no automatic invocation of the mutation tools. The existing stock configuration must pass again, with exact planner-configuration equality.

After explicit authorization and freeing competing VRAM, `draft.cmd --artist-demo --recover-oom --confirm-run` permits one additional synthesis and one local ASR, zero new composition jobs. It requires the original retained manifest, reviewed plan/score and request hashes, original policy/configuration, a freshly read terminal failure with the native model-loading OOM message and zero library songs. It creates `oom-recovery-1` under the existing run, preserves original evidence, and reuses the same native score, brief, seed, settings and MIDI gate. Repeating the exact recovery command resumes its own known journal only; a second failed recovery ends the experiment. No model switches, engine restarts, automatic retries or new score generation. The `recovery.json` records the incremental zero-plan/one-song/one-ASR budget; draft report intent budget remains the original plan-inclusive policy. Software tests do not establish adequate live VRAM or musical success.

### First live run — reported GPU memory failure (2026-11-26)

Operator reports Studio displayed a GPU out-of-memory popup while the engine was loading the model. Exact popup wording and native phase/message remain unverified. One native plan and MIDI conversion succeeded; one song job failed, no ASR or audio acceptance. Preserve the plan and journal. Retrieve the existing job with `draft.cmd --artist-demo --inspect` after the diagnostic fix; do not resubmit. Distinguish model loading, retained memory and other GPU workload before choosing a recovery strategy; no automatic model downgrade, engine restart or new inference authorized. The 8 GB stock reference passed earlier runs but is not a guarantee against memory exhaustion.
