# Browser security review — 2026-10-28

Scope: application TypeScript, build/deployment configuration, package validation and browser-local storage. This is a bounded static review and functional check, not a penetration-test certification.

## Controls checked / fixes applied

- No app secrets or account credentials embedded in the client. OCR/PDF processing uses local files and same-origin model/runtime downloads; the app has no score-upload endpoint, analytics, scraping or remote model API.
- Untrusted strings are escaped before HTML interpolation or assigned with `textContent`. Numeric scores, ranks, dates, source names and award objects are validated, including prototype-property rejection.
- ZIP files are not extracted to the filesystem. Manifest and hashed asset names are allowlisted, original bytes are SHA-256 checked, and duplicate/encrypted/oversized entries are rejected. Both per-entry and cumulative **actual expanded bytes** are bounded, independently of advertised ZIP sizes.
- Image dimensions are checked before full decoding. File/page/pixel limits bound normal input workloads. Large valid inputs may still be slow or fail under browser memory limits.
- PDF originals are rendered by the bundled PDF.js to canvas, not embedded as active documents. Dependencies are lockfile-pinned; the latest audit in this review reported zero known vulnerabilities.
- Production CSP restricts executable content and connections to the same origin, disallows frames/objects, and allows WASM required by local OCR. GitHub Pages serves over HTTPS. The workflow has read-only repository permissions except the deployment job's Pages/OIDC permissions.
- IndexedDB saves are transactional. Stale revisions reject concurrent overwrites; undo preserves prior records. Review confirmation and explicit conflict choices precede import commits.
- Development QA uses a separate, clearly labelled database and is disabled in production.

## Remaining operational limits

The library is unencrypted browser-local storage shared by users of the same profile/origin; it is not an account-isolated or encrypted vault. Browser extensions, compromised same-origin code or local device access can access it. Browser clearing/eviction can lose data; export backups. Original attachments are included in shared packages, so inspect their contents before sharing. Repository/hosting account access and future dependency updates remain maintenance responsibilities. No claim of complete security is made.
