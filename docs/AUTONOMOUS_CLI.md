# Autonomous CLI (active alpha)

Use `music.cmd --advisor` for read-only [hardware and configuration advice](HARDWARE_ADVISOR.md). The current production CLI uses its documented reference gate. Alternate runtime/model production profiles remain future work.

For first-ever use, follow [fresh-host setup](FRESH_INSTALL.md#5-prepare-full-autonomous-production-only-if-wanted) before confirming production. The old host's DPAPI provider record, model files and job receipts are not installation prerequisites or transferable evidence. Export-only workflows need neither a hosted provider nor this gate.

## Historical live status — 2026-11-27

Hosted text and full autonomous generation ran successfully on the operator host; the subsequent reviewed-native retained continuation completed without repeating synthesis or ASR. Human listening, cover prompt and original single-song export were favorable/successful for that retained example. Opening policy v3, source provenance, export timing hardening, human feedback and audio finishing are separate implementation/CI milestones, not additional live validations. The current [native audit checkpoint](NATIVE_AUDIT_CHECKPOINT.md) records subsequent completion/lyric verification fixes and saved lyric schedule evidence. See [active roadmap](AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md), [feedback](HUMAN_FEEDBACK.md) and [finishing](AUDIO_FINISHING.md). Use the completed-source commands for retained jobs rather than production resume. Historical development reports below describe their earlier state; they are not requests to repeat tests.

One natural-language request drives separate Composer, Lyricist, editorial reviewer, native production, neutral listening and advisory Director judgment. Existing creative and native journal contracts are reused; no separate song_create implementation. The default is plan-only. Confirmed scope: four text completions sent to explicitly configured HTTPS provider (including brief/lyrics and selected text evidence for final review), one native score plan, one native song, one explicit ASR, two CPU excerpts. No raw audio, file paths, credentials or raw native logs are sent by the final review payload. Native Studio automatic karaoke may also run as configured by Studio. No automatic revision or finishing; result provisional or review required.

Development entry: `music.cmd --confirm-run` prompts for the idea, defaults to English and a 195-second cap, generates a local job ID. Override via --language and --duration. Resume known job using `music.cmd --job JOB --confirm-run`; it reads retained request and parameters. Configure once using `music.cmd --setup` in the Windows terminal (NVIDIA NIM, OpenRouter explicit :free model, or custom HTTPS endpoint; exact model ID from the operator; NVIDIA preset offers the documented Nemotron 3.5 Super VL 120B ID as an editable default). Key is entered without echo, protected by Windows current-user DPAPI in Git-ignored local/llm-provider.json. Setup never contacts the provider. Optional `music.cmd --check-provider` authorizes one synthetic JSON completion per distinct configured model, no song data or GPU work. Environment configuration remains an explicit alternative; partial environment settings fail rather than mixing with the saved key. Provider quotas/charges apply; no paid fallback. Do not ask for live testing until CI passes.

Artifacts: results/autonomous/JOB (private), separate creative receipts, production native journal, listening packet and final result. All normal stages run sequentially. Shared draft and critic locks protect existing runner paths. Completed native reports and validated listening receipts are reused; an unresolved attempt stops safely. No automatic retry on ambiguous text/ASR/captioner/native submissions. For an unresolved text stage only, `music.cmd --job JOB --retry-text ROLE --confirm-run` permits one separately approved extra completion using identical inputs/provider; the original attempt is retained, a second unresolved retry stops. Completed stages are not rerun. This does not authorize extra GPU or ASR work. Never use this flag for a completed or previously unattempted stage. If MOSS unavailable before an attempt, the same job may resume without resynthesizing. An abrupt process crash can leave a lock. See [local lock inspection and recovery](LOCAL_LOCK_RECOVERY.md); only independently verified stale owners with known journal context qualify for explicit marker recovery. No journal replay or background service is authorized. A continuation's unresolved Director attempt has its own one-retry command: `music.cmd --continue-plan JOB --retry-text director --confirm-run`. Job configuration immutable; changing model, prompt or request may require a new job. The default CLI does not reliably enforce arbitrary natural-language hard constraints or infer verbatim supplied lyrics from prose; use the explicit [typed creative spec](TYPED_CREATIVE_SPEC.md) for exact operator lyrics and supported typed constraints. Hosted typed schema live compatibility remains unverified. Approved revision automation remains out of scope; the default is for simple original vocal-song requests. This is not the finished P0 acceptance gate.

Tests inject provider and listening failures and mock native stage reuse; existing native tests cover actual journal/receipt handling. CI does not connect to real Nemotron or Studio. Live provider and end-to-end score-first recovery are recorded above; independent generalization and full knowledge/artist-profile acceptance remain pending. Local artist profiles, offline indexes and explicit authored-style selection are implemented and CI-tested; see the current [project memory](../PROJECT_MEMORY.md).

Provider endpoint/model references: [NVIDIA NIM LLM API](https://docs.api.nvidia.com/nim/reference/llm-apis), [Nemotron 3.5 Super VL](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b?section=deploy), [OpenRouter chat completion](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request). The default model name is not proof of the operator's account access or free quota.

## Use an explicitly selected artist profile

For a new song, `music.cmd --artist-profile "The Midnight Echo"` previews a compiled typed
spec (with optional `--profile-revision N` and `--creative-spec PATH` overrides).
Add `--confirm-run` for the existing production budget. Existing jobs resume
from their frozen spec and profile provenance without looking up the current
profile. See [Artist Memory](ARTIST_MEMORY.md). No automatic profile choice.

## Select an original offline style

See [offline knowledge workflow](OFFLINE_KNOWLEDGE_WORKFLOW.md) and [Style Library](STYLE_LIBRARY.md). Build and browse with `music.cmd --styles --build` and `music.cmd --styles --genre folk`. Preview a new job with `music.cmd --job folk-song --request "A quiet goodbye" --style-id folk-001`. Add `--confirm-run` only to authorize actual production, repeating all new-job arguments. Resume using the saved job ID and confirmation; recipe identity is frozen and cannot be changed on an existing job. The Composer receives only the chosen authored recipe as advisory context, not observed-reference metadata or historical lyrics. PR #126 passed CI; no new live production or native control guarantee. Existing default jobs are unchanged. Historical knowledge descriptors are separately opt-in, never automatic.


## Historical knowledge in autonomous production (explicit opt-in)

Build the bundled index, then preview without provider or Studio calls:

```cmd
music.cmd --knowledge --build
music.cmd --job knowledge-song --request "A quiet goodbye" --knowledge-query home
```

Preview prints local source provenance and selected numeric descriptors (up to
three works per role); it is not a job receipt. A query with no matches in
either role stops. To authorize a new production job with this context, repeat
the preview command with both `--confirm-run --confirm-knowledge-context`.
Only versioned bounded numerical fields and advisory guidance enter
Composer and Lyricist requests; no source title, query, work ID, hashes,
raw lyric, melody, recording, or database is sent as the knowledge payload.
The normal authorized song brief and generated lyrics still enter the existing
text stages. A role with no matches receives empty observations. Operator
supplied exact lyrics still bypass the Lyricist provider. No new calls or
GPU/embedding operations are added by retrieval. The historical corpus is
seven works, not a representative contemporary genre model.

Resume an existing knowledge job with
`music.cmd --job knowledge-song --confirm-run --confirm-knowledge-context`.
Snapshot and checksum are frozen in job identity; the original database need
not still exist. Do not add/change query on an existing job. Plan-only resume
may inspect frozen knowledge without consent. The separate retained-plan
continuation only validates completed creative receipts using frozen context;
it does not re-send it to Composer/Lyricist or accept query overrides.
Observed references remain local-only candidates. Original style selection
can coexist; explicit user constraints take precedence. The optional feature
does not establish artistic quality or modern genre coverage.


## Automatic lexical retrieval from the song brief

Optional `--knowledge-auto` derives a short local lexical query from the
brief after Unicode normalization (up to 12 distinct alphabetic terms, with
common English and Indonesian function words such as `never` and `tanpa`
removed from the query). The creative stages still receive the original brief.
It uses the same historical role-specific FTS5 search and numeric-only payload.
Matches reflect word overlap. Preview a brief with this command.

```cmd
music.cmd --job auto-song --request "A song about home" --knowledge-auto
```

Preview reports the exact derived query, matched local evidence or explicit
abstention (`no_terms` or `no_matches`), with zero provider/Studio calls.
Build the historical index first; a missing/corrupt index is an error if a
query needs it, not a fabricated no-match. Confirmed production requires
both `--confirm-run --confirm-knowledge-context` with the new-job arguments.
If no matches, no historical payload is sent; ordinary creative stages may
proceed within the existing budget. A matched lexical term is not proof that
a historical work is stylistically relevant. Explicit manual `--knowledge-query`
remains available; do not combine both modes. Resume with the job ID and both
confirmation flags; the frozen match or abstention is reused without another
database search. No extra provider calls or GPU work. Existing manual and
legacy jobs retain their exact previous identity.

## Read-only readiness check

Run `music.cmd --ready` on the Windows Studio host before starting a new
song if readiness is uncertain. It checks local provider configuration
without contacting the provider, FFmpeg/ffprobe presence, local production
mutex markers, the live advertised native schema, idle status, Whisper
readiness and the existing stock reference gate. It does not wait for a busy
Studio, download, generate, reserve a job or modify configuration. Add
`--media-dir PATH` only if you want to check the MOSS managed files using
the exact existing Studio media directory; never scan drives.

Exit 0 means the checks performed passed, not that inference or the hosted
provider is guaranteed ready. Exit 2 means a blocker was observed. The
report distinguishes untested provider authentication, available GPU
memory, and uninspected MOSS files from observed readiness. It is a
point-in-time snapshot, not a reservation; existing submission guards still
apply. No keys, private paths, raw tool responses or raw errors are printed.
No automatic repairs. For a lock blocker inspect the named lock, never
delete a marker blindly. For provider authentication only, the existing
separately authorized `--check-provider` makes a synthetic completion.

## Provider authentication troubleshooting

Live Windows report 2026-11-26: configuration saved, then HTTP 403 and repeated HTTP 401. No successful provider completion; no Studio inference. NVIDIA's [model API reference](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b/apireference) confirms the preset endpoint and model ID. HTTP 401 means authentication rejected, HTTP 403 means access denied; the exact cause is not known. The prior working agent may use a different provider or credential. Verify the provider first, not only the model name. For NVIDIA use a valid [NVIDIA API key](https://build.nvidia.com/settings/api-keys) with [Public API Endpoints access](https://docs.nvidia.com/ngc/latest/ngc-user-guide.html), not a key from another API. Do not rotate or revoke credentials used by another working agent unnecessarily. `music.cmd --check-provider` shows configuration source, host and model without exposing credential bytes. Environment settings override saved local config; setup warns when this is the case. No automatic retry or provider change. This diagnostic update does not fix account-side access or establish that the key was entered correctly. Never paste keys into a chat or support log.

NVIDIA-specific diagnostic now separates the read-only hosted model catalog GET from a synthetic chat completion POST, using the same stored credential and no redirects. Catalog 401/403 stops before completion; catalog 200 does not demonstrate inference access. An absent model is advisory, not proof it is unavailable. Credentials containing whitespace, control or non-ASCII characters are rejected before network calls. This changes diagnostics and input validation, not NVIDIA account permissions. Recent [NVIDIA forum report](https://forums.developer.nvidia.com/t/403-authorization-failed-on-integrate-api-nvidia-com-v1-chat-completions-while-v1-models-returns-200-request-to-enable-public-api-endpoints-on/383161) documents the catalog/inference distinction. No access to, import of, or modification to Hermes credentials.

## Live JSON contract follow-up

Operator report: local config loaded, NVIDIA catalog HTTP 200, exact Nemotron VL model present; completion parsed as JSON but failed the exact smoke assertion. Earlier HTTP 401/403 did not recur in this check. Actual returned object was not recorded, so the reason for the mismatch is unknown. Do not change credentials. The [exact hosted model API reference](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b/apireference) documents strict JSON schema and thinking template controls. For this exact endpoint/model pair, use role-specific schema constraints, independently validated local output, a small no-thinking smoke request, and the documented 16384 token completion budget for creative calls with thinking enabled. Other providers/models retain the original request shape. No automatic fallback or retry. Version the provider policy in job identity; existing jobs using the older policy must not silently resume with changed parameters. Smoke reports only schema shape on mismatch, not raw content. Offline tests mock transport, so live support is still to be verified.

## Reviewed score-first autonomous policy

First real autonomous take was marked engine_truncated=true. Retained audit: 194.998667 s audio, 195 s cap, 312.1951219512195 s native score clock, 54 lyric lines, missing notated verse#3 and structural mismatch. Native score's bridge/last chorus/outro start after the cap on the score clock; this is not acoustic alignment. New jobs use reviewed_native with follow_lyrics steering, one native plan and the existing deterministic musical review/MIDI gate before synthesis. Advisory creative target reserves 3–15 seconds under the cap; this is a heuristic, not an audio duration guarantee. Unassessable notation, over-cap score or unresolved structural flags stop before song synthesis; no automatic replan/rewrite, no ASR/MOSS or Director call on stop. Plan-stop evidence stays separate from completed result. Existing jobs remain immutable, inspect only with the prior ending audit; this release does not migrate their generation policy. Reviewed audio evidence validates exact retained plan, score and request hashes. Per-role progress logs do not print private text. A pinned native replay classifier provides length/memory when the top-level flag is missing and sufficient replay evidence exists. New score-first workflow must be live-tested explicitly; original song is not repaired. 

## Variable meter/key review

Live score-first run stopped correctly before synthesis, but the reason was a local unsupported-notation error, not a measured over-cap score. Pinned upstream [native ABC parser](https://github.com/timoncool/YuE2-Studio/blob/bfd35a0e594cbd1268557833001d5675ebbdd2d3/crates/music-server/src/score/abc.rs#L293-L375) supports per-voice M:/K: fields and synchronized inline [K:] changes. Extend the local reviewer to track meter lengths, key timelines and note offsets, reject mismatched voice grids, and use cumulative duration for review. The legacy non-native parser remains unchanged. The original stopped plan may be rechecked with `music.cmd --review-plan JOB`, offline with no LLM/Studio calls; output in results/plan-review-output.txt. Prior plan decisions remain immutable; recheck does not authorize synthesis or migrate the job. A reviewed decision still needs a separately designed continuation protocol and native MIDI. Actual retained ABC not provided to developer; fixtures exercise upstream-supported syntax, live compatibility pending.

## Continue a parser-blocked retained plan

Live recheck on main 289b0bc: original score now retained with 188.333333 s score clock against cap 195 s, 58 bars, 72 BPM, initial Bb, variable meter, no hard/soft flags. Verse 1 lasts 90 s, one chorus and a 45 s bridge; Ins melody contains 5 attacks, not proof of sparse rendered accompaniment. Artistic quality remains unknown. Use `music.cmd --continue-plan JOB --confirm-run` for a separately authorized continuation only after a previously unsupported score now passes. Existing creative receipts are validated/reused and existing native planning receipts copied into one fixed continuation-1 folder; original stopped artifacts remain unchanged. Recheck and identity mismatch fail closed. No new native plan, Composer, Lyricist or Reviewer calls; budget is one song, one ASR, two CPU excerpts and one Director text call, native MIDI check and stock configuration required. Repeat same command only for a known continuation; native journals prevent duplicate submission. An ambiguous incomplete initialization stops, not auto repaired. Result under the original job's continuation-1/result.json; no automatic acceptance or revisions. Not live tested yet.

## Reviewed take verification after continuation

Live continuation on 780d670: retained creative stages, native MIDI gate, one song completed, native saved score/lyrics verified and engine completion not_flagged; ASR invoked. Later listening verifier failed with generic retained reviewed score identity mismatch. Code audit found inconsistent comparison: synthesis verifies score semantics while listening demanded identical bytes and normalized source line endings on read. Keep independent hashes for planned and imported score, match pre-render and saved-score review receipts, compare semantic signatures including meter/key timelines, and emit precise failure labels. Integrated regression now invokes the real listening verifier after native report creation and tests equivalent formatting versus modified notes. Exact local mismatch predicate not confirmed without local artifacts. Repeat the same continuation command only after green CI: completed native report is reused, no new synthesis/ASR if retained evidence matches. Remaining budget is MOSS and Director. No automatic repair or new song.

## Intentional opening and vocalist direction (reviewed-score-v2)

Operator rated the second live take good in all five musical categories; reported no intro and female vocalist. The latter is not a fault by itself. New jobs use a versioned direction guide: explicit instrumental_intro or direct_vocal, vocalist identity, narrator perspective and musical rationale within the existing Composer performance string. Lyricist must include a wordless [Intro] when planned, or begin with a sung section for direct_vocal. Local score gate checks actual first notated section and vocal activity; this does not guarantee acoustic onset or voice identity. Editorial reviewer checks story, style and explicit user requirements. Director receives advisory-evidence limits and opening score metrics only for the new policy. Old reviewed-score-v1 jobs retain exactly their original guidance and constraints; no migration or automatic generation. No new provider schema or call budget. No forced intro on every song, no fixed artist voice, no live validation yet. Finishing and Artist Memory are separate work.
 
New opted-in historical contexts include descriptive lexical repetition, melodic event ratios and automatic harmony token statistics; see [Knowledge Bank](KNOWLEDGE_BANK.md#descriptive-craft-analysis-v3). Saved v1 contexts preserve the exact earlier payload. Rebuild the derived index for new retrieval; no raw reference transfer.


## Structured default Composer direction

A reported Indonesian natural-language job reached the Composer provider but
returned ordinary performance prose instead of the old required headers.
No downstream stages ran. New autonomous jobs use
`reviewed-score-v5-structured`, with separate required opening, vocal,
narrator and musical_rationale fields in the Composer JSON contract.
The local validator converts a valid response into the established canonical
performance format; a complete and valid legacy-format response remains
acceptable for providers without schema enforcement. Missing decisions are
not invented. The existing score timing gate remains mandatory.
Old v1/v2/v3 and explicit v4 typed jobs preserve their original contract,
prompt and receipt identity. An old rejected v3 job may use its existing
explicit one-time retry, but is not silently migrated or repaired; this may
still fail. Do not overwrite a rejected receipt or retry blindly.
Offline tests cover structured responses and legacy preservation. Hosted
schema compatibility and live acceptance remain unverified.

## Duration-only plan fit preview

Live P0 follow-up: structured Composer, Lyricist and Reviewer completed;
sole score-review hard violation was a 207.887-second score against a
195-second cap, with zero soft flags. No song was submitted. A read-only
`music.cmd --review-plan JOB --fit-duration` checks whether a single global
quarter-note tempo increase (at most 10%, with three seconds of reserve)
would pass the full existing local review. No notes, lyrics, chords or
section structure are changed. Reject explicit tempo constraints or BPM
text, multiple tempo headers, other hard/soft flags or excessive adjustment.
The preview does not save or render the candidate, and does not prove the
native engine will follow the change. Artistic review and a separate
immutable recovery implementation are still required. Do not edit existing
receipts or use the parser-only continuation on this case.


## Explicit duration-only continuation

PR #135's live read-only preview correctly stopped on Composer-authored BPM
text. The follow-up can propose a bounded adjustment for simple integer BPM
descriptions, keeping source notes, lyrics, chords, meter and sections and
rewriting only the tempo header and consistent numeric BPM descriptions in
the separate child brief/intent. Original request tempo mentions, typed
constraints, ambiguous ranges and conflicting descriptions remain blocked.
Preview with `music.cmd --review-plan JOB --fit-duration`. A candidate
requiring artistic review is not a failure or authorization. If the operator
accepts the exact printed candidate BPM, use
`music.cmd --continue-plan JOB --approve-tempo BPM --confirm-run` (replace BPM
with the integer). Only plain structured autonomous jobs are currently
supported. No new Composer, Lyricist, Reviewer or composition plan call.
Budget: one song, one ASR, two CPU excerpts and one Director. Original plan
and journals are copied unchanged into the existing fixed continuation-1;
the revised score and decision have distinct receipts. Native MIDI and
configuration checks remain mandatory. Same command resumes the same
child; never rerun the parent. If Director alone is unresolved, use the
existing child Director retry without the tempo flag. No automatic
acceptance, automatic fit or unapproved synthesis. Offline CI and live
native compatibility must be verified separately.


## Explicit retained audio identity recovery

Keep the original journal and `acoustic.json` if a completed duration or
instrumental intro continuation stops at acoustic identity. A change after
import can affect the hash. The hash comparison measures file identity.

Before any ASR attempt, approve the current full SHA-256 from the existing
acoustic evidence and add `--approve-audio-sha SHA256` to the original
confirmed continuation command. Include the original `--approve-tempo BPM`
or `--approve-intro` flag. The launcher matches the current file against the
approved hash and checks the completed job, song, submission acknowledgment,
saved score and lyrics. An immutable sidecar binds the two hashes. The
journal is retained as evidence and a second change stops recovery. The
recovered report requires technical review. Remaining QA runs on the existing
take.


Live checkpoint 2026-11-28: the approved 77 BPM continuation and subsequent
explicit audio-identity recovery completed on the operator's Windows host.
One retained song, one explicit ASR, two CPU excerpts and one Director,
review_required, exit 0. No replay of completed creative or synthesis work.
Use the completed-source commands (ending audit, finishing, feedback) next;
no production resume is necessary. Human listening, headroom and original
waveform equivalence remain unverified. No automatic acceptance.


Live checkpoint 2026-11-28: a Windows instrumental intro continuation also
completed explicit audio identity recovery with exit 0 and `review_required`.
One rendered take measures 182.198667 seconds against its 190-second cap.
The original plan and creative stages were reused. Audible lyric delivery,
vocal layering and the ending remain open for human review.

### Lyric language default and quality

New jobs default to English, even when the idea is written in Indonesian.
Select Indonesian explicitly with `--language id`. Existing jobs always
retain their saved language unless a conflicting override is rejected.
Operator feedback on the completed Indonesian take rejected its lyrics on
artistic grounds; pipeline completion and ASR agreement do not establish
lyric quality. English-first craft evaluation remains required.
