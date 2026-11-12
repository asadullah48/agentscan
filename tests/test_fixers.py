import json

from click.testing import CliRunner

from agentscan.cli import main
from agentscan.detectors import Asset, AssetType
from agentscan.fixers import fix_asset

SKILL_TYPE = AssetType(
    id="skill",
    label="SKILL.md skill",
    filenames=["SKILL.md"],
    validator="frontmatter",
    required_fields=["name", "description"],
)
SUBAGENT_TYPE = AssetType(
    id="subagent",
    label="Subagent definition",
    suffix=".md",
    path_contains="/.claude/agents/",
    validator="frontmatter",
    required_fields=["name"],
)


def make_asset(path, type_id="skill"):
    return Asset(type_id=type_id, label="x", path=path, rel_path=path.name)


def test_fix_adds_skeleton_for_missing_frontmatter(tmp_path):
    skill_dir = tmp_path / "pdf"
    skill_dir.mkdir()
    path = skill_dir / "SKILL.md"
    path.write_text("# pdf skill\n", encoding="utf-8")
    fixes = fix_asset(make_asset(path), SKILL_TYPE)
    assert fixes == ["added frontmatter skeleton (name: pdf)"]
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\nname: pdf\ndescription: TODO - describe this asset\n---\n")
    assert content.endswith("# pdf skill\n")


def test_fix_inserts_missing_name(tmp_path):
    path = tmp_path / "reviewer.md"
    path.write_text("---\nmodel: sonnet\n---\nbody\n", encoding="utf-8")
    fixes = fix_asset(make_asset(path, "subagent"), SUBAGENT_TYPE)
    assert fixes == ["inserted frontmatter field name: reviewer"]
    assert path.read_text(encoding="utf-8").startswith("---\nname: reviewer\nmodel: sonnet\n---\n")


def test_fix_leaves_valid_and_hard_cases_alone(tmp_path):
    valid = tmp_path / "SKILL.md"
    valid.write_text("---\nname: ok\ndescription: fine\n---\n", encoding="utf-8")
    assert fix_asset(make_asset(valid), SKILL_TYPE) == []
    unterminated = tmp_path / "u.md"
    unterminated.write_text("---\nname: x\n", encoding="utf-8")
    assert fix_asset(make_asset(unterminated, "subagent"), SUBAGENT_TYPE) == []


def test_fix_dry_run_does_not_write(tmp_path):
    path = tmp_path / "SKILL.md"
    original = "# no frontmatter\n"
    path.write_text(original, encoding="utf-8")
    fixes = fix_asset(make_asset(path), SKILL_TYPE, apply=False)
    assert fixes and path.read_text(encoding="utf-8") == original


def test_cli_fix_roundtrip(tmp_path):
    (tmp_path / "skills" / "pdf").mkdir(parents=True)
    broken = tmp_path / "skills" / "pdf" / "SKILL.md"
    broken.write_text("# pdf\n", encoding="utf-8")
    runner = CliRunner()

    dry = runner.invoke(main, ["fix", str(tmp_path), "--dry-run"])
    assert dry.exit_code == 0 and "[would fix] skills/pdf/SKILL.md" in dry.output
    assert broken.read_text(encoding="utf-8") == "# pdf\n"

    applied = runner.invoke(main, ["fix", str(tmp_path)])
    assert applied.exit_code == 0 and "[fixed] skills/pdf/SKILL.md" in applied.output

    # after fixing, validate reports no errors (TODO description is non-empty)
    validate = runner.invoke(main, ["validate", str(tmp_path), "--json"])
    assert validate.exit_code == 0
    data = json.loads(validate.output)
    assert all(not entry["problems"] for entry in data)

    again = runner.invoke(main, ["fix", str(tmp_path)])
    assert "Nothing to fix." in again.output
