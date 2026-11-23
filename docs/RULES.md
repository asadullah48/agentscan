# Rule catalog

<!-- Generated from agentscan/catalog.yaml by `python -m agentscan.rules`. Do not edit by hand. -->

Every check `agentscan validate` can report. `error` fails validation; `warning` fails only with `--fail-on warning`. Rule ids appear in `--format json` (`rule`) and `--format sarif` (`ruleId`).

17 rules: 14 errors, 3 warnings.

| Rule | Severity | Applies to | Check | Fix |
| --- | --- | --- | --- | --- |
| `unreadable` | error | All assets | The file cannot be read as UTF-8 text. | Manual. Re-save the file as UTF-8 and check its permissions. |
| `empty-file` | warning | All assets | The file is empty or contains only whitespace. | Manual. Add content or delete the file. |
| `unknown-validator` | error | All assets | The catalog names a validator that agentscan does not implement. | Manual. Correct the `validator` key in catalog.yaml. |
| `frontmatter-missing` | error | SKILL.md skill, Subagent definition | The file does not start with a `---` YAML frontmatter block. | Auto. `agentscan fix` prepends a skeleton with a derived name and, for skills, a TODO description. |
| `frontmatter-unterminated` | error | SKILL.md skill, Subagent definition | The frontmatter block has no closing `---` line. | Manual. Add the closing `---` line. |
| `frontmatter-invalid-yaml` | error | SKILL.md skill, Subagent definition | The frontmatter block is not valid YAML. | Manual. Correct the YAML syntax reported in the message. |
| `frontmatter-not-mapping` | error | SKILL.md skill, Subagent definition | The frontmatter parses, but not as a key/value mapping. | Manual. Rewrite the block as `key: value` lines. |
| `field-missing` | error | SKILL.md skill, Subagent definition | A required frontmatter field (`name`, and `description` for skills) is absent. | Auto for `name` (derived from the skill directory or subagent filename). Manual for `description`. |
| `field-invalid` | error | SKILL.md skill, Subagent definition | A required frontmatter field is empty or not a string. | Manual. Set the field to a non-empty string. |
| `description-too-long` | warning | SKILL.md skill, Subagent definition | The `description` field is longer than 1,024 characters. | Manual. Shorten the description. |
| `mcp-invalid-json` | error | MCP server config | The MCP config is not valid JSON. | Manual. Correct the JSON syntax reported in the message. |
| `mcp-servers-missing` | error | MCP server config | The config has no top-level `mcpServers` object. | Manual. Wrap server entries in a top-level `mcpServers` object. |
| `mcp-servers-empty` | error | MCP server config | `mcpServers` is not an object or has no entries. | Manual. Declare at least one server, or delete the config. |
| `mcp-server-no-transport` | warning | MCP server config | A server entry declares neither `command` nor `url`. | Manual. Add a `command` (stdio) or `url` (HTTP) key to the entry. |
| `plugin-invalid-json` | error | Plugin manifest | The plugin manifest is not valid JSON. | Manual. Correct the JSON syntax reported in the message. |
| `plugin-not-object` | error | Plugin manifest | The plugin manifest is not a JSON object. | Manual. Make the top-level value an object. |
| `plugin-name-invalid` | error | Plugin manifest | The plugin manifest's `name` is missing, empty, or not a string. | Manual. Set `name` to a non-empty string. |
