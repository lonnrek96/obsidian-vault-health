# Reporting and optional profiles

## Default checks

The checker reads Markdown files under the selected directory, skips hidden
files/directories and symbolic links, and checks internal wikilinks, Markdown
inline/reference links, headings, block IDs and YAML frontmatter. Fenced/indented
examples and comments are ignored. Template files named `*-template.md` inside a
`templates` directory are excluded. Other assets can be link targets.

Short wikilinks with multiple possible targets are warnings; the checker does not
pick an arbitrary note. It does not resolve every Obsidian extension or frontmatter
alias, execute plugins, or check external web URLs. A diagnostic is a static-file
finding, not proof that an app interaction failed.

`file:` links, absolute Markdown paths and paths escaping the vault are not
checked for existence unless `--local-root` explicitly selects their device scope.
Remote `file://server/...` paths are never mounted or contacted. Symlinks are
resolved before external existence checks to keep them inside the selected scope.
The `file:line` convention is flagged for review, not treated as a missing filename.

## Baselines

The JSON schema version is 1. Each issue has a vault-relative `path`, `code`,
`target`, `detail`, `level`, `group` and `document_scope`. CLI reports also attach
`age`: `unclassified`, `new` or `historical`.

A baseline compares `(path, code, target)`. Use the same vault and options.
Moving a file can make a diagnostic appear new, so inspect renames manually.
An unchanged error can produce exit 0 when it is historical; this does not mean
the vault has no errors. Baselines must be ordinary private JSON reports, not
redacted reports. The tool does not automatically verify that two reports came
from the same device or vault.

## Optional conventions

No project schema or numbered directory layout is required by default.

With `--projects-dir Projects`, only `Projects/<project>/README.md` is treated as
a project index. It requires `title`, `type`, `status`, `project`, `project_id`,
`project_status`, `summary_as_of` and `updated`. Type is `project-index`; aliases
use `project-alias` and are excluded from project counts and duplicate IDs.
IDs use lowercase letters, digits and hyphens. Project status can be `active`,
`planning`, `paused`, `completed` or `archived`. Dates use `YYYY-MM-DD`.

With `--inbox-dir Inbox`, dated Markdown filenames generate age warnings, with a
specific note after seven days. This option does not process an inbox or queue.

Archive grouping recognizes directory names `Archive`, `Archives`, `corpus` and
`evidence`, or frontmatter `status: historical` / `status: superseded`. Grouping
does not suppress errors or bypass the baseline rules.

To retain an intentionally missing note, put a nonempty reason for that exact
target in the source note's `intentional_missing_links` mapping. It is reported as
information. Private reasons appear in ordinary reports; `--redact` removes them.

## Privacy of reports

The checker does not write files or send network requests. The absolute vault
root is omitted from reports. Ordinary issues still contain private filenames,
raw link targets (including external local paths), and free-text exception reasons.

`--redact` substitutes per-report note IDs and removes raw targets and details. It
preserves issue types, severity, counts, groups and age. It does not make a report
a verified anonymous dataset. Review these remaining metadata before sharing it.
The skill guides an agent; it does not restrict the host's other tools or network
permissions. Installing dependencies can require network access separately.
