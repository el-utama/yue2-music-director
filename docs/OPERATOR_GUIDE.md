# Operator guide — start here

For the Windows machine running YuE2 Studio. Mac and other devices can
read documentation and develop offline, but the installed Studio production
host is Windows. This is an experimental alpha. The private audit bridge
is not a remote production service. Current evidence and open requirements:
[PROJECT_MEMORY.md](../PROJECT_MEMORY.md). The live retained reference is
already complete; do not repeat it merely to check installation.

## 1. Install or adopt an existing checkout

Requirements: Python 3.10+ (CI 3.11/3.13), Git, FFmpeg/ffprobe for audio
operations, an installed compatible YuE2 Studio with local MCP for native
operations. See [Studio configuration](LOCAL_STUDIO_CONFIGURATION.md) and
[README setup](../README.md#setup). Do not install or switch models automatically.
For the offline database only, Studio, FFmpeg, hosted provider and GPU are not
required. Use Command Prompt in the repository directory.

For a new checkout only:
```cmd
git clone https://github.com/el-utama/yue2-music-director.git
cd yue2-music-director
py -3 --version
py -3 -m pip install -e .
```

For an existing checkout, inspect first:
```cmd
git status --short
git rev-parse HEAD
py -3 --version
music.cmd --help
```

Do not clone over an existing directory or replace local settings. If the
working tree is clean and an update is wanted, `git pull --ff-only` updates
the existing checked-out branch (verify it is main first). If there are local
changes, a non-main branch, divergence, or an interrupted update, stop and
review; never reset, clean, force-pull or delete local data. Keep private
backups of `local/` and `results/`; preserve all journals and selected audio.
The launcher sets PYTHONPATH to the checkout; the editable install is useful
for direct Python module commands and tests. For development only,
`py -3 -m unittest discover -s tests -v` runs the local test suite (audio
fixtures require FFmpeg). No live generation is required.

## 2. Choose the workflow

| Goal | Starting command (examples are placeholders) | Effect |
|---|---|---|
| Browse original style recipes | `music.cmd --styles --build` | Offline disposable index |
| Browse observed references | `music.cmd --references --build` | Offline candidate metadata, not approved tracks |
| Browse historical lyrics/score descriptors | `music.cmd --knowledge --build` | Offline historical index |
| Inspect named artist | `music.cmd --artist-memory "Artist Name"` | Read-only local profile |
| Check production readiness | `music.cmd --ready` | Read-only local/Studio preflight; no provider completion |
| Configure hosted text provider | `music.cmd --setup` | Local encrypted configuration, no network calls |
| Diagnose provider authentication | `music.cmd --check-provider` | Explicitly authorizes synthetic external text checks; quota/charges may apply |
| Preview a new song | `music.cmd --job new-song --request "A quiet goodbye"` | No provider or Studio calls |
| Inspect existing job | `music.cmd --job JOB` | Plan-only; no new generation |
| Diagnose retained ending | `music.cmd --inspect-ending JOB` | Read-only retained evidence/loopback lookup |
| Duration-only fit preview | `music.cmd --review-plan JOB --fit-duration` | Advisory local tempo candidate; no inference or repair |
| Approved duration continuation | `music.cmd --continue-plan JOB --approve-tempo BPM --confirm-run` | Exact previewed BPM, one song; original unchanged |
| Review a stopped plan | `music.cmd --review-plan JOB` | Retained local evidence; no new score |
| Inspect lock | `music.cmd --inspect-lock autonomous` | Read-only journal summary |
| Preview finishing | `music.cmd --finish JOB` | Existing source, no new song |
| Read feedback | `music.cmd --feedback JOB` | Local feedback/approval state |
| Preview cover direction | `music.cmd --cover JOB` | No image generation |
| Preview export | `music.cmd --export JOB` | Existing source only |
| Preview assembly | `music.cmd --assemble-release RELEASE` | Existing explicitly approved audio variants |
| Preview delivery | `music.cmd --release-delivery RELEASE` | Existing package state |
| Preview combined release | `music.cmd --release RELEASE` | Existing approved inputs; no publishing |

See [offline knowledge workflow](OFFLINE_KNOWLEDGE_WORKFLOW.md) for the three
indexes, actual counts, selected styles, and recovery. Each index is derived
and disposable; no reason to build all three for every song.

## 3. Produce a new original song only when requested

First `music.cmd --ready` if readiness is uncertain. This does not reserve
the host or authenticate the text provider. A blocked readiness report
requires resolving the reported issue, not blind retry. If provider setup
already works, do not redo it. For the first setup or a changed provider,
use the [provider troubleshooting guide](AUTONOMOUS_CLI.md#provider-authentication-troubleshooting).

```cmd
music.cmd --job new-song --request "A quiet goodbye" --style-id folk-001
```

Preview only, with the optional authored style. An explicitly chosen local
artist profile can supply typed requirements; see [Artist Memory](ARTIST_MEMORY.md)
and [typed creative specification](TYPED_CREATIVE_SPEC.md). These optional
features are CI-tested, not independently live-validated.

Only when actual new production is authorized, repeat the new-job command
with `--confirm-run`. The existing bounded budget is up to four text
completions, one native score plan, one native song, one explicit ASR and
two CPU excerpts. The text provider is online if configured as hosted; local
SQLite and YuE2 are not a promise of wholly offline production. Lyrics/brief
and selected authorized text evidence are sent as part of confirmed production.
No automatic observed-reference or raw historical lyric transfer. For an explicit historical numeric context preview use `--knowledge-query home`; confirmed production additionally requires `--confirm-knowledge-context`. See [Autonomous CLI](AUTONOMOUS_CLI.md#historical-knowledge-in-autonomous-production-explicit-opt-in).

The confirmed job writes private immutable stage identities under
`results/autonomous/JOB`. If interrupted, use the same job ID only, not a
new job to bypass receipts. Resume with `music.cmd --job JOB --confirm-run`
only when needed, after inspecting the blocker. Review retained evidence
before deciding whether a new job is necessary. Do not replay a successful
song or unresolved external attempt automatically.

## 4. Failures and safe recovery

| Symptom | Safe next action |
|---|---|
| Python or FFmpeg missing | Follow README setup; check installation/PATH. Do not download models to fix a missing executable. |
| Studio unavailable, not idle, or schema mismatch | Check installed Studio and local loopback MCP; use readiness, then the configuration guide. No remote-public endpoint. |
| 401/403, quota or provider JSON error | Use the provider troubleshooting guide; check exact configured provider/model and account. No automatic fallback, no key in logs/chat. |
| Unresolved text attempt | Consult the original receipt and [Autonomous CLI](AUTONOMOUS_CLI.md); one explicit `--retry-text ROLE` only for a matching unresolved stage. |
| Plan stopped before synthesis | Use `--review-plan JOB`; `--continue-plan JOB --confirm-run` is only for the documented formerly parser-blocked retained plan; duration-only stops require the separately documented exact tempo approval. |
| Native, ASR or listening interrupted | Preserve the original job and follow same-job recovery. A saved Studio acknowledgment with a valid plan or song ID lets the agent continue the known job. If the acknowledgment is missing or ambiguous, inspect Studio before proceeding. |
| Stale lock or concurrent writer | Inspect the exact lock; use [lock recovery](LOCAL_LOCK_RECOVERY.md) only for verified stale owner and matching marker hash. |
| OOM or missing model | Stop and inspect native status/configuration, preserve journals. No unapproved changes, downloads or automatic retry. |
| Missing/stale SQLite index | Rebuild just the requested derived index; see the offline guide. |
| Mac audit connection unavailable | Follow [restricted bridge recovery](RESTRICTED_AUDIT_BRIDGE.md); do not expose Studio publicly or repeat completed audit probes. |
| Release approval or artwork missing | Stop at the relevant stage, request operator approval/input. No fabricated credits, artwork or inferred approval. |

For unresolved situations keep the exact command, exit status, commit,
stage name, and redacted error. Do not share credentials, raw unpublished
lyrics, private audio, or the full local results folder. No generic
destructive "reset everything" advice. The local CLI is not a supervised
always-on agent or an automatic repair service.

## 5. Existing song to release package

Review the retained original and optional separate fixed-gain candidate;
the operator chooses the variant. See [finishing](AUDIO_FINISHING.md),
[feedback](HUMAN_FEEDBACK.md), [cover art](COVER_ART.md) and
[export](RELEASE_EXPORT.md). Use [assembly](RELEASE_ASSEMBLY.md) and
[delivery](RELEASE_DELIVERY.md) to prepare already approved assets and actual
local artwork. Confirming preparation does not authorize publishing;
whole-package approval is a distinct explicit operator action. The original
reference and its gain-only candidate must remain unchanged. The live
technical finishing check is already complete; multi-track and final
package live acceptance remain open. See [release checkpoint](LOCAL_RELEASE_CHECKPOINT.md).

## 6. Complete primary launcher route index

All special first-argument routes below were checked against the current
`music.cmd` source. The default route is [Autonomous CLI](AUTONOMOUS_CLI.md);
it also handles `--job`, `--request`, `--style-id`, `--artist-profile`,
`--creative-spec`, `--continue-plan`, and `--retry-text`.
Read each module guide for precise confirmation semantics. `--setup` and
`--check-provider` are actions, **not help flags**; do not invoke casually.

| Route | Reference |
|---|---|
| `--references` | [OBSERVED STYLES](OBSERVED_STYLES.md) |
| `--styles` | [STYLE LIBRARY](STYLE_LIBRARY.md) |
| `--knowledge` | [KNOWLEDGE BANK](KNOWLEDGE_BANK.md) |
| `--artist-memory` | [ARTIST MEMORY](ARTIST_MEMORY.md) |
| `--ready` | [AUTONOMOUS CLI](AUTONOMOUS_CLI.md) |
| `--setup` | [AUTONOMOUS CLI](AUTONOMOUS_CLI.md) |
| `--check-provider` | [AUTONOMOUS CLI](AUTONOMOUS_CLI.md) |
| `--inspect-ending` | [ENDING AUDIT](ENDING_AUDIT.md) |
| `--review-plan` | [AUTONOMOUS CLI](AUTONOMOUS_CLI.md) |
| `--cover` | [COVER ART](COVER_ART.md) |
| `--export` | [RELEASE EXPORT](RELEASE_EXPORT.md) |
| `--feedback` | [HUMAN FEEDBACK](HUMAN_FEEDBACK.md) |
| `--inspect-lock` | [LOCAL LOCK RECOVERY](LOCAL_LOCK_RECOVERY.md) |
| `--recover-lock` | [LOCAL LOCK RECOVERY](LOCAL_LOCK_RECOVERY.md) |
| `--release` | [RELEASE DELIVERY](RELEASE_DELIVERY.md) |
| `--release-delivery` | [RELEASE DELIVERY](RELEASE_DELIVERY.md) |
| `--assemble-release` | [RELEASE ASSEMBLY](RELEASE_ASSEMBLY.md) |
| `--finish` | [AUDIO FINISHING](AUDIO_FINISHING.md) |

Historical experiment commands are separate and are not the everyday
production workflow. See [development](../DEVELOPMENT.md) and
[research handbook](RESEARCH_HANDBOOK.md) for context.


If a completed duration continuation has an acoustic hash mismatch, use the
[explicit retained audio identity recovery](AUTONOMOUS_CLI.md#explicit-retained-audio-identity-recovery)
only after the current exact hash is confirmed and approved. No new song
submission is permitted on that path.


Draft export does not require full credits, artwork or audio release approval.
Use the default production preset for FLAC, tagged and clean lyric text and
existing native timing, or `--preset distribution` for audio and lyric texts
without timing reads. See [export presets](RELEASE_EXPORT.md#production-and-distribution-presets).

Native collection discovery: `music.cmd --export --list-collections`.
Use `music.cmd --export RELEASE --native-collection ID --confirm-run` to
package an existing playlist or album of completed autonomous results.
See [native playlists and albums](RELEASE_EXPORT.md#native-playlists-and-albums).
Studio-only songs use the explicit draft source below.

For ordinary Studio library tracks, use `music.cmd --export --list-songs`
and `music.cmd --export DRAFT --native-song ID --confirm-run`. Native
collection drafts use `--native-collection ID --library-only` with export.
See [native draft sources](RELEASE_EXPORT.md#native-library-draft-sources).

For video editors use `--preset video` to include original native LRC,
plain line LRC and SRT. Correct timing in Studio and export a new immutable
snapshot with the same preset. See [video preset](RELEASE_EXPORT.md#video-preset-and-native-timing-corrections).

Use `--song-name "My Song"` or `--collection-name "My Album"` for an
unambiguous native draft selection. See [name selection](RELEASE_EXPORT.md#select-by-song-title-or-collection-name).
For consolidated native export acceptance use `music.cmd --export --check-library --confirm-run` after updating to the verified main. See [acceptance](RELEASE_EXPORT.md#consolidated-local-acceptance).

The consolidated exporter acceptance report checks actual assets/order in
addition to hashes. Long track names are shortened only when necessary for
portable Windows paths. The report is not a listening or subtitle playback
review.
