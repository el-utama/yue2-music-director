# Alpha 5 — human-led fidelity audit

Use a frozen ABC, its intended sectioned lyrics and an existing native-asr-review-v1 report for the same reference. The operator must establish identity of the score/audio/report; matching reference text alone does not prove provenance.

Observations JSON:

```json
{"lines":[{"section":"verse#1","line_index":1,"status":"issue_confirmed"}],"transitions":[]}
```

A transition row has after and before objects, each with section and line_index, identifying consecutive reference lines, and status. Allowed statuses: issue_confirmed, no_issue_heard, uncertain. Unlisted lines are not_reviewed.

`fidelity-audit SCORE --lyrics LYRICS --asr-review REVIEW --observations OBS --out NEW_REPORT`

The report joins phrase-level observations, ASR edit counts, approximate equal-partition bar ranges, note counts and rough English syllable estimates. It blocks acceptance when a human reports an issue; absence of issues is not acceptance. Observations are not a verbatim transcript, and targeted review is selection-biased. ASR arm names preserve the input report's labels; for a full mix versus vocal stem report they are not original versus candidate. No audio inference, rendering, score changes, or automatic correction. Reports contain private lyrics and stay local.

The B experiment shows persistent errors after source separation and human-confirmed issues at targeted locations. Do not infer that pitch edits caused the errors, or assume score density causes a particular pronunciation issue. Inspect score allocation before proposing a controlled intervention. Full mix remains the default ASR input, stem optional. Process Audio is a separate post-generation intervention, not a lyric correction.
