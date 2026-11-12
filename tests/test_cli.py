import json

from click.testing import CliRunner

from agentscan.cli import main
from tests.test_detectors import make_tree


def test_scan_table(tmp_path):
    make_tree(tmp_path)
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "SKILL.md skill" in result.output
    assert "5 asset(s) found." in result.output


def test_scan_json(tmp_path):
    make_tree(tmp_path)
    result = CliRunner().invoke(main, ["scan", str(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert {entry["type"] for entry in data} == {
        "skill",
        "mcp_config",
        "agent_instructions",
        "subagent",
        "plugin_manifest",
    }


def test_scan_empty(tmp_path):
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "No agent assets found." in result.output


def test_validate_all_ok(tmp_path):
    make_tree(tmp_path)
    result = CliRunner().invoke(main, ["validate", str(tmp_path)])
    assert result.exit_code == 0
    assert "5 asset(s) checked: 0 error(s), 0 warning(s)." in result.output


def test_validate_catches_bad_skill(tmp_path):
    make_tree(tmp_path)
    (tmp_path / "skills" / "pdf" / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["validate", str(tmp_path)])
    assert result.exit_code == 1
    assert "[FAIL] skills/pdf/SKILL.md" in result.output
    assert "missing YAML frontmatter" in result.output


def test_validate_warning_only_passes_unless_strict(tmp_path):
    make_tree(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("", encoding="utf-8")  # empty file -> warning
    result = CliRunner().invoke(main, ["validate", str(tmp_path)])
    assert result.exit_code == 0
    assert "[WARN] CLAUDE.md" in result.output
    assert "0 error(s), 1 warning(s)." in result.output
    strict = CliRunner().invoke(main, ["validate", str(tmp_path), "--strict"])
    assert strict.exit_code == 1


def test_validate_json_output(tmp_path):
    make_tree(tmp_path)
    (tmp_path / ".mcp.json").write_text("{broken", encoding="utf-8")
    result = CliRunner().invoke(main, ["validate", str(tmp_path), "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    bad = [entry for entry in data if entry["problems"]]
    assert len(bad) == 1 and bad[0]["path"] == ".mcp.json"
    assert bad[0]["problems"][0]["severity"] == "error"
