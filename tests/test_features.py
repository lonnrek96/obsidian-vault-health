import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/obsidian-vault-health/scripts'))
import check
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
spec = importlib.util.spec_from_file_location('package_check', ROOT / 'tools/check_package.py')
package_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_check)


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.vault = self.root / 'vault'
        self.vault.mkdir()

    def put(self, path, text):
        p = self.vault / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = check.main(['--vault', str(self.vault), *args])
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_excluded_tree_is_not_read_or_counted(self):
        self.put('Private/Secret.md', '[[Missing]]')
        self.put('PrivateOther/Visible.md', '# Visible')
        self.put('One.md', '[[HiddenMissing]]')
        original = Path.read_text
        def guarded(p, *args, **kwargs):
            self.assertNotIn('Private', p.parts)
            self.assertNotEqual(p.name, 'One.md')
            return original(p, *args, **kwargs)
        with patch.object(Path, 'read_text', guarded):
            report = check.scan(self.vault, exclude=['Private', 'One.md'])
        self.assertEqual(report['notes'], 1)
        self.assertEqual(report['issues'], [])

    def test_links_to_excluded_targets_are_unverified_not_missing(self):
        self.put('Start.md', '[[Private/Hidden]]\n[x](Private/Absent.md)')
        report = check.scan(self.vault, exclude=['Private'])
        self.assertEqual([i['code'] for i in report['issues']], ['excluded-target', 'excluded-target'])
        self.assertTrue(all(i['level'] == 'info' for i in report['issues']))

    def test_exclusion_cannot_hide_entire_root_or_escape(self):
        for value in ['.', '..', '../outside', '/absolute', 'C:/outside', 'Private/../Other']:
            self.assertEqual(self.cli('--exclude', value)[0], 2)

    def test_exclusions_accept_trailing_slash_and_windows_separators(self):
        self.put('Private/Nested/Note.md', '[[Missing]]')
        for value in ['Private/Nested/', 'Private\\Nested']:
            code, out, err = self.cli('--exclude', value, '--json')
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)['notes'], 0)
            self.assertEqual(err, '')

    def test_baseline_rejects_changed_exclusion_scope(self):
        baseline = self.root / 'before.json'
        baseline.write_text(json.dumps(check.scan(self.vault)))
        self.assertEqual(self.cli('--exclude', 'Private', '--baseline', str(baseline))[0], 2)

    def test_redaction_also_removes_exclusion_names(self):
        self.put('Note.md', '[[Missing]]')
        report = check.redact_report(check.scan(self.vault, exclude=['Secret-canary']))
        self.assertNotIn('Secret-canary', json.dumps(report))

    def test_summary_contains_only_aggregates_and_keeps_exit_code(self):
        self.put('Secret-canary.md', '[[Target-canary]]')
        code, out, err = self.cli('--json', '--summary-only', '--exclude', 'Folder-canary')
        self.assertEqual(code, 1)
        self.assertEqual(err, '')
        self.assertNotIn('canary', out)
        data = json.loads(out)
        self.assertEqual(set(data), {'schema', 'notes', 'projects', 'counts', 'group_counts'})
        self.assertEqual(data['counts'], {'unclassified:error': 1})
        baseline = self.root / 'summary.json'
        baseline.write_text(out)
        self.assertEqual(self.cli('--baseline', str(baseline))[0], 2)

    def test_markdown_languages_and_untrusted_text_escaping(self):
        self.put('Note.md', '[[Missing|alias]]')
        report = check.scan(self.vault)
        report['issues'][0]['target'] = '<script>alert(1)</script>|[click](https://example.com)\nInjected'
        for language, heading in [('en', 'Obsidian health report'), ('zh-TW', 'Obsidian 健康檢查報告')]:
            output = check.markdown_report(report, language)
            self.assertIn(heading, output)
            self.assertNotIn('<script>', output)
            self.assertNotIn('|[click]', output)
            self.assertIn('&#124;', output)
        code, output, err = self.cli('--markdown', '--language', 'zh-TW', '--redact')
        self.assertEqual(code, 1)
        self.assertIn('健康檢查', output)
        self.assertNotIn('Note.md', output)
        self.assertEqual(err, '')

    def test_empty_markdown_and_summary_markdown(self):
        code, output, err = self.cli('--markdown', '--summary-only')
        self.assertEqual(code, 0)
        self.assertIn('Statistics only', output)
        self.assertIn('No issues', output)
        self.assertEqual(err, '')

    def test_output_modes_are_mutually_exclusive(self):
        self.assertEqual(self.cli('--json', '--markdown')[0], 2)

    def test_install_both_and_run_real_installed_checker(self):
        destinations = installer.install(self.root, 'both', Path(sys.executable))
        self.put('Start.md', '[[Missing-canary]]')
        for dest in destinations:
            runtime = json.loads((dest / 'runtime.json').read_text())
            self.assertEqual(runtime['python'], str(Path(sys.executable).absolute()))
            proc = subprocess.run([runtime['python'], str(dest / 'scripts/check.py'), '--vault', str(self.vault), '--json'], capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['issues'][0]['code'], 'missing-link')

    def test_existing_install_prevents_partial_second_install(self):
        old = self.root / '.claude/skills/obsidian-vault-health'
        old.mkdir(parents=True)
        marker = old / 'keep.txt'
        marker.write_text('Keep this')
        with self.assertRaises(ValueError):
            installer.install(self.root, 'both', Path(sys.executable))
        self.assertEqual(marker.read_text(), 'Keep this')
        self.assertFalse((self.root / '.agents').exists())

    def test_existing_install_blocks_dependency_download(self):
        (self.root / '.agents/skills/obsidian-vault-health').mkdir(parents=True)
        env = self.root / 'new-env'
        with patch.object(installer.venv.EnvBuilder, 'create', side_effect=AssertionError('Should not create an environment')):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                installer.main(['--project', str(self.root), '--agent', 'codex', '--venv', str(env)])
        self.assertEqual(exc.exception.code, 2)
        self.assertFalse(env.exists())

    def test_public_scanner_detects_canary_without_printing_secret(self):
        token = 'ghp_' + 'A' * 32
        found = package_check.findings('example.txt', token)
        self.assertEqual(found, [('example.txt', 1, 'access-token')])
        self.assertNotIn(token, repr(found))
        self.assertEqual(package_check.findings('example.txt', 'No credentials here'), [])
        home = '/' + 'Users' + '/fictional-person/note.md'
        self.assertEqual(package_check.findings('example.txt', home), [('example.txt', 1, 'private-home-path')])

    def test_published_example_has_only_two_expected_errors(self):
        report = check.scan(ROOT / 'examples/vault')
        self.assertEqual(report['notes'], 2)
        self.assertCountEqual([i['code'] for i in report['issues']], ['missing-link', 'missing-anchor'])


if __name__ == '__main__':
    unittest.main()
