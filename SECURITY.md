# Security policy

agentscan is a local CLI that reads agent asset files in a directory you point it at.

## What it does and does not do

- `scan` and `validate` only read files. They never write, execute, or upload anything.
- YAML is parsed with `yaml.safe_load` only, so frontmatter cannot construct Python objects.
- agentscan makes no network calls. It does not start MCP servers, run commands from
  MCP configs, or contact any URL found in a config.
- `fix` is the only command that writes. It writes only to frontmatter assets whose real
  location (after resolving symlinks) is inside the target path; any other file is
  reported as `[skipped]` and left untouched. Use `fix --dry-run` to preview.

These boundaries are covered by tests: `tests/test_fixers.py` checks that `fix` changes
only files inside the target and never writes through a symlink that points outside it.

## Out of scope

- agentscan checks structure, not content. It does not detect prompt injection, malicious
  instructions, or unsafe MCP servers. A passing `validate` does not mean an asset is safe
  to run.
- Files you choose to scan are trusted to be readable; very large files are read into memory.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting on this repository (Security tab →
"Report a vulnerability") rather than a public issue. This is a portfolio project with no
SLA; reports are handled on a best-effort basis.
