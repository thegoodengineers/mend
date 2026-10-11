# #neatHack post drafts

Every number below comes from a file in the repo. A human posts them; agents never post.
Tag @neatlogs, and @entirehq or @arithecfo where the post is about Entire or cfo.ai.

## 1. The bug it found in itself (screenshot: the demo trace, or the live video at 0:30)
our agent found its own bug. it read 200 of 233 lines of a file, then rewrote the whole file to change one word, silently deleting the rest. mend caught it in its @neatlogs traces and gave itself an edit tool. 27/28 -> 28/28 #neatHack
https://thegoodengineers.github.io/mend/

## 2. Five rounds, no human
5 self-repair rounds, no human in the loop. each one: read traces, diagnose, patch itself, re-run all 29 tasks, keep only if it got better. tokens per suite run: 1,005,203 -> 347,960 #neatHack
https://github.com/thegoodengineers/mend#self-repair-rounds-five-kept-one-reverted

## 3. Held-out test (the "is it overfitting?" answer)
does self-repair just overfit? we ran 10 bugs it never saw. original worker: 9/10 twice. after self-repair: 10/10 twice, 60% fewer tokens #neatHack
https://github.com/thegoodengineers/mend#held-out-test-10-bugs-the-supervisor-never-saw

## 4. Live recording (attach video/live/mend-live.mp4)
same task, same model, recorded live at real speed. before: failed, 15 turns, 147k tokens. after mend fixed itself: passed, 4 turns, 18k tokens #neatHack

## 5. Regression guards (screenshot: neatlogs detections page, no keys visible)
every failure mend diagnoses becomes a @neatlogs detection, tested against real traces before it is created. so if a fixed bug ever comes back, neatlogs flags it #neatHack

## 6. Entire checkpoints (screenshot: the round 4 checkpoint page)
every fix mend makes to itself is written by claude code and linked to that session in @entirehq. and before each diagnosis, mend reads its own past checkpoints so it never retries a reverted fix #neatHack
https://entire.io/gh/thegoodengineers/mend/commit/7e2148e201fdaa9b2b3f921d1f2651950f537205

## 7. Every number is checked
every number in our README is recomputed from raw run files on every push. edit one by hand and CI goes red #neatHack
https://github.com/thegoodengineers/mend/actions

## 7b. The gate said no
our agent proposed a change to itself, tested it on all 29 tasks, saw it cost 3.8% more tokens, and reverted it. no human involved. that's the point: it only keeps what the numbers prove #neatHack
https://github.com/thegoodengineers/mend#self-repair-rounds-five-kept-one-reverted

## 8. Submission (Monday 7:00-11:55 PM IST, quote the official neatlogs post)
Team The Good Engineers - Mend: an agent that fixes itself and proves it. repo: https://github.com/thegoodengineers/mend demo: https://thegoodengineers.github.io/mend/ #neatHack

## 9. LinkedIn (long form; all numbers from the README tables)
Day 1 of #neatHack: our AI agent fixed itself, and proved it.

We're building Mend: an agent that reads its own neatlogs traces, works out why it failed, patches its own code, and keeps the fix only if a full re-run gets better. Otherwise it reverts.

The first bug it found in itself: the worker read 200 lines of a 233-line file, then rewrote the whole file to change one word, silently deleting the rest. Mend caught it in the trace and gave itself a precise edit tool.

Five self-repair rounds later, no human in the loop:
✅ 27/28 → 29/29 tasks solved
💸 cost per task $0.040 → $0.015
🔁 every fix checkpointed in Entire, every failure turned into a neatlogs detection

Then the "is it overfitting?" test:
🧪 10 bugs it never saw: 9/10 → 10/10
🌍 8 bugs in a real open-source library: 2-3/8 → 8/8, 82% fewer tokens

Lesson: an agent that changes itself needs a gate. Ours only keeps what the numbers prove.

https://thegoodengineers.github.io/mend/
#neatHack #AIAgents #BuildInPublic

## 10. Answering "Self-healing is self-defeating" (quote-reply the neatlogs blog post; day 2)
Image: [`docs/img/post-10-judgment.png`](img/post-10-judgment.png)
@neatlogs' founder argues that a self-healing agent drifts toward the median unless someone defines "better". His fix: automate what isn't a choice, ask when it is, remember the answer.

So we built that into Mend:
- it only auto-fixes what has an objective answer (tests and tokens)
- every diagnosis now says "correction" or "choice"; a choice stops and asks a person
- the answer becomes a precedent that every later round must follow

https://thegoodengineers.github.io/mend/#judgment #neatHack

## 11. 69% of its own instructions (screenshot: the site's "Who wrote the worker?" table)
Image: [`docs/img/post-11-provenance.png`](img/post-11-provenance.png)
`entire blame` on our agent's system prompt: 9 of 13 lines were written by its own self-repair sessions. Each line traces to an @EntireHQ checkpoint, the instruction the supervisor gave Claude Code, the diagnosis, and the @neatlogs traces it read.

https://thegoodengineers.github.io/mend/#provenance #neatHack

## 12. Error bars on our own gate (screenshot: README "How sure is each decision?" table)
Image: [`docs/img/post-12-ablation.png`](img/post-12-ablation.png)
We ran a paired sign test and bootstrap interval on every self-repair decision. Honest result: rounds 3-5 are solid; rounds 1-2 were kept on a single task flipping. So we tightened the gate, publicly, before round 8: no task may break, and a token win must hold across tasks.

Round 7 then saved 4.6%: under the bar, reverted. Round 8, the first under the stricter gate, cost 22% more: reverted. Round 9 saved a real 12%, under the 15% bar fixed in advance: reverted too. The gate has said no four times.
#neatHack
