"""agentscan command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import __version__
from .detectors import load_catalog, scan
from .fixers import fix_asset
from .validators import validate_asset


@click.group()
@click.version_option(version=__version__, prog_name="agentscan")
def main() -> None:
    """Discover, inventory, and validate AI-agent assets in a directory tree."""


def _render_table(rows, headers) -> str:
    widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    lines = [fmt.format(*headers), fmt.format(*("-" * w for w in widths))]
    lines.extend(fmt.format(*(str(c) for c in row)) for row in rows)
    return "\n".join(lines)


@main.command("scan")
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def scan_cmd(path: Path, as_json: bool) -> None:
    """Inventory the agent assets under PATH."""
    assets = scan(path)
    if as_json:
        click.echo(
            json.dumps(
                [{"type": a.type_id, "label": a.label, "path": a.rel_path} for a in assets],
                indent=2,
            )
        )
        return
    if not assets:
        click.echo("No agent assets found.")
        return
    rows = [[a.label, a.rel_path] for a in assets]
    click.echo(_render_table(rows, ["TYPE", "PATH"]))
    click.echo(f"\n{len(assets)} asset(s) found.")


@main.command("validate")
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option("--strict", is_flag=True, help="Treat warnings as failures too.")
def validate_cmd(path: Path, as_json: bool, strict: bool) -> None:
    """Validate the agent assets under PATH; exit 1 on errors (and warnings with --strict)."""
    catalog = load_catalog()
    types_by_id = {t.id: t for t in catalog}
    assets = scan(path, catalog)
    results = []
    errors = warnings = 0
    for asset in assets:
        problems = validate_asset(asset, types_by_id[asset.type_id])
        errors += sum(1 for p in problems if p.severity == "error")
        warnings += sum(1 for p in problems if p.severity == "warning")
        results.append({"type": asset.type_id, "path": asset.rel_path, "problems": problems})
    if as_json:
        click.echo(
            json.dumps(
                [
                    {
                        "type": r["type"],
                        "path": r["path"],
                        "problems": [
                            {"severity": p.severity, "message": p.message} for p in r["problems"]
                        ],
                    }
                    for r in results
                ],
                indent=2,
            )
        )
    else:
        if not results:
            click.echo("No agent assets found.")
        for res in results:
            if any(p.severity == "error" for p in res["problems"]):
                worst = "FAIL"
            elif res["problems"]:
                worst = "WARN"
            else:
                worst = "OK"
            click.echo(f"[{worst:<4}] {res['path']}")
            for problem in res["problems"]:
                click.echo(f"       - ({problem.severity}) {problem.message}")
        if results:
            click.echo(f"\n{len(results)} asset(s) checked: {errors} error(s), {warnings} warning(s).")
    if errors or (strict and warnings):
        sys.exit(1)


@main.command("fix")
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Show what would be fixed without writing files.")
def fix_cmd(path: Path, dry_run: bool) -> None:
    """Apply safe, trivial repairs to frontmatter assets under PATH.

    Fixes only: a missing frontmatter block (skeleton with derived name and a
    TODO description) and a missing required 'name' field. Everything else is
    reported by `validate` and left to a human.
    """
    catalog = load_catalog()
    types_by_id = {t.id: t for t in catalog}
    assets = scan(path, catalog)
    fixed_count = 0
    for asset in assets:
        fixes = fix_asset(asset, types_by_id[asset.type_id], apply=not dry_run)
        if fixes:
            fixed_count += 1
            verb = "would fix" if dry_run else "fixed"
            click.echo(f"[{verb}] {asset.rel_path}")
            for fix in fixes:
                click.echo(f"       - {fix}")
    if fixed_count == 0:
        click.echo("Nothing to fix.")
    else:
        click.echo(f"\n{fixed_count} asset(s) {'would be ' if dry_run else ''}fixed.")
