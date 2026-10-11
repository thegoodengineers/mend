# Evidence index

Every claim in README.md has a file here or a link to a run file in `runs/`.

| Claim | File |
|---|---|
| neatlogs traces are created per task | [t02-first-traced-call.txt](t02-first-traced-call.txt) |
| Supervisor reads traces back over MCP | [t04-trace-readback.txt](t04-trace-readback.txt) |
| Agent recovers from a failed tool call | [t17-recovery-from-timeout.txt](t17-recovery-from-timeout.txt) |
| Task 23 before self-repair (failing trace) | [task23-before-trace.json](task23-before-trace.json) |
| Task 23 after self-repair (passing trace) | [task23-after-trace.json](task23-after-trace.json) |
| neatroots second-opinion check | [neatroots-check.md](neatroots-check.md) |
| Entire checkpoints (rounds 4 and 5) | [entire-checkpoint.md](entire-checkpoint.md) |
| All run files (tasks, tokens, trace IDs) | [`runs/`](../runs/) |
| Mend on a second agent (SQL analyst): runs, round record, diagnosis | [`runs/analyst/`](../runs/analyst/), [`mend/analyst_round.py`](../mend/analyst_round.py) |
| Business plan (cfo.ai export) | [`docs/business-plan.md`](../docs/business-plan.md), [`docs/business-plan-cfo-ai.xlsx`](../docs/business-plan-cfo-ai.xlsx) |
| Build log (timestamped) | [`hackathon.md`](../hackathon.md) |
| Commit history (all during the event) | https://github.com/thegoodengineers/mend/commits/main |

## Screenshots still needed (to be captured by a human)

- [ ] neatlogs dashboard showing the project's real traces (1920×1080, no cursor waving)
- [ ] Entire checkpoint page for round 4 or 5

Save as `evidence/neatlogs-dashboard.png` and `evidence/entire-checkpoint.png`.
