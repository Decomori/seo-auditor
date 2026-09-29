#!/usr/bin/env python3
"""Install one local skill OR register one plugin without replacing other entries."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def package() -> tuple[str, Path]:
    catalog = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text('utf-8'))
    entries = catalog.get('plugins', [])
    if len(entries) != 1:
        raise ValueError('This installer accepts exactly one independent plugin.')
    entry = entries[0]
    name = entry['name']
    import re
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
        raise ValueError('Invalid package name.')
    source = (ROOT / entry['source']['path']).resolve()
    if not source.is_relative_to(ROOT) or not source.is_dir():
        raise ValueError('Plugin source escapes the repository or is missing.')
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('Symlinked package content is not supported.')
    return name, source


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.writing-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.write('\n')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def safe_path(path: Path, home: Path) -> Path:
    # Reject pre-existing symlink components so another project cannot redirect writes.
    relative = path.relative_to(home)
    current = home
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f'Refusing symlinked installation path: {current}')
    return path


@contextmanager
def locked(home: Path):
    folder = safe_path(home / '.agents', home)
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / '.independent-skill-install.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def load_catalog(path: Path) -> dict:
    if not path.exists():
        return {'name': 'personal-plugins', 'interface': {'displayName': 'Personal plugins'}, 'plugins': []}
    data = json.loads(path.read_text('utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('plugins'), list):
        raise ValueError('Existing marketplace format is invalid; no settings changed.')
    return data


def act(args: argparse.Namespace) -> None:
    name, plugin = package()
    home = Path(args.home).expanduser().resolve() if args.home else Path.home().resolve()
    destination = home / ('.agents/skills' if args.mode == 'skill' else '.codex/plugins') / name
    source = plugin / 'skills' / name if args.mode == 'skill' else plugin
    catalog_path = home / '.agents/plugins/marketplace.json'
    for path in (destination, catalog_path):
        safe_path(path, home)
    receipt_name = '.independent-skill-receipt.json'
    receipt = destination / receipt_name
    if args.action == 'status':
        print(json.dumps({'package': name, 'mode': args.mode, 'exists': destination.exists(),
                          'managed': receipt.exists(), 'path': str(destination)}, ensure_ascii=False, indent=2))
        return
    if args.action == 'uninstall' and not args.confirm:
        raise ValueError('Uninstall requires --confirm. Only this package will be removed.')
    if not home.is_dir():
        raise ValueError('Home directory must already exist.')
    with locked(home):
        catalog = load_catalog(catalog_path) if args.mode == 'plugin' else None
        expected = './.codex/plugins/' + name
        existing_entries = [e for e in catalog['plugins'] if e.get('name') == name] if catalog else []
        if len(existing_entries) > 1:
            raise ValueError('Duplicate marketplace entries: resolve manually before continuing.')
        if existing_entries and existing_entries[0].get('source') != {'source': 'local', 'path': expected}:
            raise ValueError('An unrelated same-name marketplace entry exists. No changes made.')
        if args.action == 'uninstall':
            if not receipt.exists():
                raise ValueError('Refusing to remove a directory not installed by this helper.')
            info = json.loads(receipt.read_text('utf-8'))
            if info.get('package') != name or info.get('mode') != args.mode:
                raise ValueError('Installation receipt mismatch.')
            if catalog:
                catalog['plugins'] = [e for e in catalog['plugins'] if e.get('name') != name]
                atomic_json(catalog_path, catalog)
            shutil.rmtree(destination)
            print(f'Removed only {name}: {destination}. Restart the app. Backups were kept.')
            return
        if destination.exists() and not args.replace:
            raise ValueError('Already exists. Review local changes, then use --replace to update with backup.')
        if destination.exists() and not receipt.exists():
            raise ValueError('Refusing to replace an unmanaged same-name directory, even with --replace.')
        if destination.exists():
            info = json.loads(receipt.read_text('utf-8'))
            if info.get('package') != name or info.get('mode') != args.mode:
                raise ValueError('Installation receipt mismatch.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.' + name + '-stage-', dir=destination.parent))
        backup = None
        installed_new = False
        try:
            shutil.copytree(source, stage, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            version = json.loads((plugin / '.codex-plugin/plugin.json').read_text('utf-8'))['version']
            atomic_json(stage / receipt_name, {'package': name, 'mode': args.mode, 'version': version})
            if destination.exists():
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                # Put backups outside discovery directories to avoid duplicate skill registration.
                backup_root = safe_path(home / '.agents/independent-skill-backups', home)
                backup_root.mkdir(parents=True, exist_ok=True)
                backup = backup_root / f'{name}-{args.mode}-{stamp}'
                destination.rename(backup)
            stage.rename(destination)
            installed_new = True
            if catalog is not None:
                catalog['plugins'] = [e for e in catalog['plugins'] if e.get('name') != name]
                catalog['plugins'].append({'name': name, 'source': {'source': 'local', 'path': expected},
                                           'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
                                           'category': 'Productivity'})
                atomic_json(catalog_path, catalog)
        except Exception:
            if installed_new and destination.exists():
                shutil.rmtree(destination)
            if backup is not None and backup.exists():
                backup.rename(destination)
            raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        print(f'Installed files: {destination}')
        if backup:
            print(f'Previous files backed up: {backup}')
        if args.mode == 'plugin':
            print('Registered in the personal marketplace. Restart the desktop app, then install/enable this plugin in Plugins. This helper does not change app enablement or permissions.')
        else:
            print('Restart/start a new session if the skill does not appear. Do not also enable its plugin copy.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'uninstall', 'status'])
    parser.add_argument('--mode', choices=['skill', 'plugin'], default='plugin')
    parser.add_argument('--home', help='Explicit OS home for testing or a separate local profile.')
    parser.add_argument('--replace', action='store_true', help='Update this managed package and back up previous files.')
    parser.add_argument('--confirm', action='store_true', help='Confirm removal of this package only.')
    try:
        act(parser.parse_args())
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
