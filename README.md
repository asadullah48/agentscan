# agentscan

A Python CLI to find and validate AI-agent assets in a local directory.

## Install

Requires Python 3.9 or newer.

```bash
pip install .
```

## Usage

```bash
agentscan scan .
agentscan scan . --json
agentscan validate . --json
agentscan validate . --strict
agentscan fix . --dry-run
agentscan fix .
```

Detects SKILL.md files, MCP configs (`.mcp.json`, `mcp.json`), instruction files
(`CLAUDE.md`, `AGENTS.md`), subagent definitions in `.claude/agents/`, and
plugin manifests in `.claude-plugin/plugin.json`.

`scan` and `validate` read files. `fix` writes limited frontmatter repairs:
a missing block gets a derived name and a TODO description; a missing name
gets a derived value. Review the dry run first and replace TODO descriptions.
Broken YAML, unterminated frontmatter, and malformed JSON need manual repair.

Validation exits with code 1 for errors, or for warnings with `--strict`.
Invalid command usage exits with code 2.

The bundled YAML catalog defines detection patterns and selects existing
validators. New validation behavior requires Python code.

## Development

```bash
pip install '.[dev]'
python -m pytest tests -q
```

## Status

Version 0.2.0, imported from the supplied weekly-loop archive into a fresh
repository. Local CLI project; no production-use claims.

## License

MIT. See LICENSE.
