# Obsidian Vault Health

English | [繁體中文](README.zh-TW.md)

A read-only Obsidian health checker with an Agent Skill wrapper. Find broken
internal links, missing headings and block IDs, malformed YAML, and ambiguous
note references. Compare results before and after maintenance without editing
your notes.

No account, Obsidian plugin, API key or running Obsidian app is required. The
checker makes no network requests and does not rewrite vault files.

## Try it locally

Use Python 3.9+ and an isolated environment outside your vault:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/obsidian-vault-health/requirements.txt
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --json
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.
Dependency installation may contact the package index; the checker itself runs
locally. Exit 1 means errors were found, so inspect stdout rather than treating
the scan as a crashed program. Keep any redirected report outside your vault.

## Install as a Skill

### Quick project installation

From this downloaded repository, install for either agent or both with one command:

```sh
python3 install.py --project "/path/to/project" --agent both --venv "/path/outside-vault/health-env"
```

The project directory must exist and the environment path must be new. This
creates an isolated environment, installs PyYAML, and copies the full Skill to
both project directories. Use `--agent codex` or `--agent claude-code` for one.
An existing Skill is preserved; review it manually before upgrading. No agent
or model is launched. The dependency download requires network access.

Already have Python with PyYAML? Use the offline installation path:

```sh
python3 install.py --project "/path/to/project" --agent both --python "/path/to/environment/python"
```

The installer stores the interpreter path in an ignored local `runtime.json` so
the agent can locate it. Do not share that machine-specific file. On Windows,
use `python` if `python3` is unavailable.

### Manual installation


Designed for **Codex and Claude Code**, using the same Skill instructions and
Python checker. Copy the complete `skills/obsidian-vault-health` folder into one
of these project locations:

| Agent | Installed Skill file | Explicit invocation |
| --- | --- | --- |
| Codex | `.agents/skills/obsidian-vault-health/SKILL.md` | `$obsidian-vault-health` |
| Claude Code | `.claude/skills/obsidian-vault-health/SKILL.md` | `/obsidian-vault-health` |

Keep `scripts`, `references`, `agents` and `requirements.txt` together with
`SKILL.md`. Check for an existing installation before copying. Set up the Python
dependency using the isolated environment described above. The optional
`agents/openai.yaml` supplies Codex display metadata; the shared workflow does
not depend on it.

Codex example:

```text
$obsidian-vault-health Review the vault at "/path/to/vault". Report broken links
and missing anchors, but do not change any notes.
```

Claude Code example:

```text
/obsidian-vault-health Review the vault at "/path/to/vault". Report broken links
and missing anchors, but do not change any notes.
```

These paths and invocation styles follow the official
[Codex documentation](https://learn.chatgpt.com/docs/build-skills) and
[Claude Code documentation](https://code.claude.com/docs/en/skills).
The shared Python checker has passed local synthetic tests. Actual Skill
activation inside Codex and Claude Code has not yet been tested. Automated checker tests passed on Linux, macOS and Windows with Python 3.9 and
3.13; this does not verify other agents or real host behavior.

## Example reports

Try the entirely fictional [demo vault](examples/vault). It has two notes and
two intentional errors: one missing note and one missing heading.

- [English report](examples/report.en.md)
- [繁體中文報告](examples/report.zh-TW.md)

```sh
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault examples/vault --markdown --language en
```

## Optional checks and reports

```sh
# Enable project-index metadata checks only for the specified folder.
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --projects-dir Projects --json

# Compare with an earlier private report from the same vault and options.
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --baseline "/path/to/private/before.json" --json

# Remove note names, link targets and free-text details before reviewing a report for sharing.
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --json --redact
```

Use `--exclude Private --exclude Imports` to skip exact vault-relative files or
subtrees before reading. Links explicitly pointing into them are unverified;
short wikilinks can remain unresolved. Baseline exclusions must match.

Use `--markdown --language en` or `--markdown --language zh-TW` for a readable
report with suggested review order. Issue codes and technical details remain
English. Use `--summary-only` with any format for aggregate counts without note
names or targets. Summary-only output cannot be used as a baseline. All formats
preserve exit status; redirect private reports outside the vault.

`--inbox-dir Inbox` enables dated-note age warnings. `--local-root` explicitly
permits external local-path existence checks in the selected directory; it is
off by default. No particular vault layout is required. Full behavior and
limitations are in [reporting.md](skills/obsidian-vault-health/references/reporting.md).

## Privacy

Only code, instructions and synthetic tests belong in this repository. Do not add
real notes, reports, screenshots, settings, backups, account data or credentials.
Ordinary reports can contain private note names and external local paths. Keep
them local; use `--redact` and review the result before sharing. Redaction removes
these fields but is not a guarantee of anonymous output.

The checker does not execute note content or fetch web URLs. Hidden entries and
symbolic links are skipped. It does not verify the rendered Obsidian interface,
all Markdown extensions, JavaScript, Dataview or Bases queries.

## Development

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

Tests use temporary synthetic vaults. They cover link/anchor checks, baseline
behavior, read-only operation, explicit local scope, redaction and private-data
boundaries. Do not replace them with copied personal notes.

## Automated checks and verification status

The [GitHub Actions workflow](.github/workflows/check.yml) runs tests, project
installation journeys, Skill format validation and common secret-pattern checks.
It targets Linux, macOS and Windows with Python 3.9 and 3.13. Adding the workflow
is not proof those remote jobs passed; see [verification status and host test
steps](docs/verification.md). Pattern checks do not guarantee the absence of
all sensitive data and do not scan Git history or your vault.

## License

MIT. This project is independent and is not affiliated with Obsidian.
