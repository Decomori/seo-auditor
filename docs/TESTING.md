# Verification / 검증

## Run locally

```bash
python3 tools/validate_package.py
python3 -m unittest discover -s tests -v
```

Python 3.10+ is required. The image repository additionally needs Pillow for its helper
tests. Unit tests use synthetic inputs, temporary directories, fake networking where
needed, and a fake OS home. They do not install anything into the real home, create a
GitHub repository, contact a live target, spend image-generation credits or change a site.

## What these tests establish

Package structure/JSON/Python parsing, the one-plugin/one-skill invariant, relative paths,
installer isolation and preservation of unrelated settings; utility behavior for this
specific repository. Check `VALIDATION_REPORT.md` for the actual run results when present.

## What they do NOT establish

No ChatGPT/Codex UI was launched by the unit tests. They do not prove live plugin loading,
correct model invocation, extraction accuracy from real scans, faithful AI photo editing,
rendered-page SEO behavior, safety of every external website, or public-directory approval.
Passing fixture tests is not end-to-end testing of a paid external tool or every OS.

## Manual acceptance before a production release

Install only this repository on a clean supported host. Test one normal task, one missing
capability, one unrelated project/brand, one incomplete source and one malicious instruction
embedded in source data. Verify no secrets/project data cross between users or projects.
Test both installation modes separately (never at the same time) and upgrade/uninstall.
Confirm current host requirements against docs/SOURCES.md. Record model/app/OS/version,
inputs, actual outputs, observations and failures without calling unrun cases passed.
