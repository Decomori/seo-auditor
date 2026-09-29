# SEO Auditor

Independent agent skill and single-skill plugin, version 0.1.0. No dependency on any
sibling plugin, company data, fixed domain, saved account context or personal paths.
[한국어](README.md)

## Install
Ask a supported local agent to read this repository's README and `docs/INSTALL.md`,
review the scripts, and install **one** of the following modes. Do not install both.

```bash
python3 tools/manage.py install --mode plugin
# OR, for a local skills-capable host:
python3 tools/manage.py install --mode skill
```

Plugin mode registers files in the personal marketplace; it does not click the app's
Install/Enable button. Restart the desktop app, select the plugin in Plugins, install or
enable it, and start a new chat. Skill mode copies only the skill to `~/.agents/skills/`.
The required plugin manifest lives at `plugins/seo-auditor/.codex-plugin/plugin.json`.

Required capabilities: Host browsing or Python 3.10+; rendered DOM and performance tools are optional and separate.

This is an agent workflow with deterministic helpers, not a bundled image/LLM service.
Python 3.10+ is required for helpers. Product Visual's helpers additionally require Pillow.
Use `docs/TESTING.md` for actual automated coverage and untested host/runtime boundaries.

## Share
Publish this repository separately from unrelated skills. `tools/publish.py --plan`
lists exactly the files to upload without network access. Explicit `--confirm` is required
to create a repository. It defaults to private, uses your own `gh` authentication, and
never modifies an existing remote repository. See `docs/SHARING.md`.
A GitHub repository is not automatic publication in the universal ChatGPT directory.
Web/mobile distribution and directory review remain separate.

## Use, update, remove
Keep client assets, project preferences and credentials outside this repository.
`tools/manage.py install --mode plugin --replace` updates only this managed plugin with a
backup. `tools/manage.py uninstall --mode plugin --confirm` removes only this registration
and installed directory. Use `--mode skill` for the standalone copy instead.

No background hooks, telemetry, shared API keys or automatic production writes are bundled.
See SECURITY.md and PRIVACY.md for processing boundaries. MIT licensed.
