#!/usr/bin/env python3
"""Install project-local skills without overwriting an existing installation."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv

NAME = 'obsidian-vault-health'
SOURCE = Path(__file__).resolve().parent / 'skills' / NAME


def install(project, agent, python):
    project = Path(project).resolve()
    if not project.is_dir():
        raise ValueError('Project directory must already exist.')
    folders = ['.agents', '.claude'] if agent == 'both' else [('.agents' if agent == 'codex' else '.claude')]
    destinations = [project / folder / 'skills' / NAME for folder in folders]
    for dest in destinations:
        if dest.exists() or dest.is_symlink():
            raise ValueError('An installation already exists; review it before replacing it.')
        if any(p.is_symlink() for p in (dest.parent, dest.parent.parent)):
            raise ValueError('Skill parent directories must not be symbolic links.')
    subprocess.run([str(python), '-c', 'import sys, yaml; assert sys.version_info >= (3, 9)'], check=True, capture_output=True)
    created = []
    try:
        for dest in destinations:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.skill-stage-', dir=dest.parent) as temp:
                stage = Path(temp) / NAME
                shutil.copytree(SOURCE, stage, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'runtime.json'))
                (stage / 'runtime.json').write_text(json.dumps({'python': str(Path(python).absolute())}) + '\n')
                stage.rename(dest)
            created.append(dest)
    except Exception:
        for dest in created:
            shutil.rmtree(dest)
        raise
    return destinations


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--agent', choices=('codex', 'claude-code', 'both'), required=True)
    runtime = parser.add_mutually_exclusive_group(required=True)
    runtime.add_argument('--python', type=Path, help='Existing Python 3.9+ interpreter with PyYAML.')
    runtime.add_argument('--venv', type=Path, help='Create a NEW environment outside your vault; installs dependencies from the package index.')
    args = parser.parse_args(argv)
    # Validate all destinations before any environment creation or download.
    project = args.project.resolve()
    folders = ('.agents', '.claude') if args.agent == 'both' else ('.agents' if args.agent == 'codex' else '.claude',)
    if not project.is_dir():
        parser.error('Project directory must already exist.')
    for folder in folders:
        dest = project / folder / 'skills' / NAME
        if dest.exists() or dest.is_symlink() or dest.parent.is_symlink() or dest.parent.parent.is_symlink():
            parser.error('Existing installation or symbolic-link parent; no changes made.')
    python = args.python
    if args.venv:
        env = args.venv.absolute()
        if env.exists() or env.is_symlink():
            parser.error('Choose a new environment path; existing environments are not overwritten.')
        try:
            venv.EnvBuilder(with_pip=True).create(env)
            python = env / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
            subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(SOURCE / 'requirements.txt')], check=True)
        except (OSError, subprocess.CalledProcessError):
            parser.error('Environment setup failed; no Skill installed. The new environment may remain for inspection.')
    try:
        destinations = install(project, args.agent, python)
    except (OSError, ValueError, subprocess.CalledProcessError):
        parser.error('Installation failed. Check Python/PyYAML and destination permissions; existing skills were preserved.')
    for dest in destinations:
        print('Installed:', dest)
    print('Python:', Path(python).absolute())
    print('Restart the agent if the Skill does not appear. No agent or model was launched.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
