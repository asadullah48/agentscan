from agentscan.detectors import AssetType, Asset
from agentscan.validators import (
    MAX_DESCRIPTION_LEN,
    validate_asset,
    validate_frontmatter,
    validate_mcp_json,
    validate_plugin_json,
)

SKILL_TYPE = AssetType(
    id="skill",
    label="SKILL.md skill",
    filenames=["SKILL.md"],
    validator="frontmatter",
    required_fields=["name", "description"],
)
MCP_TYPE = AssetType(id="mcp_config", label="MCP server config", filenames=[".mcp.json"], validator="mcp_json")
PLUGIN_TYPE = AssetType(
    id="plugin_manifest", label="Plugin manifest", filenames=["plugin.json"], validator="plugin_json"
)


def messages(problems):
    return [p.message for p in problems]


def severities(problems):
    return [p.severity for p in problems]


def test_frontmatter_valid():
    content = "---\nname: pdf\ndescription: Work with PDFs\n---\nbody\n"
    assert validate_frontmatter(content, SKILL_TYPE) == []


def test_frontmatter_missing_block():
    problems = validate_frontmatter("# just markdown\n", SKILL_TYPE)
    assert messages(problems) == ["missing YAML frontmatter (file must start with '---')"]
    assert severities(problems) == ["error"]


def test_frontmatter_unterminated():
    assert "unterminated" in validate_frontmatter("---\nname: x\n", SKILL_TYPE)[0].message


def test_frontmatter_missing_field():
    problems = validate_frontmatter("---\nname: pdf\n---\n", SKILL_TYPE)
    assert messages(problems) == ["frontmatter field 'description' is missing"]


def test_frontmatter_empty_field():
    problems = validate_frontmatter("---\nname: ''\ndescription: ok\n---\n", SKILL_TYPE)
    assert messages(problems) == ["frontmatter field 'name' must be a non-empty string (got str)"]


def test_frontmatter_non_string_field():
    problems = validate_frontmatter("---\nname: 123\ndescription: ok\n---\n", SKILL_TYPE)
    assert messages(problems) == ["frontmatter field 'name' must be a non-empty string (got int)"]


def test_frontmatter_long_description_warns():
    desc = "x" * (MAX_DESCRIPTION_LEN + 1)
    problems = validate_frontmatter(f"---\nname: pdf\ndescription: {desc}\n---\n", SKILL_TYPE)
    assert severities(problems) == ["warning"]
    assert "consider trimming" in problems[0].message


def test_mcp_json_valid():
    assert validate_mcp_json('{"mcpServers": {"gh": {"command": "gh-mcp"}}}', MCP_TYPE) == []


def test_mcp_json_invalid_json():
    assert "not valid JSON" in validate_mcp_json("{oops", MCP_TYPE)[0].message


def test_mcp_json_missing_servers():
    assert messages(validate_mcp_json("{}", MCP_TYPE)) == ["missing top-level 'mcpServers' object"]


def test_mcp_json_empty_servers():
    assert messages(validate_mcp_json('{"mcpServers": {}}', MCP_TYPE)) == [
        "'mcpServers' must be a non-empty object"
    ]


def test_mcp_json_server_without_command_warns():
    problems = validate_mcp_json('{"mcpServers": {"odd": {"env": {}}}}', MCP_TYPE)
    assert severities(problems) == ["warning"]
    assert "neither 'command' nor 'url'" in problems[0].message


def test_plugin_json_valid():
    assert validate_plugin_json('{"name": "my-plugin", "version": "1.0"}', PLUGIN_TYPE) == []


def test_plugin_json_missing_name():
    problems = validate_plugin_json('{"version": "1.0"}', PLUGIN_TYPE)
    assert severities(problems) == ["error"]
    assert "'name'" in problems[0].message


def test_validate_asset_unreadable(tmp_path):
    missing = tmp_path / "SKILL.md"  # never created
    asset = Asset(type_id="skill", label="SKILL.md skill", path=missing, rel_path="SKILL.md")
    problems = validate_asset(asset, SKILL_TYPE)
    assert len(problems) == 1 and problems[0].message.startswith("unreadable:")


def test_validate_asset_empty_file_warns(tmp_path):
    plain_type = AssetType(id="agent_instructions", label="Agent instructions", filenames=["CLAUDE.md"])
    path = tmp_path / "CLAUDE.md"
    path.write_text("", encoding="utf-8")
    asset = Asset(type_id="agent_instructions", label="Agent instructions", path=path, rel_path="CLAUDE.md")
    problems = validate_asset(asset, plain_type)
    assert severities(problems) == ["warning"] and messages(problems) == ["file is empty"]


def test_validate_asset_no_validator(tmp_path):
    plain_type = AssetType(id="agent_instructions", label="Agent instructions", filenames=["CLAUDE.md"])
    path = tmp_path / "CLAUDE.md"
    path.write_text("anything", encoding="utf-8")
    asset = Asset(type_id="agent_instructions", label="Agent instructions", path=path, rel_path="CLAUDE.md")
    assert validate_asset(asset, plain_type) == []


def test_unknown_validator_reports_instead_of_crashing(tmp_path):
    bad_type = AssetType(id="x", label="X", filenames=["X.md"], validator="nope")
    path = tmp_path / "X.md"
    path.write_text("anything", encoding="utf-8")
    asset = Asset(type_id="x", label="X", path=path, rel_path="X.md")
    problems = validate_asset(asset, bad_type)
    assert len(problems) == 1 and "unknown validator 'nope'" in problems[0].message
