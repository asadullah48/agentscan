"""Validation of discovered agent assets.

Each validator takes the asset's text content plus its catalog entry and
returns a list of :class:`Problem`s (empty list = valid). Problems carry a
severity: ``error`` fails ``agentscan validate``; ``warning`` only fails it
under ``--strict``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Dict, List

import yaml

from .detectors import Asset, AssetType

#: Warn when a skill description exceeds this many characters.
MAX_DESCRIPTION_LEN = 1024


@dataclass
class Problem:
    severity: str  # "error" | "warning"
    message: str


def err(message: str) -> Problem:
    return Problem("error", message)


def warn(message: str) -> Problem:
    return Problem("warning", message)


def parse_frontmatter(content: str):
    """Return (meta_dict_or_None, problem_or_None) for a leading YAML frontmatter block."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, err("missing YAML frontmatter (file must start with '---')")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return None, err("unterminated YAML frontmatter (no closing '---')")
    try:
        meta = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        return None, err(f"frontmatter is not valid YAML: {exc}")
    if not isinstance(meta, dict):
        return None, err("frontmatter is not a YAML mapping")
    return meta, None


def validate_frontmatter(content: str, asset_type: AssetType) -> List[Problem]:
    """Require a leading YAML frontmatter block with the catalog's required fields."""
    meta, problem = parse_frontmatter(content)
    if problem:
        return [problem]
    problems: List[Problem] = []
    for field_name in asset_type.required_fields:
        if field_name not in meta:
            problems.append(err(f"frontmatter field '{field_name}' is missing"))
            continue
        value = meta[field_name]
        if not isinstance(value, str) or not value.strip():
            problems.append(
                err(
                    f"frontmatter field '{field_name}' must be a non-empty string"
                    f" (got {type(value).__name__})"
                )
            )
    description = meta.get("description")
    if isinstance(description, str) and len(description) > MAX_DESCRIPTION_LEN:
        problems.append(
            warn(f"description is {len(description)} chars (> {MAX_DESCRIPTION_LEN}); consider trimming")
        )
    return problems


def validate_mcp_json(content: str, asset_type: AssetType) -> List[Problem]:
    """Require valid JSON with a non-empty 'mcpServers' mapping; warn on odd entries."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        return [err(f"not valid JSON: {exc}")]
    if not isinstance(data, dict) or "mcpServers" not in data:
        return [err("missing top-level 'mcpServers' object")]
    servers = data["mcpServers"]
    if not isinstance(servers, dict) or not servers:
        return [err("'mcpServers' must be a non-empty object")]
    problems: List[Problem] = []
    for name, entry in servers.items():
        if not isinstance(entry, dict) or not ({"command", "url"} & set(entry)):
            problems.append(warn(f"server '{name}' declares neither 'command' nor 'url'"))
    return problems


def validate_plugin_json(content: str, asset_type: AssetType) -> List[Problem]:
    """Require valid JSON with a non-empty string 'name'."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        return [err(f"not valid JSON: {exc}")]
    if not isinstance(data, dict):
        return [err("plugin manifest must be a JSON object")]
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return [err("plugin manifest field 'name' is missing or not a non-empty string")]
    return []


VALIDATORS: Dict[str, Callable[[str, AssetType], List[Problem]]] = {
    "frontmatter": validate_frontmatter,
    "mcp_json": validate_mcp_json,
    "plugin_json": validate_plugin_json,
}


def validate_asset(asset: Asset, asset_type: AssetType) -> List[Problem]:
    """Run the catalog-declared validator for *asset*; empty files always warn."""
    try:
        content = asset.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [err(f"unreadable: {exc}")]
    if not content.strip():
        return [warn("file is empty")]
    if not asset_type.validator:
        return []
    validator = VALIDATORS.get(asset_type.validator)
    if validator is None:
        return [
            err(
                f"catalog declares unknown validator '{asset_type.validator}'"
                f" (known: {', '.join(sorted(VALIDATORS))})"
            )
        ]
    return validator(content, asset_type)
