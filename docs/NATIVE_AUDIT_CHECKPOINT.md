# Native audit and development checkpoint — 2026-11-27

Read with the [active roadmap](AUTONOMOUS_MUSIC_DIRECTOR_ROADMAP.md), [native control contract](knowledge/NATIVE_CONTROL_CONTRACT.md), and [local release checkpoint](LOCAL_RELEASE_CHECKPOINT.md). This is a handover for subsequent sessions, not authorization for further inference.

## Verified repository baseline

Main after PR #109: `6fb0d62d6de8fb8f938049844f843399a3c87ffc`. Exact-head PR CI [45939412931](https://github.com/el-utama/yue2-music-director/actions/runs/45939412931) passed four Windows/Linux Python 3.11/3.13 jobs; the Windows 3.13 log records 368 tests and all four new lyric schedule tests passing. Recheck current main and CI at the beginning of a new session.

| PR | Result | Evidence |
|---|---|---|
| [104](https://github.com/el-utama/yue2-music-director/pull/104) | UI-to-native source audit | Pinned Studio source, not installed binary identity |
| [105](https://github.com/el-utama/yue2-music-director/pull/105) | Live velocity and request boundary | Direct synthetic native conversion; operator-reported UI check; [CI](https://github.com/el-utama/yue2-music-director/actions/runs/45937553774) |
| [106](https://github.com/el-utama/yue2-music-director/pull/106) | Pinned engine conditioning and completion | Source audit; [CI](https://github.com/el-utama/yue2-music-director/actions/runs/45937897079) passed on retry after external apt HTTP 403 |
| [107](https://github.com/el-utama/yue2-music-director/pull/107) | Fail closed on malformed completion metadata | [CI](https://github.com/el-utama/yue2-music-director/actions/runs/45938564815), 362 Windows tests |
| [108](https://github.com/el-utama/yue2-music-director/pull/108) | Exact or native CRLF-normalized saved lyric comparison | [CI](https://github.com/el-utama/yue2-music-director/actions/runs/45938982372), 364 Windows tests |
| [109](https://github.com/el-utama/yue2-music-director/pull/109) | Optional saved lyric schedule evidence for Director | [CI](https://github.com/el-utama/yue2-music-director/actions/runs/45939412931), 368 Windows tests; no new live synthesis |

## Do not repeat completed work

The retained reference and its separate gain-only candidate are unchanged.
The favorable reference listening result, native generation, recognition,
MOSS, cover prompt, original export and technical fixed-gain check are already
recorded in the local release checkpoint. Do not regenerate or repeat them.
Do not infer package or publication approval from a technical pass or a
listening preference. Preserve the reference, exact hashes and historical
receipts. Local artifacts, private feedback and credentials stay out of Git.
No Windows pull is required solely for documentation; a future executable
test should use verified current main, not a stale checkout.

The installed music-server 5.0.0 was accessed through the restricted bridge.
The successful velocity fixture used identical synthetic melodies with
different note velocities; both ABC outputs and re-exported note velocities
were identical. Operator confirmed that edited velocity did not persist in
score-mode UI. Do not repeat that fixture. It does not establish the behavior
of all standalone MIDI editors or acoustic generation routes.

## Next work, ordered by unresolved artistic value

1. Compare installed writing guides and native notation/section contracts
   with Composer/Lyricist and reviewer policies. Review lyric density,
   phrasing, verse/chorus contrast and style descriptors. Existing prompt
   identities must remain immutable; any changed guidance needs an explicit
   versioned path. Do not invent phoneme or singer routing controls.
2. Audit the remaining melody/harmony/arrangement capabilities and native
   parser/tokenizer constraints; distinguish symbolic score evidence from
   acoustic instrumentation. The existing schedule evidence records
   coverage, not actual vocal onset or syllable alignment.
3. Trace semantic replay, continuation, cover, backing and AR/NAR adapters
   through real handlers. Never rerender the reference merely to test a
   parameter. Design an explicit bounded experiment only for an unresolved
   material question after source and retained evidence are exhausted.
4. Review installed engine identity and effective settings through a
   separately authorized, narrowly scoped read-only tool if necessary.
   The current bridge cannot read arbitrary configuration or library data.
5. Further product work remains: persistent Artist Memory, multi-track
   orchestration, supervised workers, approved-variant release delivery
   verification and private authenticated service. None is claimed complete.

The current audit is not exhaustive. Source-pinned engine behavior is not
proof of the installed executable build. New executable changes require
exact-head Windows/Linux CI; actual acoustic claims need suitable listening
evidence. For remote audit setup/recovery see [Restricted audit bridge](RESTRICTED_AUDIT_BRIDGE.md).
