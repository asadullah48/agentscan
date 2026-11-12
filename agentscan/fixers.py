"""Safe, trivial repairs for frontmatter-validated assets.

Only two fixes are considered safe enough to automate; anything else (broken
YAML, unterminated frontmatter, malformed JSON) is deliberately left to a
human:

* missing frontmatter block entirely -> prepend a skeleton with a derived
  ``name`` and a ``TODO`` description;
* frontmatter present but ``name`` missing -> insert a derived ``name``.

The derived name is the parent directory for SKILL.md files (skills live in a
directory named after them) and the file stem otherwise.
"""

from __future__ import annotations

from typing import List

from .detectors import Asset, AssetType
from .validators import parse_frontmatter

TODO_DESCRIPTION = "TODO - describe this asset"


def derive_name(asset: Asset) -> str:
    if asset.path.name == "SKILL.md":
        return asset.path.parent.name
    return asset.path.stem


def fix_asset(asset: Asset, asset_type: AssetType, apply: bool = True) -> List[str]:
    """Return descriptions of fixes (applied unless *apply* is False)."""
    if asset_type.validator != "frontmatter":
        return []
    try:
        content = asset.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    fixes: List[str] = []
    new_content = content
    meta, problem = parse_frontmatter(content)

    if problem and problem.message.startswith("missing YAML frontmatter"):
        name = derive_name(asset)
        skeleton = f"---\nname: {name}\n"
        if "description" in asset_type.required_fields:
            skeleton += f"description: {TODO_DESCRIPTION}\n"
        skeleton += "---\n"
        new_content = skeleton + content
        fixes.append(f"added frontmatter skeleton (name: {name})")
    elif meta is not None and "name" in asset_type.required_fields and "name" not in meta:
        name = derive_name(asset)
        lines = new_content.splitlines(keepends=True)
        lines.insert(1, f"name: {name}\n")
        new_content = "".join(lines)
        fixes.append(f"inserted frontmatter field name: {name}")

    if fixes and apply:
        asset.path.write_text(new_content, encoding="utf-8")
    return fixes
