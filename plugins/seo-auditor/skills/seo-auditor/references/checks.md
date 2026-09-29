# Checks and interpretation

| Area | Required evidence | Avoid |
|---|---|---|
| HTTP | Actual request status, final URL and redirects | Guessing status from a saved page |
| Crawl | Retrieved robots and scope/user-agent interpretation | Treating disallow as noindex |
| Index | Real meta/header directives and page intent | Claiming actual indexed status from HTML alone |
| Canonical | Head/HTTP declarations plus target evidence | Flagging every absent canonical as a critical failure |
| Metadata | Exact title/description from inspected source or DOM | Arbitrary hard character limits or guaranteed rankings |
| Headings | Visible structure and actual document content | Treating every second h1 as an automatic penalty |
| Images | Context and actual alt attribute | Calling decorative alt="" incorrect by default |
| Structured data | Current engine requirements and real visible facts | Fake reviews, invented offers, schema-valid = eligible |
| Performance | Measured tool, run time, device and field/lab type | Invented Lighthouse scores or Core Web Vitals |
| Coverage | Attempted/inspected pages, URL filters, failures | Calling a 10-page sample a full-site audit |

Severity expresses likely action priority, not a Google penalty or ranking prediction.
Blocked login/admin/checkout URLs may be correct. Review intended visibility before changes.
The helper checks only static HTML and records other checks as not performed.
A link destination is not "broken" unless an actual relevant response was observed.
