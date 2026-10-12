"""The harness around the worker (task runner, stats, patch guard): robustness, no API keys needed."""

import json
import math
import os

import pytest

from mend import stats, tasks


def test_task_word_guard_matches_whole_words_only():
    from mend.supervisor import mentions_task_code
    assert mentions_task_code("+ handle invoice aging buckets")
    assert mentions_task_code("+ see Money.py for rounding")  # file names match anywhere
    assert mentions_task_code("+ use ROUND_HALF_UP")
    assert not mentions_task_code("+ when managing several edits, batch them")  # contains "aging"
    assert not mentions_task_code("+ an interesting failure mode")  # contains "interest"
    assert not mentions_task_code("+ staging, messaging, averaging, imaging")


def test_round_stats_survives_a_task_that_raised(tmp_path, monkeypatch):
    monkeypatch.setattr(stats, "RUNS", tmp_path)
    ok = {"passed": True, "input_tokens": 100, "output_tokens": 10}
    (tmp_path / "b.json").write_text(json.dumps({"tasks": [{"task_id": "T1", **ok}, {"task_id": "T2", **ok}]}))
    (tmp_path / "a.json").write_text(json.dumps({"tasks": [
        {"task_id": "T1", **ok}, {"task_id": "T2", "passed": False, "stop": "exception", "error": "APIError"}]}))
    r = stats.round_stats({"before": "b", "after": "a", "kept": None})
    assert r["broke"] == 1 and r["tasks"] == 2
    assert r["token_ratio"] == 0.5


def test_token_ratio_with_nothing_to_compare_is_not_a_win():
    ratio, lo, hi = stats.token_ratio_ci([])
    assert math.isnan(ratio) and math.isnan(hi)
    assert not hi < 1.0  # the gate's "interval entirely below 1" test must not pass on no evidence
    ratio, lo, hi = stats.token_ratio_ci([(0, 5), (0, 7)])
    assert math.isnan(ratio)


def test_prepare_cleans_up_when_a_task_is_malformed(tmp_path, monkeypatch):
    import tempfile
    made = []
    real = tempfile.mkdtemp

    def tracking_mkdtemp(*a, **k):
        made.append(real(*a, **k))
        return made[-1]

    monkeypatch.setattr(tempfile, "mkdtemp", tracking_mkdtemp)
    task = {"id": "BAD", "edits": [{"file": "invoicer/money.py", "find": "this text is not in the file", "replace": ""}]}
    with pytest.raises(ValueError):
        tasks.prepare(task)
    assert made and not any(os.path.exists(p) for p in made)


def test_run_tests_reports_a_timeout(tmp_path):
    (tmp_path / "test_slow.py").write_text("import time\n\ndef test_hang():\n    time.sleep(30)\n")
    ok, out = tasks.run_tests(tmp_path, timeout=3)
    assert not ok and "timed out" in out


def test_run_tests_round_trips_non_ascii_output(tmp_path):
    (tmp_path / "test_text.py").write_text(
        'def test_city():\n    assert "Ærøskøbing – Malmö “quoted”" == "x"\n', encoding="utf-8")
    ok, out = tasks.run_tests(tmp_path)
    assert not ok
    assert "Ærøskøbing" in out and "“quoted”" in out


def test_detection_lookups_accept_a_bare_list(monkeypatch):
    from mend import detections
    monkeypatch.setattr(detections, "_run", lambda tool, args: [{"name": detections.GROUP, "id": "g1",
                                                                  "display_name": "Mend: x"}])
    assert detections.group_id() == "g1"
    assert detections.existing_names() == {"Mend: x"}
