# SEO audit

**Read-only static evidence. No ranking score or full-site certification.**

Inspected pages: 1. Mode: offline-html. See audit.json for full coverage and evidence.

| Page | Finding | Severity | Evidence | Action |
|---|---|---|---|---|
| https://example.invalid/ | DESCRIPTION_MISSING | low | sources/page-001.html.txt — No nonempty meta description. | Consider a useful page-specific summary; no fixed character count or ranking guarantee. |
| https://example.invalid/ | CANONICAL_RELATIVE | low | sources/page-001.html.txt:L7 — /product/example | Prefer an absolute canonical to avoid environment-dependent resolution. |
| https://example.invalid/ | NOINDEX_META | high | sources/page-001.html.txt:L6 — {'name': 'robots', 'content': 'noindex', 'line': 6} | Compare with intended indexability. Do not remove noindex without checking page purpose. |
| https://example.invalid/ | IMG_ALT_MISSING | low | sources/page-001.html.txt — [{'src': 'example.png', 'line': 13}] | Give informative images descriptive alt; decorative images may deliberately use alt="". |
| https://example.invalid/ | JSONLD_PARSE_ERROR | medium | sources/page-001.html.txt:L8 — Illegal trailing comma before end of object: line 1 column 33 (char 32) | Fix JSON syntax, then separately check schema meaning and current rich-result requirements. |

## Not inspected / errors

None recorded.

## Duplicate titles within the sample

None found in the inspected sample.

## Not checked

- Rendered DOM/JavaScript
- Search Console and actual index status
- Core Web Vitals, page speed or Lighthouse
- Full sitemap validity
- Rich-result eligibility and structured data semantics
- All links and canonical target availability

## Interpretation

Absence of canonical/JSON-LD or multiple h1 elements is a review item, not an automatic ranking defect.
Robots disallow and noindex are different. Do not remove exclusion controls without confirming site intent.
An HTTP or permission failure is not a completed inspection. Static HTML may differ from rendered DOM.
Use current official search-engine guidance when proposing changes. No live files were modified.
