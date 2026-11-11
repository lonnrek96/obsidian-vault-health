import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/obsidian-vault-health/scripts'))
import check


class PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.vault = self.root / 'vault'
        self.vault.mkdir()

    def put(self, path, text):
        p = self.vault / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = check.main(list(args))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_generic_vault_needs_no_private_layout_or_schema(self):
        self.put('Projects/example/README.md', '# A project with no custom properties')
        self.assertEqual(check.scan(self.vault)['issues'], [])
        self.assertTrue(check.scan(self.vault, projects_dir='Projects')['issues'])
        self.assertEqual(self.cli('--vault', str(self.vault), '--json')[0], 0)

    def test_explicit_vault_is_required(self):
        code, out, err = self.cli('--json')
        self.assertEqual(code, 2)
        self.assertIn('--vault', err)
        self.assertEqual(out, '')

    def test_default_report_omits_absolute_vault_root(self):
        self.put('Note.md', '[[Missing]]')
        report = check.scan(self.vault)
        self.assertEqual(report['vault'], '.')
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_redaction_removes_names_targets_and_free_text_without_mutating(self):
        self.put('Sensitive-name.md', '---\nintentional_missing_links:\n  Private-target: private-canary-detail\n---\n[[Private-target]]\n[file](file:///private-canary-root/item.md)')
        report = check.scan(self.vault)
        original = json.dumps(report)
        redacted = check.redact_report(report)
        serialized = json.dumps(redacted)
        for value in ['Sensitive-name', 'Private-target', 'private-canary-detail', 'private-canary-root', str(self.vault)]:
            self.assertNotIn(value, serialized)
        self.assertEqual(json.dumps(report), original)
        self.assertTrue(redacted['redacted'])
        self.assertEqual(len(redacted['issues']), len(report['issues']))

    def test_redacted_cli_preserves_failure_status(self):
        self.put('Private-note.md', '[[Private-missing]]')
        code, out, err = self.cli('--vault', str(self.vault), '--json', '--redact')
        self.assertEqual(code, 1)
        self.assertEqual(err, '')
        self.assertTrue(json.loads(out)['redacted'])
        self.assertNotIn('Private-note', out)
        self.assertNotIn('Private-missing', out)

    def test_redacted_baseline_is_rejected(self):
        self.put('Note.md', '[[Missing]]')
        baseline = self.root / 'baseline.json'
        baseline.write_text(json.dumps(check.redact_report(check.scan(self.vault))))
        self.assertEqual(self.cli('--vault', str(self.vault), '--baseline', str(baseline))[0], 2)

    def test_baseline_exits_on_new_errors_and_not_historical_ones(self):
        self.put('Old.md', '[[Old missing]]')
        baseline = self.root / 'baseline.json'
        baseline.write_text(json.dumps(check.scan(self.vault)))
        args = ('--vault', str(self.vault), '--baseline', str(baseline), '--json')
        self.assertEqual(self.cli(*args)[0], 0)
        self.put('New.md', '[[New missing]]')
        self.assertEqual(self.cli(*args)[0], 1)

    def test_hidden_files_and_symlinked_files_are_not_read(self):
        self.put('.hidden.md', '[[Hidden-missing]]')
        self.put('.settings/Note.md', '[[Hidden-directory-missing]]')
        outside = self.root / 'Outside.md'
        outside.write_text('[[Outside-missing]]')
        (self.vault / 'Linked.md').symlink_to(outside)
        self.put('Visible.md', '# Visible')
        self.assertEqual(check.scan(self.vault)['issues'], [])
        self.assertEqual(check.scan(self.vault)['notes'], 1)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO support required')
    def test_nonregular_markdown_file_is_not_opened(self):
        os.mkfifo(self.vault / 'Pipe.md')
        self.assertEqual(check.scan(self.vault)['notes'], 0)

    def test_scan_makes_no_network_connection(self):
        self.put('Note.md', '[web](https://example.com) [remote](file://server/share/note.md)')
        with patch('socket.socket', side_effect=AssertionError('Network access forbidden')):
            result = check.scan(self.vault)
        self.assertEqual([i['code'] for i in result['issues']], ['local-unverified'])

    def test_profile_paths_cannot_traverse_outside_vault(self):
        for value in ['../private', '/absolute', 'C:/private']:
            self.assertEqual(self.cli('--vault', str(self.vault), '--projects-dir', value)[0], 2)

    def test_read_error_omits_private_path_and_content(self):
        self.put('Private-name.md', '# Content')
        with patch.object(Path, 'read_text', side_effect=OSError('private-canary-error')):
            code, out, err = self.cli('--vault', str(self.vault), '--redact')
        self.assertEqual(code, 2)
        self.assertNotIn(str(self.vault), err)
        self.assertNotIn('private-canary-error', err)
        self.assertNotIn('Private-name', err)


if __name__ == '__main__':
    unittest.main()
