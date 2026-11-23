<div align="center">

# agentscan

**Inspect the agent assets. Check the configuration. Review the repair.**

Local tooling for the files behind an agent system.

[![CI](https://github.com/asadullah48/agentscan/actions/workflows/test.yml/badge.svg)](https://github.com/asadullah48/agentscan/actions/workflows/test.yml)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Version](https://img.shields.io/badge/version-0.2.0-0f766e?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-475569?style=flat-square)

[Quick start](#quick-start) · [Engineering evidence](#engineering-evidence) · [Limits](#limits) · [Portfolio](https://asadullahshafique-devunity.vercel.app/)

</div>

---

## The problem

Skills, MCP configs, instruction files, and subagent definitions can spread across a repository. Before running an agent, a developer needs to know which assets exist and whether their basic structure is valid.

agentscan makes those files inspectable through a Python CLI. It finds known asset patterns, reports configuration problems, and offers two limited frontmatter repairs.

## The engineering approach

| Stage | Command | Behavior |
| --- | --- | --- |
| 01 · Discover | `agentscan scan PATH` | Inventory files using the bundled YAML catalog. |
| 02 · Check | `agentscan validate PATH` | Report errors and warnings, with exit codes for CI. |
| 03 · Preview | `agentscan fix PATH --dry-run` | Show proposed frontmatter repairs without writing. |
| 04 · Repair | `agentscan fix PATH` | Apply supported repairs to matching files. |

Discovery and validation read local files. Repairs require an explicit `fix` command. The CLI does not call a model, start MCP servers, or need an API key.

## Quick start

Requires Python 3.9 or newer. Download this repository's ZIP from GitHub, extract it, and open a terminal in the extracted project folder.

```bash
python -m pip install .

agentscan scan .
agentscan validate . --json
```

Scan your agent project by replacing `.` with its directory:

```bash
agentscan scan /path/to/project --json
agentscan validate /path/to/project --fail-on warning
agentscan validate /path/to/project --format sarif > agentscan.sarif
agentscan fix /path/to/project --dry-run
```

After reviewing the preview:

```bash
agentscan fix /path/to/project
agentscan validate /path/to/project
```

Replace generated TODO descriptions with real descriptions. A passing structural check does not establish that an asset is useful or safe to execute.

## What gets checked

| Asset | Detection | Checks |
| --- | --- | --- |
| Skills | `SKILL.md` | YAML frontmatter with non-empty string `name` and `description`. |
| MCP configs | `.mcp.json`, `mcp.json` | Valid JSON with a non-empty `mcpServers` object; warnings for entries without a `command` or `url` key. |
| Instructions | `CLAUDE.md`, `AGENTS.md` | Readability and empty-file warning; no content-policy checks. |
| Subagents | Markdown under `.claude/agents/` | YAML frontmatter with a non-empty string `name`. |
| Plugin manifests | `plugin.json` under `.claude-plugin/` | JSON object with a non-empty string `name`. |

Empty assets produce a warning before type-specific validation. Frontmatter descriptions longer than 1,024 characters also produce a warning.

Every check has a rule id, severity, and fix in [`docs/RULES.md`](docs/RULES.md), generated from [`catalog.yaml`](agentscan/catalog.yaml) by `python -m agentscan.rules`. A test fails if the doc is stale.

### Output formats

`scan` and `validate` accept `--format table|json|sarif` (default `table`; `--json` is an alias for `--format json`).

- `json`: one object per asset; `validate` problems carry `rule`, `severity`, and `message`.
- `sarif`: SARIF 2.1.0 for GitHub code scanning and other SARIF tools. Paths stay relative to the scanned directory. Tests validate the output against the official OASIS schema.

### Validation exit codes

| Code | Meaning |
| --- | --- |
| `0` | Nothing at or above `--fail-on` was found. Also returned when no assets are found. |
| `1` | Errors were found, or warnings with `--fail-on warning`. |
| `2` | Invalid command usage, such as a nonexistent path. |

`--fail-on` defaults to `error`; `--strict` is an alias for `--fail-on warning`. The exit code is the same for every `--format`.

### Repair boundary

The fixer supports two changes for frontmatter assets:

- Prepend missing frontmatter with a derived name and, when required, a TODO description.
- Insert a missing required `name` into an existing valid frontmatter block.

It never writes to a file whose real location (after resolving symlinks) is outside the target path; such files are reported as `[skipped]`. It leaves broken YAML, unterminated frontmatter, malformed JSON, and existing invalid field values for manual repair. Derived names come from the skill's parent directory or the subagent's filename. Review the diff after applying repairs.

## Use in CI

### pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/asadullah48/agentscan
    rev: <commit-sha>  # pin a commit; this repository has no release tags yet
    hooks:
      - id: agentscan-validate
        # args: [".", "--fail-on", "warning"]
```

### GitHub Actions

```yaml
# .github/workflows/agentscan.yml
name: agentscan
on: [push, pull_request]
permissions:
  contents: read
  security-events: write  # only needed for the SARIF upload
jobs:
  agentscan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: python -m pip install "git+https://github.com/asadullah48/agentscan@<commit-sha>"
      - run: agentscan validate . --format sarif > agentscan.sarif
        continue-on-error: true  # upload findings even when validation fails
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: agentscan.sarif
      - run: agentscan validate . --fail-on error
```

The SARIF upload shows findings in the Security tab; drop the upload step and `security-events` if you only want a pass/fail gate. Code scanning on private repositories requires GitHub Advanced Security.

## Engineering evidence

**VERIFIED · 2026-11-12 · code commit [`a4891c5`](https://github.com/asadullah48/agentscan/tree/a4891c59f15a42c0e269ceeeb7a711f281151d40)**

The full pytest suite passed locally: **36 passed in 2.11s**. This is a local run, not a GitHub Actions status.

```bash
python -m pytest tests -q
```

Verification covers CLI behavior, discovery, validators, and fixers. It does not establish production adoption, security certification, or complete compatibility with every agent client.

| Decision | Inspect the implementation |
| --- | --- |
| File patterns live in a packaged catalog | [`catalog.yaml`](agentscan/catalog.yaml), [`pyproject.toml`](pyproject.toml) |
| Discovery skips common build and dependency directories | [`detectors.py`](agentscan/detectors.py) |
| Errors and warnings stay separate | [`validators.py`](agentscan/validators.py) |
| Repairs are limited to frontmatter operations | [`fixers.py`](agentscan/fixers.py) |
| Table, JSON, and SARIF share the same discovery path | [`cli.py`](agentscan/cli.py), [`sarif.py`](agentscan/sarif.py) |
| Behavior is checked with pytest | [`tests/`](tests/) |

## Limits

- Detection uses known filenames and path patterns. It is not a complete inventory of every agent framework.
- MCP checks inspect configuration structure. They do not connect to servers or verify credentials, tool behavior, or protocol compliance.
- Instruction text is not assessed for correctness or prompt injection.
- New detection patterns can use existing validators through the catalog. New validation behavior requires Python code.
- This repository ships a local CLI. No hosted service or production customer results are claimed.

## Development

```bash
python -m pip install '.[dev]'
ruff check .
python -m pytest tests -q
```

Runtime dependencies: Click and PyYAML. Development extras: pytest, ruff, and jsonschema (for the JSON and SARIF schema tests).

## Built by Asadullah Shafique

Agentic AI Systems Engineer · Karachi, Pakistan

I build agent tooling with explicit controls, inspectable behavior, and checks tied to the implementation.

[Portfolio](https://asadullahshafique-devunity.vercel.app/) · [GitHub](https://github.com/asadullah48) · [Discuss an agent engineering project](mailto:asadullahshafique@hotmail.com)

## License

[MIT](LICENSE)
