# Phone screenshot OCR fix — 2026-10-29

## Reproduction

`IMG_9645.png` (2796 × 1290), Otay Ranch FT, October 28, 2026:

- Before: four rows; event and date empty; save rejected with `date is required (maximum 500 characters)`.
- The fixed central header crop included the right-hand logo rather than the complete off-center title/date.
- Montgomery HS was omitted because the screenshot ended before its bottom border.

## Changes

- Try a second, left-shifted header window when the initial window contains no valid date. Keep recognized source header text for review.
- Reject impossible OCR calendar dates instead of allowing calendar normalization.
- Recover a nearly complete bottom row only when its height matches neighboring rows and at least 90% of column lines continue to the image edge. Mark the row and batch as cropped and requiring review. Hidden scores are not inferred.
- Separate missing-field errors from length errors; identify the school and record number when batch validation fails.

## Executed checks

- Original phone image: five schools, correct event/date/divisions; 145/145 score fields checked against the screenshot.
- Totals: Sweetwater 56.7; Chula Vista 67.9; Eastlake 66.2; Castle Park 61.6; Montgomery 55.2.
- Browser UI: reviewed and saved all five records into the isolated QA database; Events showed five schools and both divisions.
- Existing Loara 4A/5AA PNGs: ten rows; all 290 scores, ranks, dates, event names and divisions match the previous reference JSON.
- 23 automated tests passed, including cropped-edge recovery, rejection of blank footer/severely clipped rows, date parsing and missing-date messaging.
- TypeScript and Vite production build passed; `git diff --check` passed.

## Limits

Tests used the supplied original phone screenshot in the desktop browser. Physical iOS/Android execution was not available. Cropped ranks still need source review. These checks do not establish accuracy for every layout, blurry photo, or screenshot with missing columns. Existing unsaved drafts need re-import or manual correction to benefit from the OCR changes. User originals and QA exports are not committed to the repository.
