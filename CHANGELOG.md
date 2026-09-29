# Changelog

## Unreleased — 2026-09-29

- Reject NaN and Infinity JSON-LD constants as syntax errors.
- Stop before fetching pages when robots.txt repeats a user-agent group; the standard-library parser does not merge those rules.
- Add regression tests for repeated groups, case/comment handling, JSON constants and valid numeric/string values.

## 0.1.0 — 2026-09-29

- Initial independent SEO Auditor skill and single-skill plugin.
- Relative-path references, project-local optional configuration, Korean/English guide.
- Explicit capability checks; no proprietary/company defaults, credentials or hooks.
- Local helper scripts and automated tests; safe local installer and create-only GitHub publisher.
- Packaging uses .codex-plugin/plugin.json with a one-entry .agents/plugins/marketplace.json.
- Host UI installation, model-quality evaluation and public-directory approval are not certified.
