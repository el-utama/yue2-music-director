# First run on a fresh Windows PC

Hardware-dependent configuration advice is planned in [Hardware Advisor](HARDWARE_ADVISOR.md), not yet available. Until implementation and target validation, the existing strict production gate remains in effect; no requirement to use that profile for export/offline.

This is the current installation runbook for a PC with a newly installed
YuE2 Studio and **no previous Music Director run, agent, provider settings,
models, library songs, local indexes, jobs, or receipts assumed**. The
Director is a local Python CLI, not a new Studio installer, background
service or replacement for Studio. A chat-based coding agent is optional.
The Windows production route targets the audited YuE2 Studio 5.0.0
contracts; verify the actual installed build and schemas. Export packaging
passed live on the original operator host; a fresh Windows host has not yet
been independently live-validated. This guide does not authorize any
generation, downloads, provider charges, or settings changes by itself.

## 1. Select what you want to use

| Goal | Git/Python | FFmpeg | Running local Studio | Music/Whisper/MOSS assets | Hosted text provider |
| --- | --- | --- | --- | --- | --- |
| Local help, previews, style and knowledge indexes | Yes | No | No | No | No |
| Read/list native songs and collections | Yes | No | Yes | No additional assets | No |
| Export existing native songs/collections | Yes | ffprobe | Yes, source media accessible | No new assets | No |
| Full autonomous new song | Yes | FFmpeg + ffprobe | Yes | Stock production reference, Whisper, managed MOSS | Yes |
| Finish or assemble retained Director jobs | Yes | Operation-specific | Operation-specific | No new synthesis | No new provider for packaging |

An empty Studio library is normal on a new machine. Native export cannot
create music for an empty library; import an authorized existing recording
using Studio if desired, or explicitly authorize a new song. Offline
indexes are bundled-data derivatives, not the Studio library. No requirement
to build them, install LoRAs, train, or enable a remote bridge before export
or ordinary new-song creation.

## 2. Install prerequisites and clone

Install Git for Windows, Python 3.11 (recommended CI baseline; package
declares 3.10+, 3.13 also has historical CI coverage), and FFmpeg including
ffprobe from their official distribution sources:
[Git](https://git-scm.com/download/win), [Python](https://www.python.org/downloads/windows/),
[FFmpeg](https://ffmpeg.org/download.html). Enable the Windows Python
launcher (py), make Git and both FFmpeg tools available on PATH, and reopen
PowerShell after installation. For CUDA production, install the supported
NVIDIA driver using the hardware vendor and Studio's own instructions.
Do not assume the old PC's GPU or driver. Confirm disk space for selected
Studio models, private audio, and export copies before downloads.

Run in PowerShell:

~~~powershell
git --version
py -3 --version
ffmpeg -version
ffprobe -version
~~~

Use a short, writable local path to reduce Windows path-length problems.
Avoid running as Administrator, syncing mutable journals via cloud drives,
or putting the checkout inside Studio's managed media folder. From your
chosen parent directory:

~~~powershell
git clone https://github.com/el-utama/yue2-music-director.git
cd yue2-music-director
git rev-parse HEAD
py -3 -m pip install -e .
.\music.cmd --help
~~~

The launcher uses py -3 and sets PYTHONPATH to its own src directory.
With multiple Python versions, verify py -3 points to the interpreter you
intend to use (py -0p lists installations); installing into another Python
or a virtual environment does not change the launcher's interpreter.
No third-party Python runtime dependencies are mandatory; editable install
may need setuptools/build dependency access. If pip fails, fix Python or
package access rather than install arbitrary scripts. The launcher can use
the checked-out src directly; editable install is useful for direct module
commands. Optional developer tests (not required for ordinary users):

~~~powershell
py -3 -m unittest discover -s tests -v
~~~

The tests are offline mocks and synthetic local audio, not live Studio
generation. A first run may create results/; absent local/ and prior job
directories are normal. Never copy example IDs from historical checkpoints.

## 3. Connect to the newly installed Studio

Start Studio using its normal launcher. In its Agent (MCP) setting, enable
the local MCP service if necessary and copy the actual URL displayed by
Studio. Keep it loopback-only; do not enable LAN/public access. The
Music Director launcher defaults to http://127.0.0.1:8791/mcp if the
environment variable is absent, but ports can differ. In this PowerShell
session set the actual URL:

~~~powershell
$env:YUE2_MCP_URL = Read-Host "Paste local Studio MCP URL"
.\music.cmd --export --list-songs
.\music.cmd --export --list-collections
~~~

Those commands perform read-only discovery and may legitimately return [].
They do not require an API key, selected music model, Whisper, MOSS, or
previous agent results. They establish basic library access, not production
readiness. The variable lasts for this terminal session; set it again in a
new terminal if the default does not match. Native endpoints must satisfy
the local client restrictions; the library read adapter requires /mcp.
Do not substitute a network-access key, hosted LLM URL, or remote tunnel.
No private Mac audit bridge is required on this PC.

Optional detailed inventory, only if investigating configuration or
compatibility (private output, no inference):

~~~powershell
$profile = "results/studio-profile-$(Get-Date -Format yyyyMMdd-HHmmss).json"
py -3 -m yue2_music_director.cli studio-profile --url "$env:YUE2_MCP_URL" --out "$profile"
~~~

See [Studio configuration](LOCAL_STUDIO_CONFIGURATION.md). Use actual
inventory rather than assuming the historical tool count, models or paths.

## 4. Export existing music without configuring an AI provider

If you only want the Exporter, this is enough after the prerequisites,
local connection and a readable song/collection. No setup of a text provider
or production readiness gate is needed.

Use an actual title or collection name from the lists. Use a fresh short
release ID consisting of letters, digits, underscores or hyphens (up to 64,
not a reserved Windows name). Example names below are placeholders:

~~~powershell
.\music.cmd --export first-song --song-name "Actual Song Title" --preset video
.\music.cmd --export first-song --song-name "Actual Song Title" --preset video --confirm-run
.\music.cmd --export first-album --collection-name "Actual Album Name" --preset production --confirm-run
~~~

The collection-name selector also works for native playlists. Duplicate
names require exact IDs from the list. Use a new ID if source, ordering or
preset changes; use an explicit new snapshot for corrected timing only.
The default is a preview. Output under results/exports contains original
audio bytes, original lyric text and clean lyrics when available, optional
existing timing assets, release.json and M3U8 for playlists. Distribution
omits timed assets; production includes valid native LRC/SRT; video adds
line-only LRC. Missing or invalid lyric timing can cause exit 2 with a
partial package, not a failed audio copy. Invalid word anchors may fall
back to valid native line anchors, with the original archived separately.
An instrumental without sung lyrics requires no subtitle. Metadata and
actual artwork are not mandatory for a draft. No automatic transcoding,
karaoke inference, audio mutation or publication. See [Release Export](RELEASE_EXPORT.md).

For a new host with a suitable existing library, optional sample acceptance
can preview with `.\music.cmd --export --check-library` and write isolated
sample exports with `.\music.cmd --export --check-library --confirm-run`.
A missing eligible native collection or unavailable timing may leave
acceptance incomplete; do not create fake data or rerun unrelated successful
cases. Album-only/playlist-only checks are documented in the export guide.
The original operator's live results are regression evidence, not proof
this new PC's data is valid.

## 5. Prepare full autonomous production only if wanted

Skip this section for offline work or exporting. A newly installed Studio
may have no installed models or active engine. Use Studio's own UI and
official model/runtime guidance to download only the required assets, after
the user approves storage, bandwidth and licensing. Never silently switch
an existing configuration. The current production gate is narrower than
Studio's complete hardware/model support:

- Stock YuE2-3B Balanced Q6_K, backbone-q6 and vae-f32, no own fine-tune,
  optional adapters or companion in the request; engine ready and matching
  selected model. CUDA backend, configured/effective Q8 KV cache, effective
  flash attention and consistent engine status; no custom binary/extra flags.
- Local Whisper recognition enabled and ready, CrisperWhisper Turbo installed,
  no recognition download in progress. The required native tools and schemas
  must be advertised. Studio must be idle; do not cancel another job.
- Managed Windows MOSS captioner and model files for the post-synthesis
  Reviewer path. Use Studio to install the appropriate captioner assets;
  no arbitrary executable or manual third-party package replacement.
  The exact managed layout is checked by the Director. On a new PC find the
  actual Studio-managed media folder through Studio/storage information;
  do not use a path copied from the previous host or scan the whole disk.

See [Local Studio configuration](LOCAL_STUDIO_CONFIGURATION.md) and the
[autonomous CLI](AUTONOMOUS_CLI.md). A CPU-only/AMD system or another model
profile may run Studio or Exporter but is not established as supported by
the current full autonomous reference gate. Do not bypass that gate or
promise that every GPU can synthesize a song.

Configure the text provider in the local Windows terminal:

~~~powershell
.\music.cmd --setup
~~~

Choose NVIDIA NIM, OpenRouter with an explicit :free model, or your own
HTTPS OpenAI-compatible chat/completions endpoint. Use the actual model ID
and account credential from the chosen provider. NVIDIA's offered model is
a preset, not guaranteed access. Input the API key only into the hidden
local prompt. Setup writes DPAPI current-user-protected local/llm-provider.json
and does not contact the provider. Do not copy encrypted settings from another
Windows account/PC; configure locally. Explicit MUSIC_LLM_* environment
settings override the saved file; incomplete settings fail. Never paste
keys into chat, log or Git. No automatic paid fallback. If authorized,
test provider access separately (one synthetic completion per distinct
model, provider charges/quota may apply):

~~~powershell
.\music.cmd --check-provider
~~~

Check full production readiness:

~~~powershell
.\music.cmd --ready
$media = Read-Host "Actual Studio managed media folder"
.\music.cmd --ready --media-dir "$media"
~~~

The second command is optional if the folder is unknown, but MOSS then
remains not_checked. Exit 0 means only performed checks passed; no actual
GPU/synthesis, provider access, captioner execution or artistic quality
verified. Exit 2 means a blocker; resolve the named check before confirming
production. Provider configuration alone does not authenticate the provider.
Do not automatically download or mutate Studio based on readiness.

## 6. First new song and first retained job

Preview an original idea in English by default (regardless of prompt
language), 195-second default cap. Explicit --language id opts into
Indonesian lyrics, whose prior artistic quality was rejected. Other
language/duration choices follow actual CLI help. Use a new, unused job ID:

~~~powershell
.\music.cmd --job first-song-job --request "An intimate acoustic song about letting go"
~~~

Preview sends no provider or Studio calls. Only after actual new-song
authorization and readiness, repeat the same request with confirmation:

~~~powershell
.\music.cmd --job first-song-job --request "An intimate acoustic song about letting go" --confirm-run
~~~

Confirmed production can send the brief, lyrics and selected text evidence
to the configured hosted provider. Budget: up to four text completions, one
native score plan, one native song, one explicit ASR, two CPU listening
excerpts; Studio may also run its configured native karaoke. No automatic
revision, mastering, or release approval. The current creative system is
alpha; technically complete music is not necessarily artistically acceptable.
Read the plan, result and listen before accepting the output.

The launcher records a local transcript under results/music-output.txt;
private retained state is under results/autonomous/first-song-job. If
interrupted, inspect with `.\music.cmd --job first-song-job`, then use
the same ID with `--confirm-run` only after resolving the blocker and
following the recovery guide. Never create a second job to bypass an
uncertain submission. Once a completed retained result exists, the
retained-job Exporter, cover prompt and finishing commands can use that job.
Existing Studio-only tracks use native source selection instead, never
fabricated Director receipts.

## 7. Optional indexes, private data and recovery

Build only the indexes you want; these use local bundled data, SQLite/FTS5,
not GPU or online generation:

~~~powershell
.\music.cmd --styles --build
.\music.cmd --references --build
.\music.cmd --knowledge --build
~~~

See [Offline knowledge workflow](OFFLINE_KNOWLEDGE_WORKFLOW.md) for counts,
query syntax and consent. No automatic profile inference, corpus download,
or historical raw-lyric transfer. Artist Memory is opt-in and may be empty.

| Symptom | Action |
| --- | --- |
| py/git/ffprobe not recognized | Install the appropriate prerequisite; reopen terminal and check version/PATH. |
| Python module missing | Verify checkout and py -3 interpreter; editable install in the correct interpreter. |
| Studio refused connection / wrong route | Check Studio running, local Agent/MCP setting and actual URL; re-set environment in this shell. |
| Library lists empty | Normal for fresh host. Export needs a real existing song; do not generate just to check setup. |
| Audio missing or unsupported | Check the reported track ID, Studio playback/storage; use authorized native conversion if needed. No silent skipping. |
| Missing timing or fallback | Keep original audio; read manifest; correct native timing only if explicitly requested, then new snapshot. |
| Readiness blocked | Inspect named check, stock reference settings, Whisper, actual GPU/runtime and MOSS files. |
| Provider 401/403/429 or JSON mismatch | Check actual selected endpoint/model and account authorization; no automatic fallback/retry. |
| OOM / busy Studio / interrupted job | Preserve receipts, inspect actual native state and follow same-job recovery; never delete locks blindly. |
| Export path too long / disk full | Shorten checkout/release ID, free space safely; preserve prior packages. |
| Private bridge absent | Not needed for ordinary local operation. Optional restricted audit only. |

More detail: [Operator guide](OPERATOR_GUIDE.md),
[provider troubleshooting](AUTONOMOUS_CLI.md#provider-authentication-troubleshooting),
[lock recovery](LOCAL_LOCK_RECOVERY.md),
[restricted audit bridge](RESTRICTED_AUDIT_BRIDGE.md).

Keep local/ and results/ private and backed up alongside any external media
they reference. The repository is public. Do not commit provider keys,
private songs/lyrics, model files, transcripts or native inventory.
Derived indexes can be rebuilt; job journals/receipts and selected source
audio cannot be fabricated. A new PC does not inherit a previous host's
evidence or provider permissions. For migration, preserve original files
privately and verify paths and hashes; do not replay historical jobs.
For updates, verify branch and clean worktree before git pull --ff-only;
do not overwrite or reset local edits.

## 8. Handover to a new development agent

No prior chat is needed. Read [AGENTS.md](../AGENTS.md),
[PROJECT_MEMORY.md](../PROJECT_MEMORY.md), the
[active roadmap](AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md), and this runbook.
Determine whether the task is offline, native export, or autonomous
production; inspect only necessary local evidence. Detect absent files as
normal fresh state, not failures of historical jobs. No assumptions about
credentials, hardware, models, drive letters, remote bridge or earlier
recordings. Explain what the current host actually passed, what is untested,
and what user authorization is needed. Do not run live inference or alter
settings solely to onboard an AI agent. See [Development](../DEVELOPMENT.md).
