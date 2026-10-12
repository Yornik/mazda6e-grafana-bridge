#!/usr/bin/env python3
"""Print every PromQL query in a Grafana dashboard as a Prometheus rule file.

`promtool check rules` then parses each one, which is the cheapest way to have
the real PromQL parser reject a typo before Grafana shows an empty panel.
"""

from __future__ import annotations

import json
import sys

# Grafana template variables, replaced with something the parser accepts.
VARIABLES = {"$vin": ".*", "${vin}": ".*"}


def expressions(dashboard: dict) -> list[tuple[str, str]]:
    found = []
    for panel in dashboard.get("panels", []):
        for target in panel.get("targets", []):
            expr = target.get("expr")
            if expr:
                for name, value in VARIABLES.items():
                    expr = expr.replace(name, value)
                found.append((f"{panel['title']} / {target['refId']}", expr))
    return found


def main(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        dashboard = json.load(f)
    rules = [
        {"record": f"dashboard:query_{i}", "expr": expr, "labels": {"panel": where}}
        for i, (where, expr) in enumerate(expressions(dashboard))
    ]
    # JSON is valid YAML, and promtool reads either.
    json.dump({"groups": [{"name": "dashboard", "rules": rules}]}, sys.stdout, indent=2)


if __name__ == "__main__":
    main(sys.argv[1])
