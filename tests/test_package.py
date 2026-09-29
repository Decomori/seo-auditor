from __future__ import annotations
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

manage = load('manage_test_module', ROOT / 'tools/manage.py')
validator = load('validate_test_module', ROOT / 'tools/validate_package.py')
publisher = load('publish_test_module', ROOT / 'tools/publish.py')
SLUG = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())['plugins'][0]['name']


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.home = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def act(self, action='install', mode='plugin', **kw):
        args = argparse.Namespace(action=action, mode=mode, home=str(self.home), replace=False, confirm=False)
        for key, value in kw.items(): setattr(args, key, value)
        with redirect_stdout(io.StringIO()): manage.act(args)
    def seed_catalog(self):
        path = self.home / '.agents/plugins/marketplace.json'; path.parent.mkdir(parents=True)
        unrelated = {'name':'unrelated-existing-plugin','source':{'source':'local','path':'./somewhere/else'},'custom':'keep'}
        path.write_text(json.dumps({'name':'my-existing-catalog','custom':'preserve-root','plugins':[unrelated]}))
        return path, unrelated
    def test_structure(self): self.assertEqual(validator.validate(ROOT), [])
    def test_exactly_one_skill(self):
        skills = list((ROOT / 'plugins').glob('*/skills/*/SKILL.md'))
        self.assertEqual(len(skills), 1)
    def test_install_preserves_other_settings(self):
        path, unrelated = self.seed_catalog(); self.act()
        data = json.loads(path.read_text()); self.assertIn(unrelated, data['plugins'])
        self.assertEqual(data['custom'],'preserve-root'); self.assertEqual(data['name'],'my-existing-catalog')
        self.assertTrue((self.home / '.codex/plugins' / SLUG / '.codex-plugin/plugin.json').exists())
    def test_skill_mode_is_standalone(self):
        self.act(mode='skill'); target=self.home/'.agents/skills'/SLUG
        self.assertTrue((target/'SKILL.md').exists()); self.assertTrue((target/'scripts').exists())
        self.assertFalse((self.home/'.codex').exists())
        self.assertFalse((self.home/'.agents/plugins/marketplace.json').exists())
    def test_existing_install_requires_replace(self):
        self.act()
        with self.assertRaises(ValueError): self.act()
    def test_update_backs_up_outside_discovery(self):
        self.act(); target=self.home/'.codex/plugins'/SLUG
        (target/'local-note.txt').write_text('keep in backup')
        self.act(replace=True)
        backups=list((self.home/'.agents/independent-skill-backups').glob('*'))
        self.assertEqual(len(backups),1); self.assertEqual((backups[0]/'local-note.txt').read_text(),'keep in backup')
        self.assertFalse((target/'local-note.txt').exists())
    def test_failed_copy_does_not_delete_existing(self):
        self.act(); target=self.home/'.codex/plugins'/SLUG
        marker=target/'existing.txt'; marker.write_text('must survive')
        with patch.object(manage.shutil,'copytree',side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError): self.act(replace=True)
        self.assertEqual(marker.read_text(),'must survive')
    def test_unmanaged_folder_refused(self):
        target=self.home/'.codex/plugins'/SLUG;target.mkdir(parents=True);(target/'client.txt').write_text('private')
        with self.assertRaises(ValueError): self.act(replace=True)
        self.assertEqual((target/'client.txt').read_text(),'private')
    def test_conflicting_catalog_refused(self):
        path,_=self.seed_catalog(); data=json.loads(path.read_text())
        data['plugins'].append({'name':SLUG,'source':{'source':'local','path':'./other-project'}});path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):self.act()
        self.assertFalse((self.home/'.codex/plugins'/SLUG).exists())
    def test_uninstall_only_own_plugin(self):
        path,unrelated=self.seed_catalog();self.act();self.act('uninstall',confirm=True)
        self.assertEqual(json.loads(path.read_text())['plugins'],[unrelated])
        self.assertFalse((self.home/'.codex/plugins'/SLUG).exists())
    def test_uninstall_needs_confirmation(self):
        self.act()
        with self.assertRaises(ValueError): self.act('uninstall')
    def test_lock_prevents_concurrent_install(self):
        d=self.home/'.agents';d.mkdir();(d/'.independent-skill-install.lock').write_text('123')
        with self.assertRaises(FileExistsError):self.act()
    def test_symlink_parent_refused(self):
        target=self.home/'outside';target.mkdir()
        try:(self.home/'.codex').symlink_to(target,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('Symlinks unavailable in this OS configuration')
        with self.assertRaises(ValueError):self.act()
    def test_publisher_excludes_runtime_data(self):
        (self.home/'README.md').write_text('readme');(self.home/'outputs').mkdir();(self.home/'outputs/private.txt').write_text('private')
        (self.home/'.env').write_text('private');paths=list(publisher.public_files(self.home))
        self.assertEqual(paths,[Path('README.md')])
    def test_publisher_rejects_secret(self):
        (self.home/'README.md').write_text('credential='+'ghp_'+'x'*40)
        with self.assertRaises(ValueError):list(publisher.public_files(self.home))
    def test_publisher_plan_is_offline(self):
        with patch('sys.argv',['publish.py','--plan']),patch.object(publisher,'run',side_effect=AssertionError('network not expected')):
            with redirect_stdout(io.StringIO()):self.assertEqual(publisher.main(),0)

if __name__ == '__main__': unittest.main()
