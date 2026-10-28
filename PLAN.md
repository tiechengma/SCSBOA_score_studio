# SCSBOA Score Studio — approved scope

Approved by user: 2026-10-26. Windows first, English UI; future mobile support via portable versioned data packages. No website scraping, accounts, cloud services or paid APIs.

Import PDF and images, offline extraction, mandatory batch review, SQLite storage, source attachments, school trends and same-event/same-division comparisons including every caption and judge subscore. Export and merge packages with originals, explicit conflict resolution and undo. Preserve missing values and original labels. Exhibition remains separate. Clear screenshots/PDF prioritized; photos may need correction. OCR accuracy must be measured, never presumed.

Implementation: Python + Qt Widgets, RapidOCR ONNX CPU models packaged locally, pdfplumber text extraction and PDFium rendering, versioned JSON+ZIP exchange. Source/data layer independent of UI. Mobile UI and mobile OCR packaging are a later phase.

Acceptance: sample imports reviewable; no unreviewed data in analytics; exact confirmed values persist; missing/cropped data marked; duplicates skipped; conflicts explicit; package roundtrip includes sources; undo restores prior records; application works offline after installation.

## Approved update: 1.1

User reviewed the updated planning summary and explicitly authorized implementation.

- Default school: Arroyo Knight Band & Colorguard, editable in Data Management. Recognize the existing plural Knights spelling as an alias; retain original source names. Default applies to school selection and manual entry, never to replacing OCR school names.
- Sidebar: Schools, Events, Season overview, Import & review, Data Management. Open Schools first.
- Store awards explicitly present in source material, with editable source notes. Preserve them in exchange packages and undo history. Highlight source-ranked first place (including ties) for all displayed metrics; show major-caption highlights and keep judge/subcaption ranks in details. Highest imported scores without source rank 1 must not be represented as official first place.
- Refresh the English interface with navy navigation, teal controls, gold first-place accents, score cards and clearer tables.
- Keep existing local data and accept version-1 packages. Version-2 exports carry awards; local default-school preferences do not travel in shared score packages.
# Approved update 1.2.0

Larger resizable charts with an expanded view; clickable points/bars and shared school score details. Bold only the six main totals, not judge subtotals. Season bars count schools per event and open division-separated rankings with school drill-down. Keep school Awards & highlights, award editing and source-first gold marks; remove other award display cards and first-place stat cards. Preserve existing records, originals and exchange compatibility; no award inference.

# Authorized security repair 1.2.1

Repair the seven reviewed findings: update affected image/PDF dependencies; whitelist actual image formats and enforce predecode/page/batch resource limits; enforce JSON numeric types; resolve cross-scoring-system collisions only by keeping/replacing whole records; normalize award-name conflicts and validate merged records; atomically write and repair originals with hash checks. Keep normal v1/v2 packages and existing database schema compatible. Regression-test hostile inputs safely, original sample OCR and the portable runtime. No automatic rewriting of saved scores.

