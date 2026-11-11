#!/usr/bin/env python3
"""Read-only vault checks. Python 3.9+, PyYAML; no app or network access."""
import argparse
import html
from collections import Counter, defaultdict
from datetime import date
import json
import os
from pathlib import Path
import posixpath
import re
import sys
from urllib.parse import unquote, urlsplit

import yaml


def visible(text, keep_inline=False):
    """Remove examples/comments, retaining newlines for locations."""
    text = re.sub(r'\A---\r?\n.*?\r?\n---(?:\r?\n|$)', '', text, flags=re.S)
    text = re.sub(r'<!--.*?-->|%%.*?%%', lambda m: '\n' * m[0].count('\n'), text, flags=re.S)
    lines, fence = [], None
    for line in text.splitlines():
        match = re.match(r'^\s*(`{3,}|~{3,})', line)
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            lines.append('')
        elif fence or line.startswith(('    ', '\t')):
            lines.append('')
        else:
            lines.append(line if keep_inline else re.sub(r'(`+).*?\1', '', line))
    return '\n'.join(lines)


def metadata(text):
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    data = yaml.safe_load(match[1]) if match else {}
    if not isinstance(data, dict):
        raise ValueError('Frontmatter must be a mapping')
    return data


def links(text):
    text = visible(text)
    found = [('wiki', m[1].replace('\\|', '|').split('|', 1)[0]) for m in re.finditer(r'!?\[\[([^\]\n]+)\]\]', text)]
    # Angle destinations, balanced parentheses (e.g. file (old).md), optional titles.
    for m in re.finditer(r'(?<!!)\[[^\]\n]*\]\(|!\[[^\]\n]*\]\(', text):
        start = m.end()
        if text[start:start + 1] == '<':
            end = text.find('>', start)
            if end >= 0:
                found.append(('markdown', text[start + 1:end]))
            continue
        depth, end = 1, start
        while end < len(text) and depth:
            if text[end] == '\\':
                end += 2
                continue
            if text[end] == '(':
                depth += 1
            elif text[end] == ')':
                depth -= 1
            end += 1
        if depth == 0:
            dest = re.split(r'\s+["\']', text[start:end - 1], maxsplit=1)[0]
            found.append(('markdown', re.sub(r'\\([()])', r'\1', dest)))
    definitions = {m[1].casefold(): m[2] or m[3] for m in re.finditer(
        r'^\s*\[([^\]]+)\]:\s*(?:<([^>]+)>|(\S+))', text, re.M)}
    for m in re.finditer(r'!?\[([^\]\n]+)\]\[([^\]\n]*)\]', text):
        key = (m[2] or m[1]).casefold()
        if key in definitions:
            found.append(('markdown', definitions[key]))
    return found


def anchor_exists(text, anchor):
    text = visible(text, keep_inline=True)
    if anchor.startswith('^'):
        return bool(re.search(r'\^' + re.escape(anchor[1:]) + r'(?:\s|$)', text))
    headings = re.findall(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*$', text, re.M)
    headings += re.findall(r'^([^\n]+)\n(?:={3,}|-{3,})\s*$', text, re.M)
    for heading in headings:
        plain = re.sub(r'[*_~`]', '', heading)
        slug = re.sub(r'[^\w\-\s]', '', plain.lower()).replace(' ', '-')
        if anchor == heading or anchor == plain or anchor == slug:
            return True
    return False


GROUPS = {
    'formal': 'Current notes',
    'history': 'Archived or superseded notes',
    'local': 'External local paths',
    'parse': 'Parsing needs review',
}


def document_scope(path, meta):
    parts = Path(path).parts
    if (any(p.casefold() in ('archive', 'archives', 'corpus', 'evidence') for p in parts)
            or meta.get('status') in ('historical', 'superseded')):
        return 'history'
    return 'formal'


def issue_group(code, scope):
    if code in ('ambiguous-link', 'local-location-syntax', 'local-link-syntax'):
        return 'parse'
    if code.startswith('local-'):
        return 'local'
    return scope


def scan(root, local_root=None, today=None, projects_dir=None, inbox_dir=None, exclude=None):
    root = Path(root).resolve()
    local_root = Path(local_root).resolve() if local_root else None
    today = today or date.today()
    excluded = sorted(set(relative_directory(p) for p in (exclude or [])))

    def is_excluded(path):
        return any(path == p or path.startswith(p + '/') for p in excluded)

    texts, all_files = {}, set()
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith('.') and not Path(directory, d).is_symlink()
                   and not is_excluded(Path(directory, d).relative_to(root).as_posix())]
        for name in dirs:
            all_files.add(Path(directory, name).relative_to(root).as_posix())
        for name in names:
            path = Path(directory, name)
            if name.startswith('.') or path.is_symlink() or not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if is_excluded(rel):
                continue
            all_files.add(rel)
            if path.suffix == '.md' and not ('/templates/' in '/' + rel and path.name.endswith('-template.md')):
                texts[rel] = path.read_text(encoding='utf-8')
    issues, ids = [], defaultdict(list)

    scopes = {}

    def add(path, code, target, detail, level='error'):
        scope = scopes.get(path, document_scope(path, {}))
        issues.append(dict(path=path, code=code, target=target, detail=detail, level=level,
                           document_scope=scope, group=issue_group(code, scope)))

    def check_local(path, raw, local, ambiguous=False):
        if ambiguous:
            add(path, 'local-link-syntax', raw,
                'A local link without file:// may be interpreted as a vault link. '
                'Confirm the target before using an encoded absolute file:/// URI; preserve historical sources.', 'warning')
        # Resolve symlinks before checking device scope; never probe their target
        # for existence when it is outside the explicitly selected local root.
        local = local.resolve()
        if re.search(r':\d+(?::\d+)?$', local.name):
            add(path, 'local-location-syntax', raw,
                'Contains file:line syntax; not treated as a literal missing filename or an app-tested location.', 'warning')
        elif local_root and (local == local_root or local_root in local.parents):
            if not local.exists():
                add(path, 'local-missing', raw, 'Target does not exist within the explicitly selected local scope.')
        else:
            add(path, 'local-unverified', raw, 'Not checked outside the selected device scope; --local-root explicitly opts in.', 'info')

    for path, text in texts.items():
        try:
            meta = metadata(text)
        except (yaml.YAMLError, ValueError) as exc:
            add(path, 'frontmatter', '', 'Invalid YAML frontmatter; check quoting, indentation and field types.')
            meta = {}
        scopes[path] = document_scope(path, meta)
        canonical = bool(projects_dir and re.fullmatch(re.escape(projects_dir.rstrip('/')) + r'/[^/]+/README\.md', path))
        if canonical and meta.get('type') != 'project-alias':
            for key in ('title', 'type', 'status', 'project', 'project_id', 'project_status', 'summary_as_of', 'updated'):
                if not meta.get(key):
                    add(path, 'required', key, 'Optional project-index profile is missing a required field.')
            if meta.get('type') != 'project-index':
                add(path, 'project-type', 'type', 'Project index type must be project-index; aliases use project-alias.')
            pid = meta.get('project_id')
            if pid:
                if not isinstance(pid, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', pid):
                    add(path, 'project-id', str(pid), 'project_id must use lowercase letters, digits and hyphens.')
                ids[str(pid)].append(path)
            if meta.get('project_status') not in ('active', 'planning', 'paused', 'completed', 'archived'):
                add(path, 'project-status', str(meta.get('project_status')), 'Unknown project_status for the optional project-index profile.')
            for key in ('summary_as_of', 'updated'):
                try:
                    date.fromisoformat(str(meta.get(key)))
                except ValueError:
                    add(path, 'date', key, 'Expected an ISO date (YYYY-MM-DD); record actual source dates.')
        if inbox_dir and path.startswith(inbox_dir.rstrip('/') + '/') and Path(path).name != 'README.md':
            try:
                age = (today - date.fromisoformat(Path(path).stem[:10])).days
                detail = f'Inbox note is {age} days old' + ('; more than 7 days' if age > 7 else '')
            except ValueError:
                detail = 'Inbox note has no readable date prefix'
            add(path, 'candidate', '', detail, 'warning')
        allowed = meta.get('intentional_missing_links', {})
        if not isinstance(allowed, dict) or any(not isinstance(v, str) or not v.strip() for v in allowed.values()):
            add(path, 'exceptions', '', 'intentional_missing_links must map each target to a non-empty reason.')
            allowed = {}
        for kind, raw in set(links(text)):
            if kind == 'markdown' and raw.lower().startswith('file:'):
                try:
                    uri = urlsplit(raw)
                    local_path = unquote(uri.path)
                    if not local_path.startswith('/') or '\x00' in local_path or uri.query:
                        raise ValueError('unsupported file URI')
                except ValueError:
                    add(path, 'local-link-syntax', raw,
                        'Invalid file URI or unsupported query; use an encoded absolute file:/// URI.', 'warning')
                    continue
                if uri.netloc.lower() not in ('', 'localhost') or local_path.startswith('//'):
                    add(path, 'local-unverified', raw,
                        'Remote file URI or network location; not connected, mounted or checked.', 'info')
                else:
                    check_local(path, raw, Path(local_path))
                continue
            if re.match(r'^[a-zA-Z][\w+.-]*:', raw) or raw.startswith('//'):
                continue
            target, _, anchor = raw.partition('#')
            target, anchor = unquote(target), unquote(anchor)
            if kind == 'markdown' and target.startswith('/'):
                check_local(path, raw, Path(target), ambiguous=True)
                continue
            def variants(value):
                return [value] if value.endswith('.md') else [value + '.md', value]
            relative = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
            if kind == 'markdown' and (relative == '..' or relative.startswith('../')):
                check_local(path, raw, root / relative, ambiguous=True)
                continue
            possible = [relative] if kind == 'markdown' else [relative, target.lstrip('/')]
            if target and any(is_excluded(p) or is_excluded(p + '.md') for p in possible):
                add(path, 'excluded-target', raw, 'Target is excluded; contents and existence were not checked.', 'info')
                continue
            candidates = []
            if not target:
                candidates = [path]
            elif kind == 'markdown':
                candidates = [p for p in variants(relative) if p in all_files]
            else:
                for candidate in (relative, target.lstrip('/')):
                    candidates = [p for p in variants(candidate) if p in all_files]
                    if candidates:
                        break
                if not candidates and not target.startswith(('.', '/')):
                    candidates = [p for p in all_files if any(p == v or p.endswith('/' + v) for v in variants(target))]
            if not candidates:
                if raw in allowed:
                    add(path, 'intentional-missing', raw, allowed[raw], 'info')
                else:
                    add(path, 'missing-link', raw, 'Target not found; check the link or record a reason in intentional_missing_links.')
            elif len(candidates) > 1:
                add(path, 'ambiguous-link', raw, 'Multiple possible targets; use an unambiguous vault-relative path.', 'warning')
            elif anchor and candidates[0] in texts and not anchor_exists(texts[candidates[0]], anchor):
                add(path, 'missing-anchor', raw, 'Page exists but anchor was not found; check its heading or block ID.')
    for pid, paths in ids.items():
        if len(paths) > 1:
            for path in paths:
                add(path, 'duplicate-id', pid, 'Duplicate project_id: ' + ', '.join(paths))
    issues.sort(key=lambda item: (item['path'], item['code'], item['target']))
    return {'schema': 1, 'vault': '.', 'redacted': False, 'notes': len(texts),
            'projects': sum(map(len, ids.values())), 'excluded': excluded, 'issues': issues}


def identity(item):
    return item['path'], item['code'], item['target']


def classify(report, baseline):
    old = {identity(item) for item in baseline['issues']}
    for item in report['issues']:
        item['age'] = 'historical' if identity(item) in old else 'new'
    return report


def redact_report(report):
    """Remove note names, link targets and free-text details from a report copy."""
    result = json.loads(json.dumps(report, default=str))
    names = {name: f'note-{i + 1:04d}' for i, name in enumerate(sorted({x['path'] for x in result['issues']}))}
    for issue in result['issues']:
        issue['path'] = names[issue['path']]
        issue['target'] = '[redacted]'
        issue['detail'] = 'See the private local report for details.'
    result['vault'] = '.'
    result['redacted'] = True
    result['excluded'] = ['[redacted]'] * len(result.get('excluded', []))
    return result


def summary_report(report):
    """Keep aggregate counts only; this output is never a baseline."""
    return {k: report[k] for k in ('schema', 'notes', 'projects', 'counts', 'group_counts')}


def markdown_report(report, language='en'):
    zh = language == 'zh-TW'
    def cell(value):
        text = html.escape(str(value)).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')
        return re.sub(r'([\\`*_{\[\]~])', r'\\\1', text)
    title = 'Obsidian 健康檢查報告' if zh else 'Obsidian health report'
    lines = ['# ' + title, '',
             (f"筆記：{report['notes']}；專案索引：{report['projects']}" if zh else
              f"Notes: {report['notes']}; project indexes: {report['projects']}"), '']
    lines += ['## ' + ('問題統計' if zh else 'Issue counts'), '']
    lines += [f'- {cell(k)}: {v}' for k, v in sorted(report.get('counts', {}).items())] or [('- 無問題。' if zh else '- No issues.')]
    if 'issues' not in report:
        lines += ['', '僅含統計，不包含筆記名稱與問題細節。' if zh else 'Statistics only; note names and issue details are omitted.']
    elif report['issues']:
        lines += ['', '## ' + ('問題與處理順序' if zh else 'Issues in suggested review order'), '',
                  '先查看新增錯誤，再查看既有錯誤與提醒；歷史問題仍未解決。' if zh else
                  'Review new errors first, then historical errors and warnings. Historical issues remain unresolved.', '',
                  '| 嚴重度 | 狀態 | 筆記 | 類型 | 目標 | 說明 |' if zh else '| Level | Age | Note | Code | Target | Detail |',
                  '| --- | --- | --- | --- | --- | --- |']
        for item in sorted(report['issues'], key=lambda i: (i['level'] != 'error', i.get('age') == 'historical', i['path'], i['code'], i['target'])):
            lines.append('| ' + ' | '.join(cell(item.get(k, '')) for k in ('level', 'age', 'path', 'code', 'target', 'detail')) + ' |')
    lines += ['', '範圍：唯讀靜態檢查；未驗證外掛或 Obsidian 畫面。' if zh else
              'Scope: read-only static checks; plugins and the rendered Obsidian interface are not verified.']
    return '\n'.join(lines) + '\n'


def relative_directory(value):
    """Accept only a vault-relative directory for optional personal conventions."""
    value = value.replace('\\', '/').rstrip('/')
    if not value or value.startswith('/') or any(p in ('.', '..', '') for p in value.split('/')) or re.match(r'^[A-Za-z]:', value):
        raise argparse.ArgumentTypeError('Use a vault-relative directory without parent traversal.')
    return value.rstrip('/')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', type=Path, required=True, help='Explicit local vault directory; no discovery or account access.')
    parser.add_argument('--local-root', type=Path, help='Opt in to checking external local links below this absolute directory.')
    parser.add_argument('--baseline', type=Path, help='Previous private JSON report; matching issues are marked historical.')
    output = parser.add_mutually_exclusive_group()
    output.add_argument('--json', action='store_true', help='Write JSON to stdout; redirect private reports outside the vault.')
    output.add_argument('--markdown', action='store_true', help='Write a Markdown report to stdout.')
    parser.add_argument('--language', choices=('en', 'zh-TW'), default='en', help='Markdown report language; issue codes and details remain English.')
    parser.add_argument('--exclude', action='append', type=relative_directory, default=[], help='Skip this vault-relative file or directory; repeat as needed. No glob patterns.')
    parser.add_argument('--summary-only', action='store_true', help='Output aggregate counts only; cannot be used as a baseline.')
    parser.add_argument('--projects-dir', type=relative_directory, help='Opt in to project-index metadata checks in this vault-relative folder.')
    parser.add_argument('--inbox-dir', type=relative_directory, help='Opt in to dated-note age warnings in this vault-relative folder.')
    parser.add_argument('--redact', action='store_true', help='Omit note names, raw link targets and free-text issue details from stdout.')
    args = parser.parse_args(argv)
    if not args.vault.is_dir():
        parser.error('--vault must be an existing directory.')
    if args.local_root and not args.local_root.is_absolute():
        parser.error('--local-root must be absolute.')
    try:
        report = scan(args.vault, args.local_root, projects_dir=args.projects_dir, inbox_dir=args.inbox_dir, exclude=args.exclude)
    except (OSError, UnicodeError, RuntimeError):
        parser.error('Cannot read the selected vault safely. Check local permissions and file encodings; paths are omitted.')
    if args.baseline:
        try:
            baseline = json.loads(args.baseline.read_text())
        except (OSError, UnicodeError, ValueError):
            parser.error('Cannot read the baseline JSON. Paths and content are omitted.')
        if not isinstance(baseline, dict) or baseline.get('schema') != 1 or not isinstance(baseline.get('issues'), list):
            parser.error('Unsupported baseline report.')
        if baseline.get('excluded', []) != report['excluded']:
            parser.error('Baseline exclusions differ from this scan; use matching scan options.')
        if baseline.get('redacted') or any(not isinstance(i, dict) or not all(isinstance(i.get(k), str) for k in ('path', 'code', 'target')) for i in baseline['issues']):
            parser.error('Baseline must be an unredacted local report with valid issue identities.')
        classify(report, baseline)
    else:
        for issue in report['issues']:
            issue['age'] = 'unclassified'
    counts = Counter(i['age'] + ':' + i['level'] for i in report['issues'])
    report['counts'] = dict(counts)
    report['group_counts'] = dict(Counter(i['group'] for i in report['issues']))
    exit_code = int(any(i['level'] == 'error' and i['age'] != 'historical' for i in report['issues']))
    if args.redact:
        report = redact_report(report)
    if args.summary_only:
        report = summary_report(report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.markdown:
        print(markdown_report(report, args.language), end='')
    elif args.summary_only:
        print(f"Notes {report['notes']}; project indexes {report['projects']}; {dict(counts)}")
    else:
        print(f"Notes {report['notes']}; project indexes {report['projects']}；{dict(counts)}")
        for group, label in GROUPS.items():
            items = [i for i in report['issues'] if i['group'] == group]
            print(f"\n{label}：{len(items)}")
            for item in items:
                print(f"{item['age']} {item['level']} [{item['code']}] {item['path']} → {item['target']}：{item['detail']}")
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
