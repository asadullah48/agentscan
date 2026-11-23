import json

import pytest
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


def _snapshot(root):
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_fix_only_changes_files_inside_target(tmp_path):
    target = tmp_path / "target"
    outside = tmp_path / "outside"
    for root in (target, outside):
        (root / "skills" / "pdf").mkdir(parents=True)
        (root / "skills" / "pdf" / "SKILL.md").write_text("# pdf\n", encoding="utf-8")
        (root / ".claude" / "agents").mkdir(parents=True)
        (root / ".claude" / "agents" / "rev.md").write_text("---\nmodel: x\n---\n", encoding="utf-8")
    before = _snapshot(tmp_path)

    result = CliRunner().invoke(main, ["fix", str(target)])

    assert result.exit_code == 0
    after = _snapshot(tmp_path)
    assert set(after) == set(before), "fix must not create or delete files"
    changed = {p for p in before if before[p] != after[p]}
    assert changed == {target / "skills" / "pdf" / "SKILL.md", target / ".claude" / "agents" / "rev.md"}
    assert all(target in p.parents for p in changed)


def test_fix_never_writes_through_symlink_outside_target(tmp_path):
    target = tmp_path / "target"
    (target / "skills" / "evil").mkdir(parents=True)
    victim = tmp_path / "outside" / "SKILL.md"
    victim.parent.mkdir()
    victim.write_text("# outside, no frontmatter\n", encoding="utf-8")
    link = target / "skills" / "evil" / "SKILL.md"
    try:
        link.symlink_to(victim)
    except OSError:
        pytest.skip("symlinks not permitted here (Windows without Developer Mode)")

    result = CliRunner().invoke(main, ["fix", str(target)])

    assert result.exit_code == 0
    assert "[skipped] skills/evil/SKILL.md" in result.output
    assert victim.read_text(encoding="utf-8") == "# outside, no frontmatter\n"
