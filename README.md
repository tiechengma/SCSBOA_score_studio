# SCSBOA Score Studio

SCSBOA field-season scores, with an English browser app and an offline Windows app. No accounts, website scraping, paid model API or score-upload service.

## Open the browser app

**[Launch SCSBOA Score Studio](https://tiechengma.github.io/SCSBOA_score_studio/)**

Open the link in a current desktop Chrome or Edge browser. Import images/PDFs, review each batch, then save to your own browser-local library. Share and back up using `.scsboa` packages, including originals. Browser and Windows packages are compatible.

Your scores are stored in this browser profile, not on GitHub. Clearing site data can erase the library; export backups regularly. First use downloads the OCR model. HEIC/HEIF must be converted to PNG/JPEG. Mobile viewing uses a responsive layout; full mobile OCR is not guaranteed.

See [web instructions](web/README.md), [web validation](WEB_VALIDATION.md) and [web security review](WEB_SECURITY.md). The link is deployed by the repository's GitHub Pages workflow; an initial deployment may take several minutes.

## Windows edition

The existing desktop app remains available from its portable build. Its version history follows.

## Version 1.2.1 — security and data integrity

Release folder: `dist/v1.2.1/`. Pillow, HEIF and compatible PDF dependencies are updated. Image content must match an allowed extension; pixel dimensions are checked before decoding/rendering (40 MP, maximum side 20,000 pixels). An OCR batch allows up to 100 files, 512 MB of source bytes and 400 MP of decoded pages. Individual originals remain limited to 100 MB and PDFs to 100 pages.

Packages require actual JSON numbers or null for scores/ranks (not strings/booleans). Different scoring systems now require keeping the whole saved record or replacing it with the whole incoming record, never mixing captions. Award names merge case-insensitively and final records are validated before committing. Originals are written atomically, damaged caches can be repaired by reimporting a valid source/package, and exports check original hashes. See SECURITY_FIXES.md for regression results and remaining limits.

## Version 1.2.0

Charts occupy about two thirds of the chart/table area. Drag the divider or use Expand chart. Click a point, bar or table row to open the matching school's score details. Six main totals are bold; individual judges' totals are not. Source rank 1 remains gold. The Original tab shows source files and Source awards keeps award editing.

Season bars count distinct imported schools per event. Clicking opens all imported results for that event, separated by official division, with selectable score metrics. Source rank and imported order are labeled separately. Click a school to drill into its scores. Only the school page retains Awards & highlights; other award cards and first-place statistic cards have been removed. Existing awards and package compatibility are preserved.

This release is built under `dist/v1.2.0/`. Close an older running instance before launching the new executable; both use the same local library.

## Version 1.1.1

Charts use larger, darker text and bold score labels. Wide charts scroll horizontally; hover a point or bar to read the full label and score. The combined Season / scoring filter selects one exact season/scoring-system pair, such as “2026 · SCSBOA Field”.

## Version 1.1

The app opens on Schools with Arroyo Knight Band & Colorguard as the initial default. Change and save it in Data Management. The known “Arroyo Knights” spelling groups with this school while preserving the source name. Preferences stay on this device and are not exported.

Navigation is Schools → Events → Season overview → Import & review → Data Management. Gold highlights mark source rank 1, including ties. Without a source first-place rank, event cards explicitly show the highest imported score instead. Named awards are entered with a source note in Source awards during review or in a saved result's details; score ranks do not invent named awards. Award edits support undo and package sharing.

Version 1.1 imports both version 1 and 2 packages and exports version 2. Recipients should update to 1.1 to read the new award fields. Other unsupported package versions are rejected.

## Quick start

Open `dist/SCSBOA-Score-Studio/SCSBOA-Score-Studio.exe`. Keep the complete folder, including `_internal`, together. Python is not required for the portable build. The initial library is empty; test data is never added to your personal library automatically.

1. Open **Import & review**, then **Import images / PDF**, or drag files into the window.
2. Wait for offline recognition. Click a school in the pending table.
3. Review **Details & judges** and **Scores & ranks** against the original. Double-click a score to change it. Blank means Missing; it is not zero. Scroll over the original to zoom, drag to pan, or click **Fit**.
4. Read **View import notes** for cropping and page-break issues. Use **Add record** for omitted/partial rows. PDF page controls let you inspect other pages; **Attach this page** records additional provenance.
5. Use **Apply edits & check totals**, then **Confirm & save batch**. Confirmation applies to the whole batch. Unconfirmed data never appears in charts.
6. Browse **Schools** for trends and **Events** for same-event, same-division comparisons. The metric selector includes all 29 printed score columns. Double-click a saved row to inspect details and originals.
7. Use **Data management** to export `.scsboa` packages with original files, import packages for review, or undo the most recent saved batch.

## Supported inputs and limits

- PDF, PNG, JPEG, WebP, BMP, TIFF and HEIC/HEIF (decoder included). Multi-page PDF is supported; image imports use the first frame of animated or multipage image formats.
- Primary automated layout: the supplied SCSBOA field recap with Music, GE, Visual, penalties, Auxiliary and Percussion, and score/rank pairs. Different layouts and photos may need manual entry.
- Up to 100 PDF pages, 100 MB per source, 40 megapixels per image; packages limited to 512 MB expanded. Split larger material.
- A clipped PDF cannot supply invisible columns. Partial rows at page breaks may be omitted and must be added manually or supplemented by a complete screenshot. Always compare school counts against the original.
- OCR is a draft, not a guarantee. Check school names, dates, every score/rank, and inherited continuation headings. Arithmetic checks flag discrepancies but never rewrite scores.
- Preserve official division labels (including 5AA, RED/BLACK and Exhibition). Keep a consistent canonical school name for trends; the original school name is stored separately. Previously saved schools are offered as autocomplete suggestions.
- `Scoring scheme` separates incompatible scoring scales. Change this field when importing a different season/rule set; matching column names alone do not prove compatibility. The built-in parser targets 2026.
- Auxiliary/Percussion raw and factored totals remain separate and are not added to the final band score. Weighting rules are not inferred for unknown layouts.
- Season coverage shows only imported records, never a claim of complete official coverage.

## Storage, sharing and undo

Personal library: `%LOCALAPPDATA%/SCSBOA Score Studio/`. `library.sqlite` contains confirmed records; `assets/` contains content-addressed originals. Close the app before making a manual copy of this directory. Export packages are the preferred portable backup.

Packages use a versioned JSON manifest plus original files. Import validates attachment hashes and never extracts arbitrary archive paths. Unsupported package versions are rejected rather than guessed. Exact matches do not duplicate scores; complementary fields are merged after batch confirmation; conflicting fields require explicit choices. Cancel a conflict dialog to leave the entire batch unsaved. School/event/date/division identity changes create distinct records, so correct names before confirming.

Undo restores the record state immediately before the latest saved batch, including prior values of replaced fields. Originals are retained even after cancellation/undo to avoid losing source evidence. The current unconfirmed review batch is not persisted when closing; the app asks before discarding it.

When sharing, send the full portable app folder/ZIP and a data package separately. The recipient does not need your Windows username or original file paths. Share only documents you are entitled to share.

## Development

Python 3.12 (64-bit). Install `requirements.txt` into a virtual environment. Run `python main.py`.

```powershell
python -m unittest discover -s tests -v
python tools/verify_samples.py 'PATH_TO_REFERENCE_SCREENSHOTS'
$env:QT_QPA_PLATFORM='offscreen'
python tools/verify_ui.py 'PATH_TO_REFERENCE_SCREENSHOTS'
```

The sample verification scripts require the two user-provided images; they are not redistributed in the app. `SCORESTUDIO_DATA` can override the library directory for isolated testing. `--verify-install OUTPUT_FOLDER [SAMPLE_IMAGE]` checks the packaged Qt window, offline model loading and optional OCR without modifying the normal library.

Build command:

```powershell
python -m PyInstaller --noconfirm SCSBOA-Score-Studio.spec
python tools/package_release.py
```

The optional ONNX quantization tooling is not needed for inference; PyInstaller may warn that the optional `onnx` developer package is absent. Runtime model loading is checked separately.

Use the supplied spec: it excludes an unrelated build-host ICU DLL which would otherwise shadow the Windows system ICU library expected by Qt. The portable executable uses the Windows system ICU ABI.

## Future mobile work

The SQLite/JSON record model and exchange format are independent of the Qt desktop UI. Mobile UI, file permissions, OCR model packaging, distribution and testing remain a separate phase; this release does not claim to run on a phone.

Third-party software and model licensing notices are in `THIRD_PARTY_NOTICES.md` and the portable build's `licenses/` directory. Keep these notices with copies.
