# Web validation — 2026-10-28

## Completed

- Strict TypeScript / Vite production build.
- Nine automated tests: numeric and calendar validation, school alias, scoring-scheme conflicts, complementary merges, award validation, exact-byte package round trip, IndexedDB transactions/stale revisions/undo, legacy/corrupt packages, and image header validation.
- Two reference PNG screenshots: 10 school records, **290/290 score fields** agree with manually transcribed expected values. Event, date and division checked. This is a sample result, not an accuracy guarantee; ranks and OCR text still require review.
- The sample two-page PDF: 22 detected rows, 17 available final totals; event/date correct for all rows and the 5AA continuation recognized. 494 score fields present and 144 absent. Available numeric fields agree with the independent desktop recognizer, not an independently transcribed PDF ground truth. One school name was misread (`Cainarillo` instead of `Camarillo`). Cropped columns and split rows are flagged; a school split across a page boundary may need manual addition.
- Browser export → isolated desktop library → desktop export → browser: 10 records and original bytes preserved. Browser recognizes the round-trip package as 10 duplicates, with no extra records.
- Save is blocked until the batch-review checkbox is checked. Saved QA records survive reload.
- School point, event bar and season bar open the corresponding detail/ranking views. The six main score totals use bold formatting; judge totals do not. Event rankings remain separated by division/scoring field.
- Dependency audit reported zero known vulnerabilities on the checked lockfile.

- Production-build JPEG and lossless WebP recognition: 10 expected rows and final totals; no captured console warnings/errors. Production CSP and local WASM/model loading exercised.

## Test-data isolation

Saved browser tests use only the development-only `?qa=1` database `scsboa-score-studio-isolated-qa`, with a visible banner. The normal library and existing Windows user data were not modified. PDF drafts and generated test fixtures are not published. Production smoke tests do not save test records.

## Limits

- Browser UI tests used the available Chromium-based in-app browser. Separate installed Chrome/Edge and physical mobile-device testing is not yet complete.
- Responsive layouts were visually checked at narrow and desktop widths; this does not establish full mobile OCR support.
- Small digits, ranks, school names, cut-off columns and split PDF tables still require human verification. Missing values are never silently replaced by zero.
- Local site storage can be cleared by the browser or user. Export `.scsboa` backups regularly; the hosted app does not provide server backups.
