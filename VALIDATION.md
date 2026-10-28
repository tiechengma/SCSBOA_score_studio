# Validation record — Windows 1.2.1

Portable v1.2.1 passed isolated PNG, PDF and HEIF runs, including offline models and JSON CMap loading. PNG totals: 78.2 / 71.7 / 67.6. PDF first page: 14 complete rows with five cropped totals Missing. Blank HEIF fixture decoded with zero records as expected. No unconfirmed records saved.

1.2.1 security regression: 29 unit tests pass; Qt integration including whole-record scheme conflict choices passes. Supported image formats decode after dependency upgrades. Reference screenshot OCR still matches all 290 score cells. Full two-page PDF import yields 22 complete rows / 17 available totals, pages 1 and 2, with no unconfirmed records saved. All 30 pinned packages were checked using PyPI's version API with no active advisory returned. See SECURITY_FIXES.md for limits and repair behavior. Older validation entries below describe historical builds.

Portable v1.2.0 EXE passed isolated Qt startup and offline model loading. Build location: dist/v1.2.0/. The old running app was not terminated; the user's normal library was not used for verification.

1.2.0: 17 unit tests pass. Qt integration clicks actual chart hit regions in Schools, Events and Season, opens school details through event rankings, and repeats school drill-down from the expanded chart. Verified all six main-total label/value fonts are bold and all other score label/value fonts are regular; Source awards editing tab remains available. Ranking fixture has 10 schools split into 4A (7) and 5AA (3), with independent top scores 71.9 and 78.2. Missing chart values have no hit region, zero values remain clickable, and drag movement does not activate details. Source UI screenshots checked at 1480 × 960 and 1100 × 740. Charts/table use an adjustable vertical divider; only Schools retains the awards display.

1.1.1: 17 unit tests and Qt integration pass. Added exact season/scoring-pair filtering checks with two 2027 scoring systems, selection retention and fallback after data removal. Larger chart text checked at 1480 × 960 and 1100 × 740; wide datasets have horizontal scrolling and full-label hover text. The isolated v1.1.1 portable EXE passed Qt startup and offline model loading. Release location: dist/v1.1.1/. Awards inference is a researched proposal only, not implemented in this release.

Update checks: 17 unit tests pass, covering persistent default-school preferences, alias matching, award validation/edit/undo, package v1 compatibility and v2 award conflicts, tied source firsts and partial imported leaders. Qt integration passes navigation order, startup school, manual-entry default, preference changes, award undo, gold highlights, review/save boundary and package originals. Updated views were inspected at 1480 × 960. OCR itself is unchanged; the original fixture results below remain the baseline.

Environment: Windows 11 x64, Python 3.12.14, PySide6 6.10.1. Dependencies are pinned in requirements-lock.txt. Tests use isolated libraries under tmp/, not the normal user library.

Version 1.1 portable EXE verification also passed: Qt window, offline model loading, three 5AA records with totals 78.2 / 71.7 / 67.6, and no unconfirmed records saved. Both 1480 × 960 and 1100 × 740 layouts were visually checked; smaller tables use horizontal scrolling.

## Completed checks

- Library tests: unconfirmed preview does not save; confirmed persistence; duplicate skipping; complementary merge; conflict cancellation is atomic; explicit replacement; undo restores the prior state; official divisions remain separate.
- Package tests: structured data and original bytes roundtrip into a separate library; unsupported versions, path traversal, missing attachments and checksum corruption are rejected.
- Screenshot integration: compared all 290 printed score values across the supplied 4A and 5AA screenshots (10 schools, 29 columns each). All 290 matched the manually transcribed reference values. School names, event and date also matched. This is a result for those two images only, not a general OCR accuracy claim.
- Qt UI integration: editing drafts and switching records, batch confirmation, correct group selection (7 schools in 4A / 3 in 5AA), chart values, package import with originals and undo. Screenshots were visually inspected at 1440 × 940.
- Source compilation and Python unit test suite pass.
- Nine unit tests pass, including generated PNG/JPEG/WebP/BMP/TIFF/HEIC decoder roundtrips.
- All 10 final-score ranks match the reference screenshots. All eight judge labels were extracted for the first 5AA record.
- Final PDF run: 22 complete school rows identified across the two pages; 17 final totals read. The five 5A final-total cells lack a complete right boundary in the clipped source and remain Missing. The split first 5AA row requires the supplied full screenshot or manual entry. Event date remains 2026-10-24 rather than the print date.

## Known limits

- The two-page reference PDF is a rasterized, clipped printout. The app identifies complete row regions and warns about clipped captions and page breaks. One 5AA row is split at the page boundary and must be supplemented using the complete screenshot or manually entered. OCR output from the PDF requires more correction than the screenshots.
- Ranks and judge labels are extracted and editable, but every rank/judge cell has not been independently transcribed into an automated oracle.
- Recognition beyond the supplied layout, low-quality photos, every possible HEIC variant and different Windows hardware have not been validated. Different layouts may require manual entry.
- No mobile app or cloud synchronization is included.
- Portable executable startup, Qt rendering, locally bundled OCR model loading and PNG recognition passed. The packaged build read the 5AA totals as 78.200, 71.700 and 67.600, with no unconfirmed records in its test library.
- A build-host ICU DLL collision was identified during executable testing and fixed in the supplied PyInstaller spec. The app uses the Windows system ICU library expected by Qt.
- Final windowed executable also passed PDF rendering and OCR on the first page of the supplied PDF: 14 complete rows recognized, with the five clipped 5A final totals left Missing; no unconfirmed rows were saved. Whole-document two-page handling was tested in the source integration run described above.
