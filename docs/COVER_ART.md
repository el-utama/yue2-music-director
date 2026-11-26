# Cover Art Specialist — optional release-art module

The module is independent of music production. It reads completed retained autonomous song results (including continuation-1), checks linked brief/report/listening hashes, and uses title, concept, emotional arc and musical style. It does not require artistic acceptance, so its output is explicitly a draft. It sends only this metadata plus explicit release title/artist/art direction to the already configured text provider; no raw audio, full lyrics, account credentials or local paths. The Composer model is reused for a separate specialist prompt/schema without changing four-role provider identities or existing music receipts.

Single (plan by default, add explicit confirmation for one text call):

```powershell
.\music.cmd --cover song-3c1384bea53a --confirm-run
```

Album (ordered jobs, explicit album title, optional artist and direction):

```powershell
.\music.cmd --cover album-01 --song song-one --song song-two --title "Album title" --artist "Artist name" --confirm-run
```

For a separate design of the same song use a distinct release ID and --song JOB. An existing identical release reuses its specialist receipt, no repeat text call. An unresolved attempt fails closed; no blind retry. Output in results/artwork/RELEASE/flow-prompt.txt and cover-brief.json (concept, typography, rationale and exact release credits). Paste prompt into Google Flow image mode, select 1:1 and preferred available model. Typography is a separate editable design step; generated imagery is text-free by design. 3000×3000 is a target delivery dimension, not a guarantee from Flow. Verify actual image, rights, dimensions and distributor rules before release. No image files created by the module, no publishing.

As of 2026-11-26 official Flow help documents image generation and aspect ratio: https://support.google.com/flow/answer/16729550. No official public Flow MCP API verified. Third-party browser automation wrappers exist; not approved, installed, or relied on. Optional future adapters may use a supported image API or an audited local Flow MCP with explicit account/credit authorization, bounded jobs, image validation and immutable receipts. No scraping tokens, account sessions, CAPTCHA bypass or automatic subscription usage. A visual provider failure must never block music completion. No live provider or Flow tests performed.
