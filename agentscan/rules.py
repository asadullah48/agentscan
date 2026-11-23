"""The rule catalog (``rules:`` in catalog.yaml) and the docs/RULES.md generator.

Regenerate the doc with ``python -m agentscan.rules`` from the repository root.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from .detectors import load_catalog, read_catalog

RULE_KEYS = {"id", "severity", "applies_to", "check", "fix"}
SEVERITIES = {"error", "warning"}
DOC_PATH = Path("docs") / "RULES.md"


@lru_cache(maxsize=None)
def load_rules() -> Dict[str, dict]:
    """Return catalog rules keyed by id, in catalog order. Raises on malformed entries."""
    rules: Dict[str, dict] = {}
    for entry in read_catalog()["rules"]:
        if set(entry) != RULE_KEYS:
            raise ValueError(f"rule '{entry.get('id', '?')}' must have exactly the keys {sorted(RULE_KEYS)}")
        if entry["severity"] not in SEVERITIES:
            raise ValueError(f"rule '{entry['id']}' has unknown severity '{entry['severity']}'")
        if entry["id"] in rules:
            raise ValueError(f"duplicate rule id '{entry['id']}'")
        rules[entry["id"]] = entry
    return rules


def _applies_to(validator: str) -> str:
    if validator == "all":
        return "All assets"
    labels = [t.label for t in load_catalog() if t.validator == validator]
    return ", ".join(labels) or f"(no asset type uses `{validator}`)"


def render_markdown() -> str:
    """Render docs/RULES.md from the catalog."""
    rules: List[dict] = list(load_rules().values())
    lines = [
        "# Rule catalog",
        "",
        "<!-- Generated from agentscan/catalog.yaml by `python -m agentscan.rules`. Do not edit by hand. -->",
        "",
        "Every check `agentscan validate` can report. `error` fails validation;"
        " `warning` fails only with `--fail-on warning`."
        " Rule ids appear in `--format json` (`rule`) and `--format sarif` (`ruleId`).",
        "",
        f"{len(rules)} rules: {sum(r['severity'] == 'error' for r in rules)} errors,"
        f" {sum(r['severity'] == 'warning' for r in rules)} warnings.",
        "",
        "| Rule | Severity | Applies to | Check | Fix |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rules:
        cells = [f"`{r['id']}`", r["severity"], _applies_to(r["applies_to"]), r["check"], r["fix"]]
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m agentscan.rules", description="Generate the rule catalog doc.")
    parser.add_argument("output", nargs="?", type=Path, default=DOC_PATH, help=f"output file (default: {DOC_PATH})")
    out = parser.parse_args(argv).output
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as fh:  # write_text(newline=) is 3.10+
        fh.write(render_markdown())
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
