from pathlib import Path

from agentscan.detectors import load_catalog, scan


def make_tree(root: Path) -> None:
    (root / "skills" / "pdf").mkdir(parents=True)
    (root / "skills" / "pdf" / "SKILL.md").write_text(
        "---\nname: pdf\ndescription: Work with PDFs\n---\n# pdf\n", encoding="utf-8"
    )
    (root / ".mcp.json").write_text('{"mcpServers": {"gh": {"command": "gh-mcp"}}}', encoding="utf-8")
    (root / "CLAUDE.md").write_text("# Project instructions\n", encoding="utf-8")
    (root / ".claude" / "agents").mkdir(parents=True)
    (root / ".claude" / "agents" / "reviewer.md").write_text(
        "---\nname: reviewer\n---\nReview code.\n", encoding="utf-8"
    )
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "plugin.json").write_text(
        '{"name": "demo-plugin", "version": "0.1.0"}', encoding="utf-8"
    )
    # noise that must be ignored
    (root / "node_modules" / "pkg").mkdir(parents=True)
    (root / "node_modules" / "pkg" / "SKILL.md").write_text("junk", encoding="utf-8")
    (root / "notes.md").write_text("not an asset", encoding="utf-8")


def test_catalog_loads_from_package_data():
    catalog = load_catalog()
    ids = {t.id for t in catalog}
    assert {"skill", "mcp_config", "agent_instructions", "subagent"} <= ids


def test_scan_finds_all_asset_types(tmp_path):
    make_tree(tmp_path)
    assets = scan(tmp_path)
    by_type = {a.type_id: a.rel_path for a in assets}
    assert by_type["skill"] == "skills/pdf/SKILL.md"
    assert by_type["mcp_config"] == ".mcp.json"
    assert by_type["agent_instructions"] == "CLAUDE.md"
    assert by_type["subagent"] == ".claude/agents/reviewer.md"
    assert by_type["plugin_manifest"] == ".claude-plugin/plugin.json"
    assert len(assets) == 5  # node_modules pruned, notes.md not matched


def test_scan_empty_tree(tmp_path):
    assert scan(tmp_path) == []


def test_scan_rooted_inside_dot_claude_still_finds_subagents(tmp_path):
    make_tree(tmp_path)
    assets = scan(tmp_path / ".claude")
    assert [a.type_id for a in assets] == ["subagent"]
    assert assets[0].rel_path == "agents/reviewer.md"


def test_scan_does_not_false_positive_on_similar_dir_names(tmp_path):
    (tmp_path / "foo.claude" / "agents").mkdir(parents=True)
    (tmp_path / "foo.claude" / "agents" / "x.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    assert scan(tmp_path) == []


def test_plugin_json_outside_claude_plugin_dir_is_not_claimed(tmp_path):
    (tmp_path / "plugin.json").write_text('{"name": "unrelated"}', encoding="utf-8")
    assert scan(tmp_path) == []
