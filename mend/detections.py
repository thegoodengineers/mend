"""Regression guards: turn a diagnosed failure into a neatlogs detection, so neatlogs flags it from now on.

    python -m mend.detections preview   # dry-run the built-in guards against recent traces
    python -m mend.detections create    # create the ones that match real spans
    python -m mend.detections trend     # occurrence counts of every guard (7 days, by day)

A guard is a regex detection on one span name (a worker tool, or the task WORKFLOW span). Following
the neatlogs MCP contract, every guard is dry-run with preview_detection first and created only if
it flags at least one real span.
"""

import asyncio
import json
import sys

from mend.traces import _call

GROUP = "Mend regression guards"

# Failures Mend has already diagnosed in its own traces (runs/*.diagnosis.md, evidence/).
KNOWN_GUARDS = [
    {"display_name": "Mend: test suite timed out", "span_name": "run_tests",
     "output_pattern": "pytest timed out",
     "description": "run_tests hit its timeout; the worker must locate the hang instead of re-running (task 29)."},
    {"display_name": "Mend: edit_file text not found", "span_name": "edit_file",
     "output_pattern": "not found in file",
     "description": "The worker's edit did not match the file; usually it edited from a stale or partial read."},
    {"display_name": "Mend: task hit the turn limit", "span_name": "solve_task",
     "output_pattern": "max_turns",
     "description": "A worker task ran out of turns (15) without finishing."},
]


def _run(tool: str, args: dict) -> dict:
    return asyncio.run(_call(tool, args))


def _regex(guard: dict) -> tuple[dict, dict]:
    config = {k: guard[k] for k in ("input_pattern", "output_pattern") if guard.get(k)}
    run_on = {"frequency": "span_name", "span_names": [guard["span_name"]]}
    return config, run_on


def group_id() -> str:
    groups = _run("list_detection_groups", {})
    for g in groups if isinstance(groups, list) else groups.get("groups", []):
        if g.get("name") == GROUP:
            return g["id"]
    created = _run("create_detection_group", {"name": GROUP})
    return created.get("id") or created.get("group", {}).get("id")


def preview(guard: dict, days: int = 14) -> int:
    config, run_on = _regex(guard)
    result = _run("preview_detection", {"type": "regex", "config": config, "run_on": run_on,
                                        "timeframe_days": days, "limit": 5})
    return int(result.get("total_count", 0))


def existing_names() -> set[str]:
    listed = _run("list_detections", {})
    items = listed if isinstance(listed, list) else listed.get("detections", [])
    return {d.get("display_name") or d.get("name") for d in items}


def create(guard: dict, gid: str) -> dict:
    """Create the guard if it matches real spans and doesn't exist yet. Returns what happened."""
    if guard["display_name"] in existing_names():
        return {"guard": guard["display_name"], "status": "exists"}
    hits = preview(guard)
    if hits == 0:
        return {"guard": guard["display_name"], "status": "skipped: matches no recent spans"}
    config, run_on = _regex(guard)
    _run("create_detection", {"display_name": guard["display_name"], "group_id": gid, "type": "regex",
                              "config": config, "run_on": run_on, "description": guard["description"]})
    return {"guard": guard["display_name"], "status": "created", "matched_spans": hits}


def trend(name: str) -> dict:
    return _run("get_detection_trend", {"detection_name": name, "period": "7d", "granularity": "day"})


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if action == "preview":
        for g in KNOWN_GUARDS:
            print(f"{g['display_name']}: {preview(g)} matching spans (14 days)")
    elif action == "create":
        gid = group_id()
        for g in KNOWN_GUARDS:
            print(json.dumps(create(g, gid)))
    elif action == "trend":
        for g in KNOWN_GUARDS:
            print(g["display_name"], json.dumps(trend(g["display_name"]))[:400])
