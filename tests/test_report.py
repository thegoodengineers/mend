from mend.report import render


def test_report_renders_rounds_and_task_grid():
    page = render()
    assert "<title>Mend report</title>" in page and "Tasks across runs" in page


def test_demo_data_names_the_fix_and_the_failing_tasks_cause():
    import json
    from mend.report import _demo_data, load_rounds, load_runs
    from mend.tasks import load_tasks
    raw = _demo_data(load_rounds(), load_runs(), load_tasks())
    assert "</" not in raw  # safe inside <script>
    d = json.loads(raw)
    assert d["failing_task"] == "23" and d["title"] and d["diagnosis"].startswith("Failing step:")
    assert d["checkpoint_url"] == ""  # round 1's checkpoint is not published
