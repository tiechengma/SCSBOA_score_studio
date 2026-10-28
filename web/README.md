# Score Studio — browser edition

English, local-first SCSBOA field-score library. No account or paid OCR API. Import PNG/JPEG/WebP/PDF, review the drafts, and confirm each batch before it enters analytics. Export and merge `.scsboa` v2 packages with originals; accepts v1/v2 packages from the Windows app.

## Run locally

Requires Node.js 24 and npm. From `web/`:

```
npm ci
npm run dev
```

Open the exact localhost address printed by Vite. `npm test` checks model validation, merge safety, packages and database transactions. `npm run build` creates `dist/` for static HTTPS hosting. Model/character files are tracked; the pinned ONNX runtime and license notices are copied from installed dependencies during build. No Python service is required by the browser app.

For isolated development QA only, append `?qa=1` to the dev URL. A prominent banner identifies a separate IndexedDB database (`scsboa-score-studio-isolated-qa`). The production build does not enable QA mode.

## Privacy and data

Scores and originals remain in IndexedDB in the current browser profile. Hosting serves application/model assets; score files are not sent to an OCR service. Another browser or device has a separate library. People using the same browser profile share its library. Export a `.scsboa` backup before clearing site data or switching browsers. Private browsing, storage pressure, or manual clearing may delete browser data. Persistent-storage requests can be declined. Closing the page stops work and discards unconfirmed drafts after a warning.

## Recognition limits

Designed for upright SCSBOA recap grids, prioritizing clear screenshots. Cropped/split PDF rows, small ranks and school spelling require review. Numeric OCR errors are not guessed. A known `0ctober` month-token confusion is normalized to October with an explicit review note. Source ranks—not computed placement—control gold first-place markers. Awards require manually supplied source evidence.

HEIC/HEIF are not accepted in this release: convert to PNG/JPEG. Desktop Chrome/Edge are the target. Mobile layout is responsive; full mobile OCR performance is not guaranteed until device testing. First use downloads model/runtime assets; offline availability is not guaranteed.

Limits: originals 100 MB each; batch/package 512 MB; 100 files and 100 PDF pages per document; 40 megapixels/page and 400 megapixels/batch. Package checks use bounds, CRC and SHA-256, not a signature establishing the original publisher's identity.

## Deployment

Repository `.github/workflows/pages.yml` builds/tests the web app and deploys only `web/dist` to GitHub Pages. Enable GitHub Pages with the GitHub Actions source. Do not deploy reference screenshots, test PDFs, database exports, `tmp/`, `experiments/` or desktop user data.
