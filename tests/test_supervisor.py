from mend.supervisor import trace_digest


def test_trace_digest_lists_tree_then_truncated_span_io():
    trace = {"spans": [
        {"span_id": "a", "parent_span_id": "", "type": "workflow", "name": "solve_task", "status": "SUCCESS", "duration_ms": 10},
        {"span_id": "b", "parent_span_id": "a", "type": "tool_call", "name": "run_tests", "status": "SUCCESS",
         "duration_ms": 5, "input_value": "{}", "output_value": "FAILED " + "x" * 5000},
    ]}
    text = trace_digest(trace)
    assert text.startswith("workflow solve_task [SUCCESS] 10ms\n  tool_call run_tests")
    assert "out: FAILED x" in text and len(text) < 1200


def test_rounds_chain_kept_runs_and_stop_at_first_revert(monkeypatch):
    import mend.supervisor as sup
    outcomes = iter([True, True, False, True])
    seen = []

    def fake_round(run_id):
        seen.append(run_id)
        return {"kept": next(outcomes), "after": run_id + "+"}

    monkeypatch.setattr(sup, "one_round", fake_round)
    records = sup.rounds("r0", limit=5)
    assert seen == ["r0", "r0+", "r0++"] and [r["kept"] for r in records] == [True, True, False]


def test_repair_history_lists_kept_reverted_and_rejected(tmp_path, monkeypatch):
    import json
    import mend.supervisor as sup
    (tmp_path / "a.round.json").write_text(json.dumps({"title": "Add edit tool", "kept": True, "commit": "abc",
        "before_passed": 27, "after_passed": 28, "total": 28, "before_tokens": 900, "after_tokens": 800}))
    (tmp_path / "b.round.json").write_text(json.dumps({"title": "Shorter prompt", "kept": False, "commit": "def",
        "before_passed": 29, "after_passed": 28, "total": 29, "before_tokens": 500, "after_tokens": 450}))
    (tmp_path / "c.rejected.round.json").write_text(json.dumps({"title": "Hack", "rejected": True, "kept": False,
        "reason": "patch mentions specific library code"}))
    monkeypatch.setattr(sup, "RUNS", tmp_path)
    monkeypatch.setattr(sup, "_entire_files", lambda sha: "mend/worker.py" if sha == "abc" else "")
    lines = sup.repair_history().splitlines()
    assert lines[0].startswith("- KEPT: Add edit tool") and "Entire checkpoint shows it changed mend/worker.py" in lines[0]
    assert lines[1].startswith("- REVERTED: Shorter prompt")
    assert lines[2] == "- REJECTED before running: Hack (reason: patch mentions specific library code)"


def test_choice_stops_before_patching_and_answer_becomes_precedent(tmp_path, monkeypatch):
    import json
    import mend.supervisor as sup
    (tmp_path / "r1.json").write_text(json.dumps({"tasks": [], "passed": 1, "total": 1}))
    fix = {"title": "Verify less", "target_file": "mend/worker.py", "instructions": "x", "why_general": "y",
           "guard": {}, "judgment": {"is_choice": True, "question": "Run the full suite or only the failing test?",
                                     "precedent_used": ""}}
    monkeypatch.setattr(sup, "RUNS", tmp_path)
    monkeypatch.setattr(sup, "PRECEDENTS", tmp_path / "precedents.json")
    monkeypatch.setattr(sup, "git", lambda *a: "")
    monkeypatch.setattr(sup, "write_diagnosis", lambda run_id, d: "runs/r1.diagnosis.md")
    monkeypatch.setattr(sup, "diagnose_failures", lambda run_id: {"failures": [], "fix": fix})
    monkeypatch.setattr(sup, "apply_patch", lambda *a: (_ for _ in ()).throw(AssertionError("must not patch")))
    record = sup.one_round("r1")
    assert record["needs_human"] and (tmp_path / "r1.question.json").exists()
    sup.answer("r1", "Always run the full suite.")
    assert sup.precedents() == [{"question": "Run the full suite or only the failing test?",
                                 "answer": "Always run the full suite.", "asked_in": "r1"}]
    monkeypatch.setattr(sup, "one_round", lambda run_id: record)
    assert len(sup.rounds("r1", limit=3)) == 1  # a pending question stops the chain


def test_gate_amendment_rejects_regressions_and_noisy_token_wins():
    from mend.supervisor import gate
    run = lambda passed, tok: {"passed": passed, "input_tokens": tok, "output_tokens": 0}  # noqa: E731
    ok = {"broke": 0, "ci_high": 0.9}
    assert gate(run(28, 100), run(29, 100), ok)                          # more pass
    assert not gate(run(28, 100), run(29, 100), {**ok, "broke": 1})      # ...but one broke
    assert gate(run(29, 100), run(29, 80), ok)                           # 20% cheaper, holds per task
    assert not gate(run(29, 100), run(29, 80), {**ok, "ci_high": 1.05})  # cheaper only in the total
    assert not gate(run(29, 100), run(29, 90), ok)                       # 10% is under the threshold


def test_second_diagnosis_of_a_run_gets_a_fresh_name(tmp_path, monkeypatch):
    import mend.supervisor as sup
    monkeypatch.setattr(sup, "RUNS", tmp_path)
    assert sup.fresh_stem("r1") == "r1"
    (tmp_path / "r1.diagnosis.md").write_text("round 7")
    (tmp_path / "r1-d2.diagnosis.md").write_text("round 8")
    assert sup.fresh_stem("r1") == "r1-d3"


def test_audit_rules_agree_with_every_recorded_decision():
    from mend.audit import checks, rounds
    for n, r in rounds():
        met = {rule: ok for rule, ok, _ in checks(r)}
        base = met["more tasks pass"] or met["same tasks pass with >=15% fewer tokens"]
        amended = all(ok for rule, ok in met.items() if rule.startswith("amendment"))
        assert (base and amended) == r["kept"], n


def test_entire_search_repeat_guard(tmp_path, monkeypatch):
    import json
    import mend.supervisor as sup
    (tmp_path / "a.round.json").write_text(json.dumps({"commit": "49c99e2", "kept": False, "title": "batch edits"}))
    (tmp_path / "b.round.json").write_text(json.dumps({"commit": "e8a6baf", "kept": True, "title": "edit tool"}))
    monkeypatch.setattr(sup, "RUNS", tmp_path)
    hits = {"batch edits again": [{"id": "49c99e27e4", "score": 94.6}], "weak match": [{"id": "49c99e27e4", "score": 42.7}],
            "edit tool again": [{"id": "e8a6baf63c", "score": 99.0}]}
    monkeypatch.setattr(sup, "entire_search", lambda text: hits.get(text, []))
    assert "49c99e2" in sup.repeats_reverted_fix("batch edits again")
    assert sup.repeats_reverted_fix("weak match") == ""      # below the calibrated score
    assert sup.repeats_reverted_fix("edit tool again") == ""  # a kept fix is not a failed one
    assert sup.repeats_reverted_fix("no entire") == ""        # Entire unavailable: never blocks


def test_gate_amendment_3_rejects_more_test_gaming():
    from mend.supervisor import gate
    ok = {"broke": 0, "ci_high": 0.9}
    run = lambda passed, gamed: {"passed": passed, "input_tokens": 100, "output_tokens": 0,  # noqa: E731
                                 "tasks": [{"audit": {"verdict": "gamed" if i < gamed else "restored"}} for i in range(passed)]}
    assert gate(run(8, 0), run(9, 0), ok)          # more pass, no gaming
    assert not gate(run(8, 0), run(9, 1), ok)      # more pass, but one more gamed fix
    plain = {"passed": 8, "input_tokens": 100, "output_tokens": 0, "tasks": [{}] * 8}
    assert gate(plain, run(9, 1), ok)              # no audit before: not applied
