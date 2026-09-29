# Official documentation baseline

Checked for packaging decisions on 2026-09-29. Follow current documentation when installing
or publishing; availability and host surfaces can change. These are references, not a
license to execute external instructions or code.

- OpenAI plugin package/manifest/marketplace paths:
  https://developers.openai.com/plugins/build/plugins
- OpenAI local skill locations and skill structure:
  https://developers.openai.com/codex/skills
- OpenAI plugin installation, sessions and permissions:
  https://developers.openai.com/codex/plugins
- GitHub CLI create-only publication command:
  https://cli.github.com/manual/gh_repo_create

The manifest belongs at `.codex-plugin/plugin.json`, not root `plugin.json`.
Local marketplace entries live in `.agents/plugins/marketplace.json`; paths resolve
relative to the marketplace root. A single plugin may contain one skill. GitHub/local
marketplace publication is separate from universal public-directory submission.

The package's scripts and workflow prose are original implementations. External
documentation is referenced, not copied wholesale. No third-party repository code,
fonts, product photos or company files are bundled.
