"""Output formats (json, sarif), the --fail-on exit policy, rule coverage, and the generated rule doc."""

import json
from pathlib import Path

import jsonschema
import pytest
from click.testing import CliRunner

from agentscan.cli import main
from agentscan.detectors import Asset, AssetType, load_catalog
from agentscan.rules import DOC_PATH, load_rules, render_markdown
from agentscan.validators import MAX_DESCRIPTION_LEN, validate_asset
from tests.test_detectors import make_tree

REPO = Path(__file__).resolve().parent.parent
# Official OASIS SARIF 2.1.0 schema (errata01), vendored so the test runs offline.
SARIF_SCHEMA = json.loads((Path(__file__).parent / "data" / "sarif-schema-2.1.0.json").read_text(encoding="utf-8"))

SCAN_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["type", "label", "path"],
        "additionalProperties": False,
        "properties": {"type": {"type": "string"}, "label": {"type": "string"}, "path": {"type": "string"}},
    },
}
VALIDATE_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["type", "path", "problems"],
        "additionalProperties": False,
        "properties": {
            "type": {"type": "string"},
            "path": {"type": "string"},
            "problems": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["rule", "severity", "message"],
                    "additionalProperties": False,
                    "properties": {
                        "rule": {"enum": sorted(load_rules())},
                        "severity": {"enum": ["error", "warning"]},
                        "message": {"type": "string"},
                    },
                },
            },
        },
    },
}


def run(*args):
    return CliRunner().invoke(main, [str(a) for a in args])


def broken_tree(root):
    """make_tree plus one error (bad MCP JSON) and one warning (empty CLAUDE.md)."""
    make_tree(root)
    (root / ".mcp.json").write_text("{broken", encoding="utf-8")
    (root / "CLAUDE.md").write_text("", encoding="utf-8")


# --- JSON -----------------------------------------------------------------


def test_scan_json_matches_schema(tmp_path):
    make_tree(tmp_path)
    result = run("scan", tmp_path, "--format", "json")
    assert result.exit_code == 0
    data = json.loads(result.output)
    jsonschema.validate(data, SCAN_JSON_SCHEMA)
    assert len(data) == 5


def test_validate_json_matches_schema(tmp_path):
    broken_tree(tmp_path)
    result = run("validate", tmp_path, "--format", "json")
    data = json.loads(result.output)
    jsonschema.validate(data, VALIDATE_JSON_SCHEMA)
    rules = {p["rule"] for entry in data for p in entry["problems"]}
    assert rules == {"mcp-invalid-json", "empty-file"}


def test_json_flag_is_alias_and_conflicts_with_sarif(tmp_path):
    make_tree(tmp_path)
    assert run("scan", tmp_path, "--json").output == run("scan", tmp_path, "--format", "json").output
    conflict = run("scan", tmp_path, "--json", "--format", "sarif")
    assert conflict.exit_code == 2 and "--json conflicts" in conflict.output


# --- SARIF ----------------------------------------------------------------


@pytest.mark.parametrize("command", ["scan", "validate"])
def test_sarif_matches_official_schema(tmp_path, command):
    broken_tree(tmp_path)
    result = run(command, tmp_path, "--format", "sarif")
    log = json.loads(result.output)
    jsonschema.Draft4Validator(SARIF_SCHEMA).validate(log)
    run_ = log["runs"][0]
    rules = run_["tool"]["driver"]["rules"]
    assert run_["results"], "expected at least one result"
    for res in run_["results"]:
        assert rules[res["ruleIndex"]]["id"] == res["ruleId"]
        uri = res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        assert not uri.startswith("/") and ":" not in uri  # relative to the scanned root


def test_validate_sarif_levels_match_severities(tmp_path):
    broken_tree(tmp_path)
    log = json.loads(run("validate", tmp_path, "--format", "sarif").output)
    levels = {r["ruleId"]: r["level"] for r in log["runs"][0]["results"]}
    assert levels == {"mcp-invalid-json": "error", "empty-file": "warning"}


# --- --fail-on exit policy ------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "sarif"])
@pytest.mark.parametrize(
    "breakage, fail_on, expected",
    [
        (None, "error", 0),
        (None, "warning", 0),
        ("warning", "error", 0),
        ("warning", "warning", 1),
        ("error", "error", 1),
        ("error", "warning", 1),
    ],
)
def test_fail_on_exit_codes(tmp_path, fmt, breakage, fail_on, expected):
    make_tree(tmp_path)
    if breakage == "warning":
        (tmp_path / "CLAUDE.md").write_text("", encoding="utf-8")
    elif breakage == "error":
        (tmp_path / ".mcp.json").write_text("{broken", encoding="utf-8")
    result = run("validate", tmp_path, "--format", fmt, "--fail-on", fail_on)
    assert result.exit_code == expected, result.output


def test_strict_equals_fail_on_warning(tmp_path):
    make_tree(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("", encoding="utf-8")
    assert run("validate", tmp_path, "--strict").exit_code == 1


def test_fail_on_rejects_unknown_level(tmp_path):
    assert run("validate", tmp_path, "--fail-on", "note").exit_code == 2


# --- every catalog rule is reachable --------------------------------------

TYPES = {t.id: t for t in load_catalog()}
# rule id -> (asset type id, file bytes) that must trigger it
RULE_CASES = {
    "unreadable": ("skill", b"\xff\xfe not utf-8"),
    "empty-file": ("agent_instructions", b"   \n"),
    "frontmatter-missing": ("skill", b"# no frontmatter\n"),
    "frontmatter-unterminated": ("skill", b"---\nname: x\n"),
    "frontmatter-invalid-yaml": ("skill", b"---\nname: [\n---\n"),
    "frontmatter-not-mapping": ("skill", b"---\n- a\n---\n"),
    "field-missing": ("skill", b"---\nname: x\n---\n"),
    "field-invalid": ("skill", b"---\nname: 5\ndescription: d\n---\n"),
    "description-too-long": ("skill", b"---\nname: x\ndescription: " + b"d" * (MAX_DESCRIPTION_LEN + 1) + b"\n---\n"),
    "mcp-invalid-json": ("mcp_config", b"{"),
    "mcp-servers-missing": ("mcp_config", b"{}"),
    "mcp-servers-empty": ("mcp_config", b'{"mcpServers": {}}'),
    "mcp-server-no-transport": ("mcp_config", b'{"mcpServers": {"a": {}}}'),
    "plugin-invalid-json": ("plugin_manifest", b"{"),
    "plugin-not-object": ("plugin_manifest", b"[]"),
    "plugin-name-invalid": ("plugin_manifest", b"{}"),
}


@pytest.mark.parametrize("rule_id", sorted(RULE_CASES))
def test_rule_is_triggered(tmp_path, rule_id):
    type_id, content = RULE_CASES[rule_id]
    path = tmp_path / "asset"
    path.write_bytes(content)
    problems = validate_asset(Asset(type_id, "x", path, "asset"), TYPES[type_id])
    assert [p.rule for p in problems] == [rule_id]
    assert problems[0].severity == load_rules()[rule_id]["severity"]


def test_unknown_validator_rule(tmp_path):
    path = tmp_path / "asset"
    path.write_text("content", encoding="utf-8")
    bogus = AssetType(id="bogus", label="x", filenames=["asset"], validator="nope")
    assert [p.rule for p in validate_asset(Asset("bogus", "x", path, "asset"), bogus)] == ["unknown-validator"]


def test_every_catalog_rule_has_a_trigger_case():
    assert set(RULE_CASES) | {"unknown-validator"} == set(load_rules())


# --- generated rule doc ---------------------------------------------------


def test_rules_doc_is_up_to_date():
    on_disk = (REPO / DOC_PATH).read_text(encoding="utf-8")  # universal newlines: CRLF checkouts still compare
    assert on_disk == render_markdown(), "docs/RULES.md is stale: run `python -m agentscan.rules`"


def test_rules_doc_lists_every_rule():
    doc = render_markdown()
    for rule_id in load_rules():
        assert f"`{rule_id}`" in doc
