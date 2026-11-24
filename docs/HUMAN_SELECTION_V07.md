# Alpha 7 — ASR-primary lyric screening

Run `human-select --asr-review REVIEW --preferences HUMAN --out NEW_REPORT` offline.

Human JSON has distinct baseline/candidate labels and a preferences array with unique criterion, preference (baseline, candidate, tie, uncertain, not_reviewed), and optional line {section, line_index}. Required criteria: overall_lyrics and overall_music (uncertain is valid). ASR report A maps to baseline and B to candidate; the operator verifies identity and comparable recognition settings.

Default lyric_evidence_policy is asr_primary: rank lyric candidates by existing full-mix ASR edit counts against the same reference, not by casual human lyric preference. The optional human_reviewed policy is for reliable reviewed lyric evidence. Musical preference remains separate. If the preferred lyric and musical candidates conflict, report tradeoff_review_required, with no overall automatic winner. Neither preference certifies absolute fidelity, clears confirmed issues or triggers regeneration. No manual word-by-word review is required for screening.

The operator reported limited confidence in manual English lyric review. B has fewer ASR edits than C, while C is preferred musically. Preserve both findings; do not promote C automatically. A has the lowest observed full-mix ASR disagreement among the three, but is not certified. A second locally available recognizer, if supported, is a possible independent cross-check; no install or external transfer by this module. Reports remain private.
