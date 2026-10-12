"""The dashboard is only useful if it asks for metrics the exporter publishes."""

from __future__ import annotations

import json
import re
from pathlib import Path

from prometheus_client import REGISTRY

from mazda6e_bridge import metrics  # noqa: F401 - registers the gauges
from scripts.dashboard_rules import expressions

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboards" / "mazda6e.json"


def load():
    return json.loads(DASHBOARD.read_text(encoding="utf-8"))


def exported_names() -> set[str]:
    return {m.name for m in REGISTRY.collect() if m.name.startswith("mazda6e_")}


def test_every_queried_metric_is_exported():
    queried = set()
    for _, expr in expressions(load()):
        queried |= set(re.findall(r"\bmazda6e_[a-z0-9_]+", expr))
    assert queried, "dashboard has no mazda6e queries"
    assert queried - exported_names() == set()


def test_panel_ids_are_unique_and_layout_does_not_overlap():
    panels = load()["panels"]
    ids = [p["id"] for p in panels]
    assert len(ids) == len(set(ids))

    cells = set()
    for p in panels:
        g = p["gridPos"]
        assert g["x"] + g["w"] <= 24, p["title"]
        for x in range(g["x"], g["x"] + g["w"]):
            for y in range(g["y"], g["y"] + g["h"]):
                assert (x, y) not in cells, f"{p['title']} overlaps another panel"
                cells.add((x, y))


def test_dashboard_is_portable():
    dashboard = load()
    assert dashboard["id"] is None
    assert dashboard["uid"] == "mazda6e-bridge"
    for panel in dashboard["panels"]:
        if panel["type"] != "row":
            assert panel["datasource"]["uid"] == "${datasource}", panel["title"]
