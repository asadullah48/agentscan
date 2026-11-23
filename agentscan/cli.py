"""agentscan command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import __version__
from .detectors import load_catalog, scan
from .fixers import fix_asset
from .rules import load_rules
from .sarif import ASSET_DETECTED, build_log
from .validators import validate_asset

FORMATS = ["table", "json", "sarif"]


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


def format_options(func):
    """Shared --format / --json options for scan and validate."""
    func = click.option("--json", "as_json", is_flag=True, help="Alias for --format json.")(func)
    return click.option(
        "--format",
        "fmt",
        type=click.Choice(FORMATS),
        default="table",
        show_default=True,
        help="Output format.",
    )(func)


def _resolve_format(fmt: str, as_json: bool) -> str:
    if as_json and fmt not in ("table", "json"):
        raise click.UsageError("--json conflicts with --format " + fmt)
    return "json" if as_json else fmt


def _emit_json(data) -> None:
    click.echo(json.dumps(data, indent=2))


@main.command("scan")
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@format_options
def scan_cmd(path: Path, fmt: str, as_json: bool) -> None:
    """Inventory the agent assets under PATH."""
    fmt = _resolve_format(fmt, as_json)
    assets = scan(path)
    if fmt == "json":
        _emit_json([{"type": a.type_id, "label": a.label, "path": a.rel_path} for a in assets])
        return
    if fmt == "sarif":
        results = [(ASSET_DETECTED["id"], "note", f"{a.label} ({a.type_id})", a.rel_path) for a in assets]
        _emit_json(build_log([ASSET_DETECTED], results))
        return
    if not assets:
        click.echo("No agent assets found.")
        return
    rows = [[a.label, a.rel_path] for a in assets]
    click.echo(_render_table(rows, ["TYPE", "PATH"]))
    click.echo(f"\n{len(assets)} asset(s) found.")


@main.command("validate")
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@format_options
@click.option(
    "--fail-on",
    type=click.Choice(["error", "warning"]),
    default="error",
    show_default=True,
    help="Lowest severity that makes the command exit 1.",
)
@click.option("--strict", is_flag=True, help="Alias for --fail-on warning.")
def validate_cmd(path: Path, fmt: str, as_json: bool, fail_on: str, strict: bool) -> None:
    """Validate the agent assets under PATH.

    Exit 0 when nothing at or above --fail-on was found, 1 otherwise,
    2 on usage errors. The exit code is the same for every --format.
    """
    fmt = _resolve_format(fmt, as_json)
    if strict:
        fail_on = "warning"
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
    if fmt == "json":
        _emit_json(
            [
                {
                    "type": r["type"],
                    "path": r["path"],
                    "problems": [
                        {"rule": p.rule, "severity": p.severity, "message": p.message}
                        for p in r["problems"]
                    ],
                }
                for r in results
            ]
        )
    elif fmt == "sarif":
        sarif_results = [(p.rule, p.severity, p.message, r["path"]) for r in results for p in r["problems"]]
        _emit_json(build_log(list(load_rules().values()), sarif_results))
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
                click.echo(f"       - ({problem.severity}) {problem.message} [{problem.rule}]")
        if results:
            click.echo(f"\n{len(results)} asset(s) checked: {errors} error(s), {warnings} warning(s).")
    if errors or (fail_on == "warning" and warnings):
        sys.exit(1)


@main.command("fix")
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Show what would be fixed without writing files.")
def fix_cmd(path: Path, dry_run: bool) -> None:
    """Apply safe, trivial repairs to frontmatter assets under PATH.

    Fixes only: a missing frontmatter block (skeleton with derived name and a
    TODO description) and a missing required 'name' field. Everything else is
    reported by `validate` and left to a human. Files whose real location is
    outside PATH (for example a symlink pointing elsewhere) are never written.
    """
    root = path.resolve()
    catalog = load_catalog()
    types_by_id = {t.id: t for t in catalog}
    assets = scan(path, catalog)
    fixed_count = 0
    for asset in assets:
        real = asset.path.resolve()
        if root not in real.parents:
            click.echo(f"[skipped] {asset.rel_path} (resolves outside {path})")
            continue
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
