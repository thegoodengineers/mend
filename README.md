# Mend

**An agent that reads its own [neatlogs](https://neatlogs.com) traces, fixes its own code, and
keeps the fix only if a full re-run gets better.** Built during
[neatHack](https://neatlogs.com/hackathon), 10–12 October 2026, by team The Good Engineers.

**Website:** https://thegoodengineers.github.io/mend/ · **Full data report:**
[report.html](https://thegoodengineers.github.io/mend/report.html) · **Build log:**
[hackathon.md](hackathon.md)

**Demo video (2:43):** [`video/demo/mend-demo.mp4`](video/demo/mend-demo.mp4) · **Keep/revert rules:** [`docs/GATE.md`](docs/GATE.md) · **Evidence index:** [`evidence/INDEX.md`](evidence/INDEX.md)

[![Mend website](docs/img/site-hero.png)](https://thegoodengineers.github.io/mend/)

[![Live recording: original worker fails, repaired worker passes](docs/img/live-result.png)](video/live/mend-live.mp4)
*Live recording (1:55, click): same task, same model. Original worker failed in 15 turns; after
self-repair it passed in 4.*

Every number in this README comes from a file in [`runs/`](runs/) or [`evidence/`](evidence/).
If a number has no file behind it, it is not here.

## For judges: 60 seconds

| neatHack evidence item | Where to check it |
|---|---|
| The agent improved (before/after with numbers) | [rounds table](#self-repair-rounds-five-kept-three-reverted), [3-vs-3 repeat runs](#repeatable-not-lucky-same-28-tasks-3-runs-each), [held-out test](#held-out-test-10-bugs-the-supervisor-never-saw), [real-world library](#real-world-test-bugs-in-an-open-source-library-it-never-saw); [live recording](video/live/mend-live.mp4) |
| You used neatlogs | [traced call](evidence/t02-first-traced-call.txt), [trace read back over MCP](evidence/t04-trace-readback.txt), [task 23 before](evidence/task23-before-trace.json) / [after](evidence/task23-after-trace.json) traces; 4 regression-guard detections ([`mend/detections.py`](mend/detections.py)); every gate verdict is also written back into neatlogs as a `mend-gate` trace, one span per keep rule, and a detection flags each revert ([`mend/audit.py`](mend/audit.py), [read-back](evidence/gate-audit-readback.md)); second opinion from neatlogs' own [neatroots](evidence/neatroots-check.md): a custom check flags all 4 original-worker runs and none of the repaired ones |
| You used Entire | [round 4 checkpoint](https://entire.io/gh/thegoodengineers/mend/commit/7e2148e201fdaa9b2b3f921d1f2651950f537205) (the supervisor's own Claude Code session); the supervisor reads past checkpoints back as repair memory; [who wrote the worker](https://thegoodengineers.github.io/mend/#provenance): `entire blame` shows 69% of the worker's prompt was written by Mend's own sessions |
| You used cfo.ai | [business plan](docs/business-plan.md) and its [cfo.ai export](docs/business-plan-cfo-ai.xlsx) |
| The improvement is real, not noise | [paired statistics per decision](#self-repair-rounds-five-kept-three-reverted) (rounds 3–5 solid; rounds 1–2 rest on one task flip, said plainly); [leave-one-out ablation](evidence/ablation.json) (removing round 5: +61% tokens); 2 fixes reverted by the gate; re-check every decision [in your browser](https://thegoodengineers.github.io/mend/#verify) |
| It knows when not to fix itself | [ask once, remember](#is-self-healing-self-defeating): a fix that is a choice stops for a person, and the answer becomes a precedent (answers neatlogs' "Self-healing is self-defeating") |
| The agent recovers from failures | [run_tests timed out, then fixed](evidence/t17-recovery-from-timeout.txt); in the live recording a tool call fails ("Permission denied") and the worker carries on |
| You built in public | [first #neatHack post](https://x.com/theintrodev/status/2108851736765141188) |
| Code written during the hackathon | [commit history](https://github.com/thegoodengineers/mend/commits/main) (first commit: plans only, as the rules allow) |

Every number in this README is recomputed from the run files by [`mend/verify.py`](mend/verify.py) on
every push ([CI](https://github.com/thegoodengineers/mend/actions)).

## How it works

```
worker agent ──runs 29 tasks──▶ neatlogs traces every model call and tool call
      ▲                                   │
      │                                   ▼  (neatlogs MCP: get_trace_context)
 keep or revert ◀── re-run the suite ◀── supervisor diagnoses failed + wasteful runs
                                          │
                                          ▼
                     Claude Code applies ONE general fix to the worker,
                     committed and captured as an Entire checkpoint
```

1. **Run.** A worker agent ([`mend/worker.py`](mend/worker.py), Claude Haiku 4.5) fixes planted
   bugs in a small invoicing library ([`sandbox/`](sandbox/), 37 tests). There are 29 tasks in
   [`tasks/tasks.json`](tasks/tasks.json). Pass means the library's test suite passes, judged
   by the runner, not by the agent.
2. **Trace.** Every model call and tool call is a span in neatlogs (one WORKFLOW span per task,
   TOOL spans per tool call). Each run file stores the task's neatlogs trace ID.
3. **Diagnose.** The supervisor ([`mend/supervisor.py`](mend/supervisor.py), Claude Opus 5.5)
   pulls the traces of failed tasks and the slowest passing tasks back over the neatlogs MCP
   server ([`mend/traces.py`](mend/traces.py)). It writes a diagnosis naming the failing step
   and one general fix.
4. **Patch.** Headless Claude Code applies the fix to `mend/worker.py` or
   `mend/prompts/worker.md` only. A guard rejects patches that touch other files or name
   specific library code.
5. **Prove.** The suite re-runs. The patch is kept if more tasks pass, or the same tasks pass
   with at least 15% fewer tokens. Otherwise it is reverted with `git revert`.

### Is self-healing self-defeating?

neatlogs' founder argues that a loop which fixes every mistake drifts toward the median, unless
someone defines what "better" means
([Self-healing is self-defeating](https://neatlogs.com/blog/self-healing-is-self-defeating)).
His prescription has three steps: automate everything that isn't a choice, ask someone when it
is, and remember the answer. Here is where Mend stands on each:

- **Automate what isn't a choice.** Mend only repairs things with an objective answer. The
  library's own test suite judges each task, the runner does the judging (not the agent), and
  token cost is counted by the API. Mend never repairs taste, tone or policy.
- **"Better" is defined by people.** The keep rule is code we wrote (`one_round()` in
  [`mend/supervisor.py`](mend/supervisor.py)), written out in [`docs/GATE.md`](docs/GATE.md).
  The supervisor may not change it, because only two files may change. Rounds 6, 7 and 8 show
  the gate saying no.
- **Remember the answer.** Every round, whether kept, reverted or rejected, is a record in
  `runs/`, and the Claude Code session behind each fix is an Entire checkpoint. Both are fed back
  into the next diagnosis, so a failed fix is not proposed again.
- **Ask someone when it is a choice** (added 11 Oct, `6a3b2c2`). Every diagnosis now states whether its
  fix is a *correction* or a *choice*. A choice trades one valid behaviour for another that no test
  or token count decides. A choice stops the round before any patch and writes the question to
  `runs/<id>.question.json`. A person answers with `python -m mend.supervisor --answer <id> "..."`.
  The answer goes to [`docs/precedents.json`](docs/precedents.json), and every later diagnosis must
  follow it, so each question is asked once. Round 7 was the first round with this step: it judged
  its fix a correction, and the gate then reverted it. No real choice has come up yet, so the
  ask path is shown only by a unit test.

### What makes this more than a loop

Several self-repair loops were built for neatHack. Here is what Mend shows beyond "it got better
once":
- **8 rounds**, 5 kept and **3 reverted** by the gate, with every decision re-checkable in the
  browser ([site, "Check it yourself"](https://thegoodengineers.github.io/mend/#verify)) or with
  `python -m mend.verify`.
- **Held-out bugs** the supervisor never saw: 9/10 → 10/10.
- **A real open-source library** it never saw (inflection): 2–3/8 → 8/8.
- **Repeat runs:** 3 runs before and 3 after, on the same 28 tasks.
- **Repair memory** read back from Entire checkpoints.
- **A second opinion** from neatlogs' own neatroots checker.

## Results

### Self-repair rounds (five kept, three reverted)

| # | What Mend changed in itself | Solved | Tokens | Commit | Diagnosis |
|---|---|---|---|---|---|
| 1 | Added an exact-replace `edit_file` tool; steered edits away from whole-file rewrites | 27 → 28 / 28 | 933,181 → 851,463 (−8.8%) | `e8a6baf` | [diagnosis](runs/2026-10-10T09-15-17.diagnosis.md) |
| 2 | `edit_file` shows the current text of a near match on a miss; clearer line prefixes | 28 → 29 / 29 | 1,005,203 → 894,839 (−11.0%) | `f9dae91` | [diagnosis](runs/2026-10-10T10-17-27.diagnosis.md) |
| 3 | Test-first workflow; stop as soon as the suite passes | 29 → 29 / 29 | 894,839 → 618,906 (−30.8%) | `931ea51` | [diagnosis](runs/2026-10-10T10-30-26-after.diagnosis.md) |
| 4 | Loop hands the worker the file list up front and finishes automatically once the full suite passes after an edit | 29 → 29 / 29 | 618,906 → 432,858 (−30.1%) | [`7e2148e`](https://entire.io/gh/thegoodengineers/mend/commit/7e2148e201fdaa9b2b3f921d1f2651950f537205) (Entire checkpoint) | [diagnosis](runs/2026-10-10T10-41-18-after.diagnosis.md) |
| 5 | Loop re-runs the full suite automatically after any successful edit and finishes on green | 29 → 29 / 29 | 456,563 → 347,960 (−23.8%) | [`c07f702`](https://entire.io/gh/thegoodengineers/mend/commit/c07f70237b8f640e5435edbec09dbb6976c49ed8) (Entire checkpoint) | [diagnosis](runs/2026-10-10T11-18-45.diagnosis.md) |
| 6 | `edit_file` takes a list of edits so a whole fix lands in one call | 29 → 29 / 29 | 347,960 → 361,174 (+3.8%) | `49c99e2`, **reverted** by `b5e788d` | [diagnosis](runs/2026-10-10T11-50-52-after.diagnosis.md) |
| 7 | `read_file` returns the whole file by default instead of a 200-line page | 29 → 29 / 29 | 302,153 → 288,229 (−4.6%) | `723015f`, **reverted** by `d1aabc9` | [diagnosis](runs/2026-10-10T13-28-51.diagnosis.md) |
| 8 | Prompt: don't read tests; map the failing test to its source module; trust the traceback over the report | 29 → 29 / 29 | 302,153 → 368,440 (+21.9%) | `badd7dd`, **reverted** by `a403b68` | [diagnosis](runs/2026-10-10T13-28-51-d2.diagnosis.md) |

Round records: the `*.round.json` files in [`runs/`](runs/). Rounds 2 and 3 were run back to back with
`python -m mend.supervisor <run> --rounds 2`; rounds 4-8 ran from a clean runner clone. **Round 8** was the first under [gate amendment 1](docs/GATE.md); it made the worker significantly worse (+21.9% tokens, paired interval [1.099, 1.355] entirely above 1) and was reverted. **Round 7** (11 Oct, the first run with the ask-once judgment step, which judged its fix a correction, not a choice) was also reverted: −4.6% tokens is under the 15% bar. **Round 6 was reverted automatically:** it still solved 29/29 but used 3.8% more tokens, so the gate rejected it. Round 5 also created its own neatlogs regression guard ("Mend: slow solve (6+ turns)", matched 5 real spans). Rounds 2-3 "after" figures are single runs. The worker after round 4 was run three times: 29/29 each time ([10-59-46](runs/2026-10-10T10-59-46-after.json) 432,858, [11-13-11](runs/2026-10-10T11-13-11.json) 451,105, [11-18-45](runs/2026-10-10T11-18-45.json) 456,563 tokens). The worker after round 5 was also run three times: 29/29 each time ([11-50-52](runs/2026-10-10T11-50-52-after.json) 347,960, [13-23-02](runs/2026-10-10T13-23-02.json) 346,214, [13-28-51](runs/2026-10-10T13-28-51.json) 302,153 tokens). **Caveat:** the supervisor learns from the same 29 tasks it is scored on, and round 3's prompt includes a rule for hanging test suites learned from task 29; on a held-out set it never sees, it also improved (below).

**How sure is each decision?** The gate looks at one re-run. Each task runs both before and
after, so the comparison can be paired per task ([`mend/stats.py`](mend/stats.py), following
Miller, [*Adding Error Bars to Evals*](https://arxiv.org/abs/2411.00640); output in
[`evidence/gate-stats.json`](evidence/gate-stats.json)):

| Round | Tasks fixed / broken | Sign test p | Tokens after ÷ before | 95% interval (tasks resampled) | Gate |
|---|---|---|---|---|---|
| 1 | 1 / 0 | 1.0 | 0.912 | [0.73, 1.156] | kept |
| 2 | 1 / 0 | 1.0 | 0.89 | [0.749, 1.042] | kept |
| 3 | 0 / 0 | 1.0 | 0.692 | [0.609, 0.788] | kept |
| 4 | 0 / 0 | 1.0 | 0.699 | [0.642, 0.764] | kept |
| 5 | 0 / 0 | 1.0 | 0.762 | [0.702, 0.824] | kept |
| 6 | 0 / 0 | 1.0 | 1.038 | [0.91, 1.194] | reverted |
| 7 | 0 / 0 | 1.0 | 0.954 | [0.82, 1.113] | reverted |
| 8 | 0 / 0 | 1.0 | 1.219 | [1.099, 1.355] | reverted (amended gate) |

What this says, plainly:
- **Rounds 3–5 are solid.** Each token cut's whole 95% interval sits below 0.85, the gate's own
  threshold.
- **Rounds 1 and 2 were kept on a single task flipping** from fail to pass. That alone is not
  statistically convincing (p = 1.0), and their token intervals include "no change". Round 1 is
  backed separately by the 3-vs-3 repeat runs below, where every repaired run solved more tasks than
  every original run (28, 28, 28 vs 27, 26, 27), and task 23 passed 3 of 3 times instead of 0 of 3.
- **Round 6's revert was right.** Its interval spans 1, so nothing was gained. Round 7 (−4.6%) is the
  same: its interval [0.82, 1.113] also spans 1.
- **Round 8 made things worse.** Its whole interval [1.099, 1.355] is above 1, so the revert was
  clearly right.

**Caveat:** the interval resamples tasks, not repeated runs, so it does not capture one task's
run-to-run noise.

**Which fixes actually carry the gain? (leave-one-out ablation)** We took today's worker, removed
one kept fix with `git revert`, and re-ran all 29 tasks once
([`scripts/ablation.py`](scripts/ablation.py) → [`evidence/ablation.json`](evidence/ablation.json),
run files in [`runs/ablation/`](runs/ablation/)). Today's worker, run 3 times: 29/29 each time,
302,153–347,960 tokens.

| Fix removed | Solved | Tokens | vs today's mean |
|---|---|---|---|
| Round 5: auto re-run the suite after an edit, finish on green | 29/29 | 535,826 | +61% |
| Round 3: test-first workflow, stop on green | 29/29 | 461,763 | +39% |
| Round 2: `edit_file` shows the near match on a miss | 29/29 | 353,131 | +6% |

What this says:
- **Rounds 5 and 3 carry the savings.** Removing either one costs far more than run-to-run noise.
- **Round 2 adds little on its own today.** Its run lands just above today's range, which matches
  the paired statistics above, where round 2 rested on one task flip.
- **Rounds 1 and 4 cannot be removed alone.** Their reverts conflict, because later fixes build on
  them; for example, every later round uses round 1's `edit_file`.
- **No single removable fix changes the solve rate.** It stays 29/29 each time; the remaining
  fixes compensate.

Each ablation is one run.

**The first bug Mend found in itself.** The worker read only the first 200 lines of the
233-line `ledger.py`, then rewrote the whole file to change one word. That silently deleted
everything after line 200. Task 23 failed at the 15-turn limit; after the fix it passed in 8
turns.

### What changed in the worker's behaviour

These counts were read back from the neatlogs traces of every task in each run
([`scripts/tool_usage.py`](scripts/tool_usage.py) → [`evidence/tool-usage.json`](evidence/tool-usage.json),
0 traces missing):

| Run | Worker | Whole-file writes | `edit_file` calls | Test runs | Model calls |
|---|---|---|---|---|---|
| [09-15-17](runs/2026-10-10T09-15-17.json) (28 tasks) | original | 31 | — | 75 | 235 |
| [09-31-07](runs/2026-10-10T09-31-07-after.json) (28 tasks) | after round 1 | 2 | 36 | 72 | 242 |
| [10-41-18](runs/2026-10-10T10-41-18-after.json) (29 tasks) | after round 3 | 0 | 32 | 56 | 174 |
| [11-50-52](runs/2026-10-10T11-50-52-after.json) (29 tasks) | after round 5 | 0 | 33 | 59 | 107 |

Round 1 replaced the destructive habit, rewriting whole files, with precise edits. Rounds 3–5
cut wasted turns, so model calls fell by more than half.

### Repeatable, not lucky: same 28 tasks, 3 runs each

| Worker | Runs | Solved | Mean tokens per run | Task 23 |
|---|---|---|---|---|
| Before self-repair (`13defdb`) | [09-15-17](runs/2026-10-10T09-15-17.json), [10-17-27-v0](runs/2026-10-10T10-17-27-v0.json), [10-28-58-v0](runs/2026-10-10T10-28-58-v0.json) | 27, 26, 27 | 946,860 | passed 0 of 3 |
| After round 1 | [09-31-07](runs/2026-10-10T09-31-07-after.json), [09-40-55](runs/2026-10-10T09-40-55.json), [09-51-17](runs/2026-10-10T09-51-17.json) | 28, 28, 28 | 875,953 (−7.5%) | passed 3 of 3 |

### Held-out test: 10 bugs the supervisor never saw

[`tasks/heldout.json`](tasks/heldout.json) holds 10 more planted bugs. They are never shown to the
supervisor (it refuses held-out runs) and no diagnosis or patch is based on them.

| Worker | Runs | Solved | Mean tokens per run | Turns |
|---|---|---|---|---|
| Original (`13defdb`) | [11-25-59](runs/2026-10-10T11-25-59-heldout-v0.json), [11-32-56](runs/2026-10-10T11-32-56-heldout-v0.json) | 9, 9 of 10 | 388,977 | 83, 86 |
| After 4 self-repair rounds | [11-30-57](runs/2026-10-10T11-30-57-heldout.json), [11-37-44](runs/2026-10-10T11-37-44-heldout.json) | 10, 10 of 10 | 156,587 (−59.7%) | 46, 48 |

The original worker's held-out runs used `mend/worker.py` and `mend/prompts/worker.md` from
`13defdb` on the current harness (noted in each run file as `worker_version`).

### Real-world test: bugs in an open-source library it never saw

[`realworld/inflection`](realworld/inflection) is the open-source `inflection` library (0.5.1, MIT,
unmodified, 455 of its own tests). [`tasks/realworld.json`](tasks/realworld.json) plants 8 bugs that
its own tests catch (2 more were dropped because the library's tests miss them). The supervisor
never sees these runs; the harness swaps the library name in the worker's prompt identically for
both workers.

| Worker | Runs | Solved | Mean tokens per run |
|---|---|---|---|
| Original (`13defdb`) | [12-10-47](runs/2026-10-10T12-10-47-realworld-v0.json), [12-23-39](runs/2026-10-10T12-23-39-realworld-v0.json) | 2, 3 of 8 | 1,462,537 |
| After 5 self-repair rounds | [12-21-13](runs/2026-10-10T12-21-13-realworld.json), [12-34-51](runs/2026-10-10T12-34-51-realworld.json) | 8, 8 of 8 | 268,926 (−81.6%) |

The original worker's failures repeat the flaw Mend found in itself: on the 426-line module it
rewrote the whole file, broke unrelated tests and ran out of turns.

### Live recording

[`video/live/mend-live.mp4`](video/live/mend-live.mp4) (1:55, also on the website): the original and
the repaired worker run task 23 live, replayed at real speed from event logs written during the
runs ([`scripts/live_run.py`](scripts/live_run.py), [`video/live/make_video.py`](video/live/make_video.py)).
Original: failed, 15 turns, 147,457 tokens (trace `1ef860cd`). Repaired: passed, 4 turns, 17,847
tokens (trace `9b29c189`). Narration is synthetic voice.

For reference, the same worker on Claude Opus 5.5 solved the first 20 tasks: 20/20, 162,006
tokens ([run](runs/2026-10-10T08-37-19.json)).

## Evidence

| Claim | Evidence |
|---|---|
| Runs are traced in neatlogs and read back by the agent | [`evidence/t02-first-traced-call.txt`](evidence/t02-first-traced-call.txt), [`evidence/t04-trace-readback.txt`](evidence/t04-trace-readback.txt); each run file has per-task `trace_id`s |
| The agent recovers from a failed action | [`evidence/t17-recovery-from-timeout.txt`](evidence/t17-recovery-from-timeout.txt): `run_tests` timed out after 60 s, then the worker found and fixed the infinite loop (task 29) |
| Before/after with the numbers compared | the tables above; every row links to its run file |
| Self-fixes are written by Claude Code and committed by the supervisor | commits `e8a6baf`, `f9dae91`, `931ea51` (`fix(worker): …`) |
| Entire checkpoints | round 4: [checkpoint `01M4JQG23JYXJ34SHA46MCGMV2`](https://entire.io/gh/thegoodengineers/mend/commit/7e2148e201fdaa9b2b3f921d1f2651950f537205) on commit `7e2148e`, the supervisor's own Claude Code session; see note below |
| Business plan with cfo.ai | [`docs/business-plan.md`](docs/business-plan.md), export [`docs/business-plan-cfo-ai.xlsx`](docs/business-plan-cfo-ai.xlsx) |
| Code written during the hackathon | commit history; the first commit holds only plans written before the event, as the rules allow |
| Building in public | [first #neatHack post](https://x.com/theintrodev/status/2108851736765141188) |

**Note on Entire checkpoints.** Entire captured the supervisor's headless Claude Code sessions
as checkpoints, for example the session behind `e8a6baf`. Those checkpoints also included the
lead's own interactive chat, so we removed them from the public repo. New checkpoints are
created from a separate clean clone that only runs the supervisor (round 4 onwards).

## Built with

- **neatlogs:** tracing (Python SDK, `wrap()` + `@neatlogs.span`) and reading traces back over
  the neatlogs MCP server. The traces are the supervisor's input.
- **Entire:** Claude Code hooks plus `commit_linking: always` link each self-fix commit to the
  Claude Code session that wrote it. Publicly available today: round 4's checkpoint (the earlier
  ones were removed because they also contained the lead's own chat; their commits still carry
  `Entire-Checkpoint` trailers that now point nowhere).
- **cfo.ai:** pricing, costs, revenue and runway, from our measured cost per repair round.
- **Claude:** Haiku 4.5 as the worker, Opus 5.5 as the supervisor, Claude Code for patches.

## Run locally

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"   # macOS/Linux: .venv/bin/pip
pytest                                  # unit tests + checks that all 29 planted bugs break the sandbox
```

Needs `NEATLOGS_API_KEY` (neatlogs Project API key) and `ANTHROPIC_API_KEY` as environment
variables. Never commit them.

```bash
python -m mend.suite                 # run the worker on all tasks -> runs/<run_id>.json
python -m mend.supervisor --rounds 2 # self-repair rounds on the latest run
python -m mend.site                  # rebuild index.html from the run files
python -m mend.report                # rebuild report.html
```

The supervisor needs the Claude Code CLI (`claude`) for the patch step, and a clean git tree.
