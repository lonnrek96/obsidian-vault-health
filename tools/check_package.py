#!/usr/bin/env python3
"""Validate Skill metadata and scan tracked public files for common secrets.

Reports paths/categories only, never matched secrets. This is a bounded pattern
scan, not a guarantee of anonymous content or a vault-scanning tool.
"""
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'private-key': r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'access-token': r'(?:sk-proj-|sk-ant-|ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{16,}|AKIA[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{30,}',
    'credential-assignment': r'(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*[\x27\x22][A-Za-z0-9_+/=-]{20,}',
    'private-home-path': r'/(?:Users|home)/[^\s\x27\x22<>]+|[A-Z]:\\Users\\',
    'email-address': r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
}


def findings(path, content):
    return [(path, n, kind) for n, line in enumerate(content.splitlines(), 1)
            for kind, pattern in PATTERNS.items() if re.search(pattern, line)]


def main():
    skill = ROOT / 'skills/obsidian-vault-health'
    text = (skill / 'SKILL.md').read_text(encoding='utf-8')
    assert text.startswith('---\n'), 'Missing frontmatter'
    meta = yaml.safe_load(text.split('---', 2)[1])
    assert meta['name'] == skill.name and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', meta['name'])
    assert 0 < len(meta['description']) <= 1024
    assert len(meta['name']) <= 64
    for ref in re.findall(r'\]\(([^)]+)\)', text):
        if not ref.startswith('https://'):
            target = (skill / ref).resolve()
            assert skill in target.parents and target.is_file(), 'Broken Skill reference'
    raw = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT)
    errors = []
    for name in sorted(set(raw.decode('utf-8').split('\0')) - {''}):
        p = ROOT / name
        if p.is_symlink():
            errors.append((name, 0, 'symbolic-link'))
            continue
        try:
            content = p.read_text(encoding='utf-8')
        except UnicodeError:
            errors.append((name, 0, 'unexpected-binary'))
            continue
        errors.extend(findings(name, content))
    for path, line, category in errors:
        print(f'{path}:{line}: {category}')
    if not errors:
        print('Skill format and public-file pattern checks passed.')
    return bool(errors)


if __name__ == '__main__':
    sys.exit(main())
