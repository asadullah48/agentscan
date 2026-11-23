"""SARIF 2.1.0 output, for GitHub code scanning and other SARIF consumers."""

from __future__ import annotations

from typing import Iterable, List, Tuple
from urllib.parse import quote

from . import __version__

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"

#: Pseudo-rule for `scan` results: discovery is an inventory, not a check.
ASSET_DETECTED = {
    "id": "asset-detected",
    "severity": "note",
    "check": "An agent asset was found by the catalog.",
    "fix": "None needed; this is an inventory entry.",
}

#: (rule_id, level, message, root-relative POSIX path)
Result = Tuple[str, str, str, str]


def build_log(rules: List[dict], results: Iterable[Result]) -> dict:
    """Return a SARIF log with one run. URIs stay relative to the scanned root."""
    index = {rule["id"]: i for i, rule in enumerate(rules)}
    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "agentscan",
                        "version": __version__,
                        "informationUri": "https://github.com/asadullah48/agentscan",
                        "rules": [
                            {
                                "id": rule["id"],
                                "shortDescription": {"text": rule["check"]},
                                "help": {"text": rule["fix"]},
                                "defaultConfiguration": {"level": rule["severity"]},
                            }
                            for rule in rules
                        ],
                    }
                },
                "results": [
                    {
                        "ruleId": rule_id,
                        "ruleIndex": index[rule_id],
                        "level": level,
                        "message": {"text": message},
                        "locations": [
                            {"physicalLocation": {"artifactLocation": {"uri": quote(path)}}}
                        ],
                    }
                    for rule_id, level, message, path in results
                ],
            }
        ],
    }
