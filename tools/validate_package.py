#!/usr/bin/env python3
"""Offline structural checks, NOT official directory approval or host compatibility certification."""
from __future__ import annotations
import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)
    try:
        catalog = json.loads((root / '.agents/plugins/marketplace.json').read_text('utf-8'))
        require(len(catalog['plugins']) == 1, 'A repository must contain exactly one plugin.')
        entry = catalog['plugins'][0]
        slug = entry['name']
        source = entry['source']
        require(source['source'] == 'local', 'Marketplace must use a local source.')
        require(source['path'].startswith('./'), 'Marketplace path must begin with ./')
        plugin = (root / source['path']).resolve()
        require(plugin.is_relative_to(root.resolve()), 'Plugin escapes repository.')
        if not plugin.is_relative_to(root.resolve()):
            return errors
        manifest = json.loads((plugin / '.codex-plugin/plugin.json').read_text('utf-8'))
        require(manifest['name'] == slug, 'Plugin name mismatch.')
        require(bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug)), 'Invalid slug.')
        require(manifest['version'] == (root / 'VERSION').read_text().strip(), 'Version mismatch.')
        require(manifest['skills'] == './skills/', 'Skills path must be ./skills/.')
        require('mcpServers' not in manifest and 'apps' not in manifest and 'hooks' not in manifest,
                'v0.1 must not contain unconfigured external servers, connections or hooks.')
        skills = list((plugin / 'skills').glob('*/SKILL.md'))
        require(len(skills) == 1, 'Exactly one skill is required.')
        text = skills[0].read_text('utf-8')
        require(text.startswith('---\n'), 'Missing YAML front matter.')
        require(f'name: {slug}\n' in text, 'Skill name mismatch.')
        require('description:' in text.split('---', 2)[1], 'Missing trigger description.')
        require(len(text.splitlines()) <= 350, 'Skill is too long; move detail into references.')
        for relative in ['README.md', 'README.en.md', 'LICENSE', 'SECURITY.md', 'PRIVACY.md',
                         'docs/INSTALL.md', 'docs/SHARING.md', 'docs/TESTING.md', 'docs/SOURCES.md']:
            require((root / relative).is_file(), f'Missing {relative}')
        require(not (root / 'plugin.json').exists(), 'plugin.json belongs in .codex-plugin/.')
        for file in root.rglob('*'):
            require(not file.is_symlink(), f'Symlink not allowed: {file.relative_to(root)}')
            if not file.is_file() or '__pycache__' in file.parts:
                continue
            if file.suffix == '.json':
                json.loads(file.read_text('utf-8'))
            if file.suffix == '.py':
                ast.parse(file.read_text('utf-8'), filename=str(file))
    except (OSError, KeyError, IndexError, TypeError, ValueError, SyntaxError) as exc:
        errors.append(str(exc))
    return errors

if __name__ == '__main__':
    found = validate()
    if found:
        print('\n'.join('FAIL: ' + item for item in found), file=sys.stderr)
        raise SystemExit(1)
    print('PASS: one independent plugin, one skill, relative paths, JSON and Python syntax.')
    print('NOT TESTED HERE: ChatGPT/Codex UI loading, public-directory submission, model output quality.')
