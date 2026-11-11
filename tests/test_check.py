import os
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/obsidian-vault-health/scripts"))
import check


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, path, body):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
        return target

    def issues(self, **kw):
        return check.scan(self.root, projects_dir='Projects', inbox_dir='Inbox', **kw)['issues']

    def test_links_paths_aliases_anchors_and_examples(self):
        self.put('folder/target.md', '# 中文標題\n## Hello World\n## `Code` Title\nparagraph ^block\n')
        self.put('folder/file (old).md', '# Old\n')
        self.put('folder/v1.0.md', '# Version\n')
        self.put('folder/source.md', '''[[folder/target#中文標題|別名]] [[./target#^block]] [[target#hello-world]]
| [[folder/target\\|表格別名]] | [[v1.0]] | [[target#Code Title]] |
[target](target.md#hello-world) [old](<file (old).md>) [old](file%20(old).md)
[reference][ref]
[ref]: target.md#中文標題
`[[fake-inline]]`
<!-- [[fake-comment]] -->
~~~md
[[fake-fence]]
~~~
    [[indented-example]]
''')
        self.assertEqual(self.issues(), [])

    def test_wrong_paths_and_anchor(self):
        self.put('other/target.md', '# Real')
        self.put('folder/source.md', '[[other/target#Absent]] [wrong relative](target.md) [[missing]]')
        self.assertCountEqual([i['code'] for i in self.issues()], ['missing-anchor', 'missing-link', 'missing-link'])

    def test_ambiguous_wiki_does_not_choose_random(self):
        self.put('a/same.md', '# A')
        self.put('b/same.md', '# B')
        self.put('source.md', '[[same]]')
        self.assertEqual(self.issues()[0]['code'], 'ambiguous-link')

    def test_metadata_duplicate_and_alias(self):
        body = '''---
title: Test
type: project-index
status: active
project: Test
project_id: same
project_status: planning
summary_as_of: 2026-10-23
updated: 2026-10-23
---
'''
        self.put('Projects/a/README.md', body)
        self.put('Projects/b/README.md', body)
        self.put('Projects/alias/README.md', '---\ntype: project-alias\nproject_id: same\n---\n')
        self.assertEqual([i['code'] for i in self.issues()], ['duplicate-id', 'duplicate-id'])
        self.put('Projects/b/README.md', body.replace('project_id: same\n', ''))
        self.assertEqual([i['code'] for i in self.issues()], ['required'])

    def test_intentional_missing_requires_reason(self):
        self.put('note.md', '---\nintentional_missing_links:\n  future: 等待下一批來源\n---\n[[future]] [[mistake]]')
        self.assertCountEqual([i['code'] for i in self.issues()], ['intentional-missing', 'missing-link'])
        self.put('note.md', '---\nintentional_missing_links: [future]\n---\n[[future]]')
        self.assertCountEqual([i['code'] for i in self.issues()], ['exceptions', 'missing-link'])

    def test_local_paths_only_on_selected_device(self):
        self.put('note.md', f'[file](<{self.root}/missing>)')
        self.assertCountEqual([i['code'] for i in self.issues()], ['local-link-syntax', 'local-unverified'])
        self.assertCountEqual([i['code'] for i in self.issues(local_root=self.root)],
                              ['local-link-syntax', 'local-missing'])

    def test_existing_absolute_link_warns_but_file_uri_is_checked(self):
        filename = 'repo/中文 note #1' + ('?' if os.name != 'nt' else '') + '.md'
        target = self.put(filename, '# Real')
        self.put('vault/Home.md', f'[old](<{target.as_posix().replace("#", "%23").replace("?", "%3F")}>)\n'
                 f'[fixed](<{target.as_uri()}#heading>)\n'
                 f'[missing](<{(self.root / "repo/missing.md").as_uri()}>)')
        before = {p: p.read_bytes() for p in self.root.rglob('*.md')}
        issues = check.scan(self.root / 'vault', local_root=self.root)['issues']
        self.assertCountEqual([i['code'] for i in issues], ['local-link-syntax', 'local-missing'])
        self.assertEqual(next(i['target'] for i in issues if i['code'] == 'local-missing'),
                         (self.root / 'repo/missing.md').as_uri())
        syntax = next(i for i in issues if i['code'] == 'local-link-syntax')
        self.assertEqual((syntax['level'], syntax['group'], syntax['document_scope']),
                         ('warning', 'parse', 'formal'))
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob('*.md')}, before)

    def test_file_uri_localhost_encoding_and_device_scope(self):
        target = self.put('repo/中文 note.md', 'body')
        self.put('vault/note.md', f'[local](<{target.as_uri().replace("file:///", "file://localhost/")}>)')
        self.assertEqual(check.scan(self.root / 'vault', local_root=self.root)['issues'], [])
        with patch.object(Path, 'exists', side_effect=AssertionError('outside selected device')):
            issues = check.scan(self.root / 'vault')['issues']
        self.assertEqual([i['code'] for i in issues], ['local-unverified'])

    def test_file_uri_remote_invalid_and_symlink_do_not_probe(self):
        self.put('vault/note.md', '[remote](file://server/share/note.md) '
                 '[relative](file:relative.md) [invalid](<file://[broken/path>) '
                 '[zero](file:///tmp/a%00b) [web](https://example.com/file)')
        with patch.object(Path, 'exists', side_effect=AssertionError('unexpected probe')):
            issues = check.scan(self.root / 'vault', local_root=self.root)['issues']
        self.assertCountEqual([i['code'] for i in issues],
                              ['local-unverified', 'local-link-syntax', 'local-link-syntax', 'local-link-syntax'])
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        (self.root / 'outside').symlink_to(external.name, target_is_directory=True)
        self.put('vault/note.md', f'[link](<{(self.root / "outside/missing.md").as_uri()}>)')
        with patch.object(Path, 'exists', side_effect=AssertionError('symlink escaped scope')):
            issues = check.scan(self.root / 'vault', local_root=self.root)['issues']
        self.assertEqual([i['code'] for i in issues], ['local-unverified'])

    def test_external_link_reference_history_and_examples(self):
        self.put('repo/task.md', '# Task')
        body = '[task][ref]\n[ref]: ../../repo/task.md\n' + \
               '`[example](/example/task.md)`\n```md\n[x](file:///missing)\n```\n'
        self.put('vault/Archive/raw.md', body)
        report = check.scan(self.root / 'vault', local_root=self.root)
        self.assertEqual([i['code'] for i in report['issues']], ['local-link-syntax'])
        self.assertEqual(report['issues'][0]['document_scope'], 'history')
        old = check.classify(report, {'issues': []})['issues'][0]
        self.assertEqual(old['age'], 'new')
        self.assertEqual(check.classify(check.scan(self.root / 'vault', local_root=self.root),
                                       report)['issues'][0]['age'], 'historical')

    def test_candidate_and_historical_classification(self):
        self.put('Inbox/2026-10-01.md', '[[old]]')
        baseline = check.scan(self.root, inbox_dir="Inbox", today=date(2026, 10, 23))
        self.put('new.md', '[[new-missing]]')
        report = check.classify(check.scan(self.root, inbox_dir="Inbox", today=date(2026, 10, 23)), baseline)
        self.assertEqual(next(i for i in report['issues'] if i['path'] == 'new.md')['age'], 'new')
        self.assertTrue(all(i['age'] == 'historical' for i in report['issues'] if i['path'] != 'new.md'))
        self.assertIn('22 days', next(i for i in report['issues'] if i['code'] == 'candidate')['detail'])

    def test_external_relative_markdown_links_respect_device_scope(self):
        self.put('vault/note.md', '[present](../repo/present.md#heading) [missing](../repo/missing.md)')
        self.put('repo/present.md', '# heading')
        report = check.scan(self.root / 'vault', local_root=self.root)
        self.assertEqual([(i['code'], i['target']) for i in report['issues']],
                         [('local-link-syntax', '../repo/missing.md'),
                          ('local-link-syntax', '../repo/present.md#heading'),
                          ('local-missing', '../repo/missing.md')])
        unverified = check.scan(self.root / 'vault')['issues']
        self.assertCountEqual([i['code'] for i in unverified],
                              ['local-unverified'] * 2 + ['local-link-syntax'] * 2)

    def test_external_symlink_does_not_escape_local_scope(self):
        self.put('vault/note.md', '[link](../outside/missing.md)')
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        (self.root / 'outside').symlink_to(external.name, target_is_directory=True)
        with patch.object(Path, 'exists', side_effect=AssertionError('unexpected existence probe')):
            issues = check.scan(self.root / 'vault', local_root=self.root)['issues']
        self.assertCountEqual([i['code'] for i in issues], ['local-link-syntax', 'local-unverified'])

    def test_relative_internal_link_is_still_checked(self):
        self.put('a/note.md', '[good](../b/target.md#Real) [bad](../b/target.md#Missing)')
        self.put('b/target.md', '# Real')
        self.assertEqual([i['code'] for i in self.issues()], ['missing-anchor'])

    def test_location_suffix_is_not_a_missing_filename(self):
        self.put('note.md', f'[line](<{self.root}/source.md:2527>)')
        issue = next(i for i in self.issues(local_root=self.root) if i['code'] == 'local-location-syntax')
        self.assertEqual(issue['code'], 'local-location-syntax')
        self.assertEqual(issue['group'], 'parse')

    def test_groups_are_independent_of_baseline_age_and_severity(self):
        self.put('current.md', '[[missing-current]] [[same]]')
        self.put('Archive/raw.md', '[[missing-history]]')
        self.put('old.md', '---\nstatus: superseded\n---\n[[old-target]]')
        self.put('a/same.md', '# A')
        self.put('b/same.md', '# B')
        report = check.classify(check.scan(self.root), {'issues': []})
        issues = report['issues']
        self.assertEqual({i['group'] for i in issues}, {'formal', 'history', 'parse'})
        self.assertTrue(all(i['age'] == 'new' for i in issues))
        self.assertEqual(next(i for i in issues if i['path'] == 'old.md')['level'], 'error')

    def test_scan_does_not_write_or_follow_symlinks(self):
        self.put('note.md', '[[missing]]')
        self.put('templates/example-template.md', '{{VALUE:title}} [[example]]')
        def hashes():
            return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        before = hashes()
        self.issues()
        self.assertEqual(hashes(), before)
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        (self.root / 'outside').symlink_to(external.name, target_is_directory=True)
        self.assertEqual(len(self.issues()), 1)
