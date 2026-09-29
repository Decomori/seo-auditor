#!/usr/bin/env python3
"""Create ONE new GitHub repository. Never pushes into an existing repository."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = {'README.md', 'README.en.md', 'LICENSE', 'VERSION', 'AGENTS.md', '.gitignore',
             'SECURITY.md', 'PRIVACY.md', 'CHANGELOG.md', 'requirements.txt'}
TOP_DIRS = {'plugins', 'tools', 'tests', 'docs', '.agents'}
SKIP_PARTS = {'__pycache__', '.venv', 'node_modules', '.git', 'private', 'outputs', 'inputs', 'local'}


def run(cmd: list[str], cwd: Path | None = None, capture: bool = True) -> str:
    result = subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=capture)
    return result.stdout.strip() if capture else ''


def public_files(root: Path):
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Refusing symlink: {path.relative_to(root)}')
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        if len(relative.parts) == 1 and relative.name not in TOP_FILES:
            continue
        if len(relative.parts) > 1 and relative.parts[0] not in TOP_DIRS:
            continue
        if path.suffix in {'.pyc', '.key', '.pem'} or path.name.startswith('.env') or '.local.' in path.name:
            raise ValueError(f'Potential private file excluded from publication: {relative}')
        data = path.read_bytes()
        if len(data) > 5_000_000:
            raise ValueError(f'Unexpected large file: {relative}; review publication manually.')
        text = data.decode('utf-8', errors='ignore')
        patterns = [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                    r'\bgh[pousr]_[A-Za-z0-9]{30,}', r'\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}']
        if any(re.search(pattern, text) for pattern in patterns):
            raise ValueError(f'Possible credential in {relative}. No repository created.')
        yield relative


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', help='Must equal the authenticated personal GitHub login.')
    parser.add_argument('--visibility', choices=['private', 'public'], default='private')
    parser.add_argument('--confirm', action='store_true', help='Explicitly allow creating and uploading this new repository.')
    parser.add_argument('--plan', action='store_true', help='List files without network access or GitHub changes.')
    args = parser.parse_args()
    try:
        catalog = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text('utf-8'))
        name = catalog['plugins'][0]['name']
        files = list(public_files(ROOT))
        if args.plan or not args.confirm:
            print(json.dumps({'repository_name': name, 'visibility': args.visibility,
                              'file_count': len(files), 'files': [str(x) for x in files],
                              'note': 'No GitHub changes. Review these files; publication requires --confirm.'}, indent=2))
            return 0
        for exe in ['git', 'gh']:
            if not shutil.which(exe):
                raise ValueError(f'{exe} is required. Install it separately; this helper never installs software.')
        run([sys.executable, 'tools/validate_package.py'], ROOT)
        run(['gh', 'auth', 'status'])
        identity = json.loads(run(['gh', 'api', 'user']))
        login = identity['login']
        if args.owner and args.owner.casefold() != login.casefold():
            raise ValueError(f'Authenticated as {login}, not requested owner. Switch your gh account first.')
        repository = f'{login}/{name}'
        exists = subprocess.run(['gh', 'repo', 'view', repository, '--json', 'name'], capture_output=True, text=True)
        if exists.returncode == 0:
            raise ValueError(f'{repository} already exists. This helper never changes existing repositories.')
        # An existence-check network failure cannot overwrite anything: gh repo create below is create-only.
        with tempfile.TemporaryDirectory(prefix=name + '-publish-') as directory:
            stage = Path(directory)
            for relative in files:
                out = stage / relative
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, out)
            run(['git', 'init', '-b', 'main'], stage)
            run(['git', 'config', 'user.name', login], stage)
            run(['git', 'config', 'user.email', f"{identity['id']}+{login}@users.noreply.github.com"], stage)
            run(['git', 'add', '.'], stage)
            version = (stage / 'VERSION').read_text().strip()
            run(['git', 'commit', '-m', f'Initial independent skill and plugin release {version}'], stage)
            manifest = json.loads((stage / 'plugins' / name / '.codex-plugin/plugin.json').read_text('utf-8'))
            print(f'Creating {repository} ({args.visibility}) with {len(files)} reviewed files.', flush=True)
            run(['gh', 'repo', 'create', repository, '--' + args.visibility, '--source', str(stage),
                 '--remote', 'origin', '--push', '--description', manifest['description']], stage, capture=False)
            print(f'Repository created: https://github.com/{repository}', flush=True)
            run(['git', 'tag', 'v' + version], stage)
            try:
                run(['git', 'push', 'origin', 'v' + version], stage)
            except subprocess.CalledProcessError:
                print('Repository and main branch were published, but the version tag push failed. Inspect the repository; do not rerun creation.', file=sys.stderr)
                return 3
        print(f'Share: https://github.com/{repository}\nSkill path: plugins/{name}/skills/{name}\nThe public ChatGPT directory has NOT been submitted or published by this command.')
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
