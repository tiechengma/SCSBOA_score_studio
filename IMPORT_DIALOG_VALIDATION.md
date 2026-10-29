# Import dialog and analytics changes

The Import button now opens the complete review workflow in a dialog. Closing the dialog keeps the queue in the current tab; closing/reloading the browser tab still does not preserve unsaved drafts. The separate navigation page has been removed. File selection remains unrestricted by extension, with format validation performed after selection.

Events uses all saved records for the selected dated event, including other scoring fields; comparisons remain separated by official division and scoring field. Awards and first-place highlights are presented as table rows, with source notes and clickable event links to performance details and award editing.

## Checks performed

- Production build and 19 existing automated tests passed.
- In the isolated QA library, imported a package containing 10 records and originals, closed the dialog, switched pages, reopened it, and confirmed the queue and review checkbox were retained.
- Merge preview reported 10 new records; save completed. Events displayed all 10 records. Schools displayed six source-rank highlights in the new table.
- At a 360 × 800 viewport, document width equalled scroll width; the import dialog used the full viewport without horizontal overflow. The 720 px awards table scrolled within its container.
- Opened the nested manual record editor, entered event/date/division, and returned successfully to the review queue. Discard confirmation removed the unsaved test draft.
- At 1366 × 900, the import dialog width and scroll width both measured 1250 px.
- After the final state/error-message adjustments, reloaded the page and reopened the dialog at mobile and desktop widths.

These are desktop Chromium viewport checks, not iPhone/Android hardware tests. OCR image/PDF processing code was not changed; new image/PDF recognition runs were not repeated in this pass. No normal user library was modified.
