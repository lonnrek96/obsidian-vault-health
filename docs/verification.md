# Verification status / 驗證狀態

This file distinguishes checker behavior from actual agent integration. No real
notes, credentials or private reports are used in tests.

| Check | Evidence / status |
| --- | --- |
| Checker, privacy and regression tests | 44 tests passed locally on macOS, Python 3.9 |
| Codex and Claude Code project directory installation | Local synthetic subprocess tests; does not prove host discovery |
| Quick installer with a new venv | Real local dependency install and execution passed; runtime paths ignored by Git |
| Existing-install protection | Tested: no overwrite or partial second installation |
| Exclusions, Markdown, aggregate reports | Local behavior tests |
| Skill format and public-file pattern scan | Local check; bounded patterns, not a complete secrets guarantee |
| Real Codex discovery and invocation | Pending; direct script execution is not discovery evidence |
| Real Claude Code discovery and invocation | Pending; requires Claude Code access |
| Linux / macOS / Windows, Python 3.9 and 3.13 | Six remote jobs passed on checker commit `c186ccd`; Windows skips the POSIX-only FIFO test |

## Reproduce local checks

Use a Python environment with PyYAML:

```sh
python -m unittest discover -s tests -v
python tools/check_package.py
```

The package check uses Git's tracked and non-ignored files. Run it inside a Git
checkout. It prints file locations and categories, never matched secrets.

## Real-host acceptance steps

Use a temporary project directory and the fictional `examples/vault` only. Keep
any resulting report local. No account sharing or private vault is needed.

1. Run `install.py` for the intended host, using a new environment outside the
   vault or an existing Python with PyYAML.
2. Start a fresh host session in that project. Confirm the skill appears in the
   host's selector or command list. This step requires the real host.
3. In Codex, invoke `$obsidian-vault-health`; in Claude Code, invoke
   `/obsidian-vault-health`. Explicitly provide the demo vault's absolute path.
4. Ask for a read-only report. Expect two notes, one `missing-link` and one
   `missing-anchor`. Verify the note files remain unchanged.
5. Ask for `--exclude Guide.md`. The explicit heading links into Guide become
   informational `excluded-target` findings; the missing note remains an error.
6. Request Markdown with `--language zh-TW`, then `--summary-only`. Confirm the
   summary has counts without note names, paths or link targets.
7. Record host/version, OS, Python, commands and observed results. Distinguish
   host discovery, model execution and report interpretation. A successful
   command copied by a person does not prove automatic skill selection.

Claude Code access is not required for checker, installation, format or privacy
tests. Leave real Claude Code steps pending until an authorized tester with access
performs them. Never silently substitute API billing or another provider.

中文說明：本機測試使用虛構資料。安裝目錄與程式可執行，不等於 AI 工具已辨識並正確呼叫技能。
兩種工具的真實操作與遠端 CI 結果，必須分別取得證據後才標示通過。

## Remote checker evidence

[GitHub Actions run 43020052686](https://github.com/lonnrek96/obsidian-vault-health/actions/runs/43020052686) passed all six OS/Python combinations on `c186ccd8ffc4e72a1bfd4a3f9ffd2ac8114a3e30`. Linux uses Ubuntu 24.04 because Python 3.9 packages are not available on Ubuntu 26.04. Windows local paths and encoded `file:` URIs are handled using the platform pathname conversion. This is checker/installation evidence, not real AI-host discovery or model behavior evidence.
