"""Filesystem discovery of agent assets, driven by the packaged catalog.yaml."""

from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import yaml

#: Directories never descended into during a scan.
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
}


@dataclass
class AssetType:
    """One entry from catalog.yaml."""

    id: str
    label: str
    filenames: List[str] = field(default_factory=list)
    suffix: Optional[str] = None
    path_contains: Optional[str] = None
    validator: Optional[str] = None
    required_fields: List[str] = field(default_factory=list)

    def matches(self, rel_posix: str, basename: str, abs_posix: str) -> bool:
        if self.filenames:
            name_ok = basename in self.filenames
        elif self.suffix:
            name_ok = basename.endswith(self.suffix)
        else:
            name_ok = False
        if not name_ok:
            return False
        if self.path_contains:
            # Check both the root-relative and the absolute path, so assets are
            # still found when the scan root is at or inside the marker
            # directory (e.g. scanning `.claude/` directly). Leading slashes
            # anchor the marker at a path-segment boundary, so a directory
            # literally named `foo.claude/` cannot false-positive.
            haystacks = ("/" + rel_posix, abs_posix)
            return any(self.path_contains in h for h in haystacks)
        return True


@dataclass
class Asset:
    """A discovered agent asset."""

    type_id: str
    label: str
    path: Path  # absolute
    rel_path: str  # POSIX, relative to scan root


def load_catalog() -> List[AssetType]:
    """Load asset-type definitions from the catalog shipped inside the package."""
    raw = yaml.safe_load(files("agentscan").joinpath("catalog.yaml").read_text(encoding="utf-8"))
    known = {f.name for f in dataclasses.fields(AssetType)}
    types = []
    for entry in raw["asset_types"]:
        unknown = set(entry) - known
        if unknown:
            raise ValueError(
                f"catalog entry '{entry.get('id', '?')}' has unknown key(s): {sorted(unknown)}"
            )
        types.append(AssetType(**entry))
    return types


def scan(root: Path, catalog: Optional[List[AssetType]] = None) -> List[Asset]:
    """Walk *root* and return every file matching an asset type, sorted by path.

    Read-only: files are matched by name/location here; contents are only read
    later, by validators.
    """
    root = root.resolve()
    if catalog is None:
        catalog = load_catalog()

    found: List[Asset] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            abs_path = Path(dirpath) / name
            rel_posix = abs_path.relative_to(root).as_posix()
            abs_posix = abs_path.as_posix()
            for asset_type in catalog:
                if asset_type.matches(rel_posix, name, abs_posix):
                    found.append(
                        Asset(
                            type_id=asset_type.id,
                            label=asset_type.label,
                            path=abs_path,
                            rel_path=rel_posix,
                        )
                    )
                    break  # first matching type wins
    return found
