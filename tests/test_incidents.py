"""mend.incidents: map neatlogs' linked traces to run files and apply its turn check (no network)."""

from mend.incidents import check


def run(file, commit, turns):
    return {"file": file, "worker_commit": commit,
            "tasks": [{"task_id": t, "trace_id": f"{commit}-{t}", "turns": n, "passed": True} for t, n in turns.items()]}


def test_check_applies_neatlogs_threshold_to_original_and_fresh_runs():
    runs = [run("runs/a-v0.json", "13defdb", {"SC04": 9, "SC07": 10, "SC01": 2}),
            run("runs/a.json", "90b7284", {"SC04": 3}),
            run("runs/incident/b.json", "0992b53", {"SC04": 3, "SC07": 4, "SC01": 3})]
    card = {"triage_id": "x", "title": "slow", "severity": "medium", "status": "open", "created_at": "2026-10-11T11:54",
            "root_cause": "", "linked_trace_ids": ["13defdb-SC04", "13defdb-SC07", "90b7284-SC04"],
            "recommended_action": {"verification": ["Verify that the average number of turns decreases below 5."]}}
    r = check(card, runs)
    assert r["tasks"] == ["SC04", "SC07"] and r["check"].endswith("below 5")
    assert r["original"]["mean_turns"] == 9.5 and not r["original"]["meets_check"]   # only the flagged worker's runs
    assert r["current"]["mean_turns"] == 3.5 and r["current"]["meets_check"] and r["current"]["slow_share"] == 0.0
