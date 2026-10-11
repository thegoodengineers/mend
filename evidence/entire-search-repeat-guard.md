# Repair memory through Entire search (validated 11 Oct ~12:40 IST)

Before Claude Code patches anything, the supervisor sends the proposed fix's title to
`entire search --compact`. Entire's search service runs hybrid semantic and keyword search over
this repo's checkpoints, commits and sessions. If a commit hit scores at least 80 and is a fix the
gate reverted, the round is rejected before the re-run, which saves about $0.44 per repeat.
Code: `entire_search` / `repeats_reverted_fix` in [`mend/supervisor.py`](../mend/supervisor.py).

Calibration, top commit hit for each query (real CLI output, `entire` 0.11.4):

| Query (fix title) | Top commit hit | Score |
|---|---|---|
| round 6's reverted fix, proposed again | `49c99e2` (round 6 itself), then its revert `b5e788d` | 94.6 |
| "Prompt: summarise the traceback in one line before reading any file" (never tried) | `f9dae91` | 24.0 |
| "Loop: cap read_file output at 120 lines and show a file outline first" (never tried) | `f9dae91` | 24.1 |
| round 7's title | `f9dae91` | 19.6 |
| round 8's title | `e530822` | 42.7 |

Live check of the guard:

    round 6 again -> Entire search: repeats reverted fix 49c99e2 '...' (score 106)
    novel         -> ''  (allowed)
    kept round 1  -> ''  (a kept fix is not a failed one)

**Limit.** Entire indexes only checkpoints that were pushed. Rounds 7 and 8 are not found, because
their checkpoints contain an email address and were kept local (see `hackathon.md`). Those rounds
are still in the supervisor's prompt through the round records (`repair_history`). If Entire is
unreachable, the guard never blocks.
