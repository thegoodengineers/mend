"""The analyst's judge and keep rule (no model calls)."""

from mend.analyst_round import keep, question_words, task_words
from mend.analyst_suite import correct

NUM = {"kind": "number", "question": "How many?", "sql": "SELECT 12"}
PCT = {"kind": "number", "question": "What percent?", "sql": "SELECT -50.0"}
TXT = {"kind": "text", "question": "Which?", "sql": "SELECT 'office'"}


def test_judge():
    assert correct(NUM, "12") and correct(NUM, "There are 12 orders.") and not correct(NUM, "13") and not correct(NUM, None)
    assert correct(PCT, "-50.04%") and not correct(PCT, "50")
    assert correct(TXT, "'Office'") and not correct(TXT, "home")


def run(passed, tokens):
    return {"passed": sum(passed), "input_tokens": sum(tokens), "output_tokens": 0,
            "tasks": [{"task_id": f"A{i}", "passed": p, "input_tokens": t, "output_tokens": 0}
                      for i, (p, t) in enumerate(zip(passed, tokens))]}


def test_keep():
    before = run([True] * 10, [1000] * 10)
    assert keep(before, run([True] * 10, [700] * 10))[0]          # same answers, 30% cheaper everywhere
    assert not keep(before, run([True] * 10, [900] * 10))[0]      # only 10% cheaper
    assert not keep(before, run([False] + [True] * 9, [500] * 10))[0]  # cheaper but lost an answer
    assert keep(run([False] + [True] * 9, [1000] * 10), run([True] * 10, [1100] * 10))[0]  # one more right


def test_guard_words():
    assert {"office", "toaster", "usa"} <= task_words()


def test_guard_boundaries():
    hit = question_words
    assert hit("+check token usage before finishing") == [] and hit("+filter to USA only") == ["usa"]
    assert hit("+where order_date >= '2025-12-01'") == ["2025-"]


def test_heldout_database():
    import json
    from mend.analyst_suite import HELDOUT
    tasks = {t["id"]: t for t in json.loads(HELDOUT[0].read_text(encoding="utf-8"))}
    assert correct(tasks["H07"], "8", HELDOUT[1]) and not correct(tasks["H07"], "2", HELDOUT[1])  # judged on clinic.db
