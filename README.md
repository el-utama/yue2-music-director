# YuE2 Music Director

**Hardware portability:** Run `music.cmd --advisor` for read-only [Hardware Advisor](docs/HARDWARE_ADVISOR.md) observations and stock configuration guidance. Actual synthesis fit and alternate production profiles require separate validation. Offline indexes and existing-audio export have their own prerequisites.

Local-first Python toolkit for **YuE2-Studio timoncool v5.0.0**, developing a generation-first, native YuE2 music director for original songs, artistic guidance and evidence-based evaluation. Existing ABC, MIDI, lyric and audio experiment utilities remain available. **Development build: experimental alpha; package version 0.7.0a8.post3. Identify unreleased builds by Git commit, not the unchanged package version.**

> The repository is public. Never commit private audio, unpublished lyrics, local job journals, model weights or credentials.

## Start here

- [Fresh Windows PC / first-run guide](docs/FRESH_INSTALL.md): install from zero, connect Studio, choose export-only or autonomous production, configure provider and recover safely.

- [Song form and duration](docs/OPERATOR_GUIDE.md#song-form-and-duration) for the 3-minute default, flexible structure and ending review.
- [Operator guide](docs/OPERATOR_GUIDE.md): new/existing checkout, readiness, short commands, safe recovery, private bridge and release workflow.
- [Offline knowledge workflow](docs/OFFLINE_KNOWLEDGE_WORKFLOW.md): local databases, styles and current inventory.
- [Development and validation](DEVELOPMENT.md): agent onboarding, tests and evidence requirements.

## Project memory and acceptance register

Read [PROJECT_MEMORY.md](PROJECT_MEMORY.md) before resuming development. It tracks outstanding user requirements, verified implementation and actual data counts, live evidence and limitations. Update it alongside substantive changes; P0 alpha is not full product readiness.

## Active product roadmap

**Current milestone: creative-quality improvements after live draft Exporter sample acceptance.** Single, EP, manual/native Album and native Playlist packaging passed across the targeted Windows runs; playback/phonetic review and final release approval remain separate. Fresh-host onboarding is documented but not yet independently live-tested. The hosted Composer/Lyricist/reviewer, native plan and synthesis, ASR, neutral MOSS and advisory Director pipeline has completed live; a recovered score-first take received favorable human feedback. Cover prompt and original single-song export also completed live. Historical-source hardening, [human feedback](docs/HUMAN_FEEDBACK.md), and [non-destructive audio finishing](docs/AUDIO_FINISHING.md) extend the retained workflow. Gain-only finishing passed the authorized retained-reference Windows technical check; this is not a mastering or release-quality claim. See the [active roadmap](docs/AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md), [autonomous CLI](docs/AUTONOMOUS_CLI.md) and [repository agent instructions](AGENTS.md).

## Native-first development policy

Music Director is an evidence-driven decision and orchestration layer for YuE2 Studio, not a replacement generator, trainer, DAW or Studio UI. The [generation-first architecture and roadmap](docs/MUSIC_DIRECTOR_ARCHITECTURE.md) governs native execution and evidence; the active product roadmap above governs next milestones; the earlier native-first audit remains the capability and safety reference.

- [Studio capability knowledge](docs/knowledge/STUDIO_CAPABILITIES.md): native workflows, requirements, side effects, limits and reuse decisions.
- [Current native audit checkpoint](docs/NATIVE_AUDIT_CHECKPOINT.md): verified PRs, test evidence, remaining artistic work and no-repeat rules.
- [Restricted audit bridge recovery](docs/RESTRICTED_AUDIT_BRIDGE.md): existing private Mac-to-Studio audit connection, scope and restart procedure.
- [Native control contract audit](docs/knowledge/NATIVE_CONTROL_CONTRACT.md): UI-to-engine score/MIDI control trace, velocity loss, generation routes and remaining review scope.
- [MCP tool index](docs/knowledge/MCP_TOOL_INDEX.md): 339 static definitions at the audited upstream revision; not live availability.
- [Community and official evaluation research](docs/knowledge/COMMUNITY_AND_EVALUATION.md): existing agent skill, model/LoRA prior art, evaluator protocols and license gates.
- [Development audit and revised roadmap](docs/knowledge/DEVELOPMENT_AUDIT.md): overlap analysis, priorities and evidence gates.

Do not add a feature until native and reusable alternatives have been checked. Do not install or train models simply to test a capability. Existing research modules remain available but do not imply production-ready autonomous correction.

## Ringkasan bahasa Indonesia

YuE2 Music Director adalah agent pendamping YuE2 Studio yang bertugas memahami tujuan musik, memilih fitur native yang sesuai, mengelola eksperimen secara aman, menilai hasil berdasarkan bukti, dan menentukan apakah kandidat perlu dipertahankan atau ditolak. Agent ini bukan pengganti generator, trainer LoRA, DAW, maupun antarmuka Studio.

**Status:** alpha. Pipeline otonom score-first telah menyelesaikan satu lagu dengan evaluasi manusia yang baik; lagu awal yang terpotong tetap menjadi pembanding negatif. Cover prompt dan export asli satu lagu telah berjalan. Feedback berbasis hash dan finishing gain-only merupakan implementasi lokal terpisah; finishing gain-only telah lulus validasi teknis pada lagu referensi operator. Tidak ada klaim naturalness lintas lagu, koreksi fonetik otomatis atau mastering profesional. Dokumentasi teknis berbahasa Inggris merupakan sumber utama.

**Kebijakan:** utamakan fitur bawaan YuE2, skill resmi, model dan adapter komunitas yang kompatibel serta berlisensi sesuai penggunaan. Gunakan eksperimen yang sudah ada sebelum meminta pengguna menjalankan inferensi lagi. Jangan mengunduh model, melatih LoRA, mengubah pengaturan, atau menghapus hasil tanpa izin.

**Penggunaan dasar:** Python 3.10+ dan Git diperlukan. Untuk instalasi editable dan tes offline, ikuti bagian Setup. Jalankan `py -3 -m yue2_music_director.cli --help` untuk melihat perintah aktual. FFmpeg dan Studio lokal diperlukan hanya untuk operasi terkait. Jangan mengulang eksperimen yang sudah selesai; periksa laporan dan jurnal lokal terlebih dahulu. Jangan unggah audio, lirik, dataset atau konfigurasi pribadi ke repository publik.

**Rencana terkini:** baca [roadmap agent otonom](docs/AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md). Pertahankan hasil musik lama, verifikasi spesialis downstream tanpa regenerasi, dan integrasikan release manifest secara terpisah. Artist Memory lokal dan tiga indeks pengetahuan offline telah tersedia pada tahap alpha; korpus lengkap, evaluasi artistik, serta layanan/web app privat masih belum selesai. Tidak perlu mengulang demo lama.

## Artist Memory (local, opt-in)

Use `music.cmd --artist-memory ARTIST` to inspect private versioned artist preferences. An explicitly saved profile can be compiled into an existing typed creative specification without provider or Studio calls. See [Artist Memory](docs/ARTIST_MEMORY.md). Inferred observations are never automatically applied.

## Offline knowledge and style libraries

Start with the [offline knowledge workflow](docs/OFFLINE_KNOWLEDGE_WORKFLOW.md)
for setup, browsing, selected-style production, recovery and current counts.
The repository contains 1,000 original recipes, 853 candidate reference IDs
and seven historical lyric/score works, not 1,860 unique songs.
All three indexes use local SQLite/FTS5, without GPU or network.
Build only the indexes you need:

```cmd
music.cmd --styles --build
music.cmd --references --build
music.cmd --knowledge --build
```

The optional `--style-id folk-001` on a new autonomous job selects an
original recipe for Composer; it is preview-only unless confirmed.
Observed references remain local candidate metadata, and historical numeric
knowledge is opt-in through the autonomous or separate text-only workflow.
Use `--knowledge-query home` for local preview and add both `--confirm-run`
and `--confirm-knowledge-context` only for authorized production.
See [current requirements](PROJECT_MEMORY.md) for incomplete corpus,
rights and live validation.

## Readiness check (Windows)

Run `music.cmd --ready` for a read-only preflight before new production. It verifies local configuration and the existing native reference gate without spending a provider completion or running music inference. See [readiness check](docs/AUTONOMOUS_CLI.md#read-only-readiness-check) for limits and optional MOSS file check.

## Setup

For a new PC, follow the [first-run guide](docs/FRESH_INSTALL.md) instead of reproducing the historical reference host. Native export does not require hosted provider setup or a generation-ready model.

Requires Python 3.10+; no mandatory third-party Python runtime dependencies. Audio commands require installed FFmpeg/ffprobe, Studio commands require local Studio, and optional MIDI render QA requires FluidSynth and a SoundFont. Optional alignment discovery does not install a backend.

```powershell
git clone https://github.com/el-utama/yue2-music-director.git
cd yue2-music-director
py -3 -m pip install -e .
py -3 -m unittest discover -s tests -v
```

## Documentation map

- [Generation-first architecture and implementation roadmap](docs/MUSIC_DIRECTOR_ARCHITECTURE.md): authoritative next phases, routing, artistic constraints, musical review, budgets, recovery and acceptance criteria (design, not shipped).

- [Research handbook](docs/RESEARCH_HANDBOOK.md): goals, architecture, evidence, operating rules and roadmap.
- [Changelog and research milestones](CHANGELOG.md): retrospective history from the early prototypes.
- [Development](DEVELOPMENT.md): architecture and validation gates.
- [Finish existing song](docs/FINISH_EXISTING.md): integrated audio processing and ASR screening.
- [Instrument dynamics](docs/INSTRUMENT_DYNAMICS.md) and [MIDI render QA](docs/INSTRUMENT_RENDER_QA.md): separate audio and MIDI workflows.
- [Offline finishing selection](docs/FINISHING_SELECTION.md): compare completed evidence without new processing.
- [Native Process Audio integration contract](docs/NATIVE_PROCESS_AUDIO.md): source audit, transaction design and outstanding blockers.
- [Historical v0.6.1 acceptance protocol](docs/MUSICAL_ACCEPTANCE_V061.md): frozen score and original research design; superseded for routine human listening by the ASR-primary policy.

## Generation control study (experimental)

See [Generation Control Study](docs/GENERATION_CONTROL_STUDY.md). Compare default native score planning against section-aware planning with the existing private brief. The Windows launcher `generation-control.cmd` plans without inference; `generation-control.cmd --confirm-plans` permits two native planning jobs, no full-song renders. Review results before selecting any generation policy.

## Generation-first artistic runner (experimental)

See [Artistic Run](docs/ARTISTIC_RUN.md). `draft.cmd --artist-demo` plans offline; `draft.cmd --artist-demo --confirm-run` authorizes one reviewed native plan, one full song and one local recognition. Original emotional blues-soul fixture, no user assets or additional model settings. `draft.cmd --artist` uses a private brief and companion intent. The new routing and recovery policy is deterministic; live musical quality is unverified.

## Director-authored first-song study (experimental)

Run `draft.cmd --director-demo` to inspect the bundled original research composition offline, or `draft.cmd --director-demo --confirm-run` to authorize one new song and one local lyric recognition. Uses an explicit pre-reviewed score, native MIDI preflight and retained score verification; no repair or edits to the private brief. See [Study 2](docs/GENERATION_CONTROL_STUDY.md#study-2--new-song-director-authored-composition). Live synthesis and resumed recognition completed; the operator rejected the musical result. Retain the demo as a research fixture, not a recommended artistic default.

## Native song draft (experimental)

See [Native Song Draft](docs/NATIVE_DRAFT.md). A private six-field brief and one explicit authorization drive one native stock reference generation and one local recognition, with a resumable journal, technical QA and automatic TXT handoff. No optional evaluator is required. The explicit-score variant completed one live song and resumed evaluation; the revised generation-first orchestration and cross-song artistic quality are not yet validated.

## Finish a generated song (alpha 8)

Requires FFmpeg/ffprobe, existing stems from the exact source mix, reference lyrics, baseline native ASR JSON and a ready local Studio. No new song generation or stem separation. One possible additional recognition call, explicitly authorized.

```powershell
py -3 -m yue2_music_director.cli finish-existing --mix local/mix.flac --instrumental local/ins.wav --vocals local/vocals.wav --lyrics local/lyrics.txt --baseline-asr local/recognition.json --language en --out results/finish-001 --confirm-recognition
```

Set the loopback MCP endpoint first. A non-regression candidate is provisional; no claim of improved naturalness. See the finishing guide for statuses and recovery. The command has completed on one real YuE2 song. Native Naturalize preview capture, headroom continuation and recognition with a matching pending preview have also completed on one real song. Direct-pass ASR, other native effects, and general compatibility remain unverified.

## Diagnose completed finishing experiments without new inference

```powershell
py -3 -m yue2_music_director.cli director-diagnose --source local/mix.flac --lyrics local/lyrics.txt --baseline-asr local/recognition.json --language en --custom results/finish-001 --native results/native-001 --out results/diagnosis-001
```

Provide at least one completed experiment directory, and optionally a matching `--abc`. Native selection currently supports the headroom-continuation record shape. This reports provisional selection and diagnostic cues, not a correction loop. The integrated real-song diagnosis has passed on Windows with cached AudioBox evidence; native timing inspection also passed. No extra audio or ASR.

## One-command score preparation workflow

Put your own score, lyrics and style text in a **local ignored folder** and run:

```powershell
yue2-director run local/song.abc --lyrics local/lyrics.txt --style local/style.txt --out results/run-001 --seed 42
```

This single command validates ABC, checks lyric-section order, reports approximate phrase density, generates a **separate** pitch candidate and prepares an A/B manifest. **Zero Studio calls and zero audio jobs** by default. Set `YUE2_MCP_URL` or pass `--url` and add `--midi` to also verify both scores through `score_to_midi` (still zero audio jobs). The output directory must be new and empty; existing results are never overwritten. No safe candidate means the run refuses to prepare A/B instead of inventing random edits.

To create audio later, review the manifest and use the separately confirmed `ab-submit` commands below, pointing `--out` to `results/run-001/ab`.

## Offline musical review (generation-first)

See [Musical Review](docs/MUSICAL_REVIEW.md) for the new offline `score-review` command: native fixed-grid major/minor score descriptors, chorus comparison, hard/soft/unknown review and mandatory constraint screening. It does not render or edit scores; existing historical gates are unchanged.

## Working with ABC, offline

```powershell
yue2-director audit path/to/song.abc --lyrics path/to/lyrics.txt
yue2-director humanize path/to/song.abc --lyrics path/to/lyrics.txt --out results/variant.abc --seed 42
```

The humanizer makes **conservative chord-aware pitch edits**, grouped by approximate lyric-line phrases. In **v0.6.1**, the default `--profile conservative` re-screens the same seed-based proposals as v0.6. It defers edits that shift pitch more than three semitones, or increase a neighboring melodic leap beyond five semitones; it does **not** replace deferred edits just to fill `--max-edits`. A `deferred_changes` array in the JSON report lists each rejected proposal and the reason. You may specify `--profile legacy` to reproduce the former v0.6 candidate for a controlled comparison. The number of accepted edits is score-dependent; **eight is a hypothesis for the earlier 114-bar score, not a hardcoded quota**. It protects chorus, intro, interlude, outro, and all instrumental notes, and checks meter/ties/events. The original ABC is never overwritten. It **does not** promise natural singing, syllable alignment, microtiming, vibrato, velocity or audible improvement.

### Conservative vs. legacy candidate (offline)

```powershell
# Profile changes must use NEW output paths; existing experiments are never overwritten.
yue2-director humanize local/song.abc --lyrics local/lyrics.txt --out results/v061.abc --seed 42 --profile conservative
yue2-director humanize local/song.abc --lyrics local/lyrics.txt --out results/v060_replay.abc --seed 42 --profile legacy
```

The report records `proposed_change_count`, `change_count`, and `deferred_changes`. A conservative filter is only a contour heuristic; musical quality and lyric stress are not established by contour screening; routine lyric comparison uses ASR, with optional human musical judgment. The change does not modify velocity, timing or audio-generation behavior.

## MCP: only explicit local Studio endpoint

Find the MCP URL in YuE2-Studio Settings, and set it once in each PowerShell session:

```powershell
$env:YUE2_MCP_URL = Read-Host "Enter the Studio MCP URL"
yue2-director studio-check
yue2-director midi-probe path/to/song.abc results/variant.abc --out results/midi
```

Only `localhost`, `127.0.0.1` and `[::1]` endpoints are accepted, with a configurable port/path. No audio job is started by `studio-check` or `midi-probe`.

## Offline MIDI event audit

After converting two ABC versions with `midi-probe`, compare their symbolic note events without any new Studio calls:

```powershell
yue2-director midi-audit --original results/midi/01_original.mid --candidate results/midi/02_variant.mid --out results/midi_audit.json --allowed-pitch-track 1 --enforce-pitch-only
```

The audit compares note counts, pitch, start/duration, velocity, tracks, tempo and meter. Pass `--allowed-pitch-track` as many times as needed for explicit vocal tracks; remove `--enforce-pitch-only` if intentionally auditing a rhythm variant. The tool rejects malformed MIDI, does **not** prove audio quality, and does not call YuE2.

## A/B audio experiment

This operation **is not a dry run after you call `ab-submit`**. Each submit can launch a GPU-intensive Studio job. Make sure the Studio is idle and no active job needs to be preserved before confirming.

```powershell
yue2-director ab-prepare --original results/original.abc --candidate results/variant.abc --style local/style.txt --lyrics local/lyrics.txt --out results/ab-001 --seed 42
yue2-director ab-submit --arm A --out results/ab-001 --confirm-idle
yue2-director ab-status --arm A --out results/ab-001
# Only after A is completed and confirmed in Studio:
yue2-director ab-recover --arm A --out results/ab-001 --confirm-complete
yue2-director ab-submit --arm B --out results/ab-001 --confirm-idle --confirm-a-complete
yue2-director ab-status --arm B --out results/ab-001
```

The output directory must be new and empty. Both arms have identical requests except ABC; source hashes are checked on submit. A journal is created **before** each submit attempt, preventing duplicates on timeout/reconnect. If submit reports unknown status, inspect Studio and use `ab-recover` only when you personally verified completion. Never delete journals or blindly repeat a song submission. A/B works for new experiments; existing v0.5.x journals are **not automatically migrated**.

## Safety and current limitations

- The ABC parser supports the tested YuE2 notation subset, not full ABC notation. Unsupported constructs are rejected.
- Section matching does not verify syllable placement. The Bridge reuse from the earlier demo was **not** prosody-verified.
- Identical seed does not guarantee identical audio realization, so A/B differences are not isolated solely to pitch edits.
- MIDI conversion verifies Studio compatibility, not musical quality.
- GitHub Actions run offline tests and actual FFmpeg synthetic-audio tests on Linux; they do **not** contact your local Studio, run inference, or prove audible improvement.
- The repository has no access to your machine's loopback MCP address from GitHub Actions or this chat.

See [DEVELOPMENT.md](DEVELOPMENT.md) for quality gates and architecture.

See [offline director diagnosis](docs/DIRECTOR_DIAGNOSIS.md) for the combined evidence-selection and diagnosis workflow.

See [temporal evidence](docs/TEMPORAL_EVIDENCE.md) for read-only inspection of existing karaoke anchors and alignment limitations.

See [optional singing alignment backend research](docs/ALIGNMENT_BACKEND.md) for the discovery-only command and model validation gates.

The optional `alignment-benchmark` command evaluates existing HTK phoneme labels against independent reference annotations without inference; see [alignment research and benchmark](docs/ALIGNMENT_BACKEND.md).

Use `alignment-reference` to prepare a short excerpt from independently annotated PCM WAV for the offline benchmark. See [reference data and limits](docs/ALIGNMENT_BACKEND.md); no dataset or model is downloaded automatically.

See [native LoRA training and MMS alignment audit](docs/NATIVE_LORA_TRAINING.md) for the separate training research track and revised native-first alignment priority. No training job is implemented or authorized by this documentation.

See [local Studio configuration and compatibility](docs/LOCAL_STUDIO_CONFIGURATION.md) for the read-only `studio-profile` command. Original YuE2 weights are not mandatory; keep a compatible existing fine-tune and record effective settings.

**Panduan konfigurasi lokal:** jangan mengganti model, VAE, LoRA atau pengaturan engine hanya untuk menyesuaikan agent. Gunakan inventaris read-only `studio-profile` sesuai [panduan konfigurasi](docs/LOCAL_STUDIO_CONFIGURATION.md), simpan hasil secara lokal, dan jangan unggah laporan mentah ke repository publik. Inventaris belum merupakan sertifikasi kompatibilitas.

See [public LoRA research](docs/knowledge/LORA_RESEARCH.md) and the [39-entry native catalog index](docs/knowledge/LORA_CATALOG_INDEX.md). Stock YuE2-trained LoRA is not automatically compatible with RS-TW/FW; retain the selected model and require verified adapter provenance before activation.

**Kompatibilitas LoRA:** model Ruach TW/FW bukan bobot YuE2 original. Jangan langsung menumpuk LoRA yang dilatih pada model original; periksa model dasar, decoder, companion, dan lisensi. Lihat riset di atas sebelum mengunduh atau melatih adapter baru.

For the 8 GB CUDA tier, the recommended development reference is stock YuE2 Balanced Q6_K with stock VAE, no optional LoRA, and explicit companion off. See [configuration guide](docs/LOCAL_STUDIO_CONFIGURATION.md). This is a controlled reference, not a quality ranking. Native training's documented minimum is 11 GB VRAM.

**Baseline pengembangan 8 GB:** YuE2 original Balanced Q6_K, VAE original, LoRA tambahan nonaktif dan companion off. Fine-tune dan LoRA hanyalah pilihan untuk kebutuhan spesifik, bukan kewajiban. Jangan menghapus file model atau menjalankan training untuk menyiapkan baseline.

Optional independent audio evaluation: see [Quality Evaluation](docs/QUALITY_EVALUATION.md) for the official AudioBox model integration, local checkpoint requirement and research-only alternatives. No required new dependencies or automatic model downloads.

Current draft export presets: production, distribution and video. Native
song, album and playlist draft sources preserve original audio bytes. See
[Release Export](docs/RELEASE_EXPORT.md); no aggregator metadata or actual
cover required for draft exports. Live acceptance of the new routes pending.

Select an existing native song with `--song-name` or a collection with
`--collection-name`. The local `--export --check-library --confirm-run`
acceptance command uses existing recordings only; see the [export guide](docs/RELEASE_EXPORT.md#consolidated-local-acceptance).
