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
activation inside Codex and Claude Code has not yet been tested. Other agents
and operating systems are not currently verified.

## Optional checks and reports

```sh
# Enable project-index metadata checks only for the specified folder.
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --projects-dir Projects --json

# Compare with an earlier private report from the same vault and options.
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --baseline "/path/to/private/before.json" --json

# Remove note names, link targets and free-text details before reviewing a report for sharing.
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --json --redact
```

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

## License

MIT. This project is independent and is not affiliated with Obsidian.
