# Submission pack (Monday 12 Oct 2026, window 7:00-11:55 PM IST)

How to submit (official rules, neatlogs.com/hackathon): a **public quote post of the official
neatlogs submission post on X**, via the "Submit on X" button that appears on the event page when
the window opens. Include team, name, project, public repo and demo link. Opening the draft does
not submit; it must be published. Late submissions are not judged. neatlogs and cfo.ai engage with
the first 50 quote posts, so post at 7:00 PM sharp. The final cutoff is announced on Discord.
A human posts this; agents never post.

## Two mandatory steps (organizers' Discord, 12 Oct)
1. **Quote-tweet the official @neatlogs launch post** (link shared at 7 PM IST). It **must tag @neatlogs,
   @EntireHQ and @arithecfo**; that is how their system detects a submission.
2. **Fill in the submission form** (link shared at 7 PM). The form alone does not count.

Window: 7:00-11:55 PM IST. They engage with the first 50 quote-tweets.

## Quote-tweet text, in the form's template (276/280 as X counts it, links = 23)
The official form (step 1 of 3) gives a template: "Our #neatHack submission / [your story] / Built with
@arithecfo @EntireHQ @neatlogs", and asks to **attach the demo video** and keep the post public with the
launch post attached. Its "Quote on X" button opens the right launch post.

```
Our #neatHack submission

our agent caught itself deleting half a file to fix one line. now it reads its own traces, patches itself, and keeps a fix only if a re-run proves it. it threw out 6 of its 11 fixes.

https://github.com/thegoodengineers/mend

Built with @arithecfo @EntireHQ @neatlogs
```

Attach `video/demo/mend-demo.mp4` (2:58). X takes up to 2:20 on accounts without Premium; if it refuses,
build a 2:20 cut.

## Answers ready for the form (fields unknown until 7 PM)
- Team: The Good Engineers
- Project name: Mend
- One line: an agent that reads its own neatlogs traces, fixes its own code, and keeps a fix only if a full
  re-run proves it better.
- Repo: https://github.com/thegoodengineers/mend
- Demo video: https://thegoodengineers.github.io/mend/video/demo/mend-demo.mp4
- Website: https://thegoodengineers.github.io/mend/
- How neatlogs was used: every model and tool call traced; the supervisor reads traces back over the
  neatlogs MCP server to diagnose; Mend creates neatlogs detections from its own failures; every gate verdict
  is written back as a trace; neatlogs' triage raised an incident (excessive turns) that Mend had fixed, its
  own check passes (8.38 -> 3.25 turns) and the incident is resolved.
- How Entire was used: every self-repair commit is linked to the Claude Code session that wrote it;
  the supervisor reads past checkpoints back as repair memory and `entire search` blocks repeating a
  reverted fix; `entire blame` shows 69% of the worker's prompt was written by Mend's own sessions.
- How cfo.ai was used: pricing, costs, revenue and runway; re-run with the measured $0.57 per repair
  round, gross margin 30.6% -> 68.6%.
- Results: 11 self-repair rounds (5 kept, 6 reverted by a pre-registered gate); bugs it never saw
  9/10 -> 10/10; a real open-source library 2-3/8 -> 8/8; a second agent: same answers, 37% fewer tokens.

## The organizers' video brief (Discord, 12 Oct) and where the video covers it
| They asked for | Scenes |
|---|---|
| The problem your agent solves | `problem` ("Agents fail quietly..."), then `hook` and `runtime` show it happening |
| How cfo.ai and Entire were part of the project | `entire` (checkpoints, repair memory, blame: 69%); `business` (cfo.ai plan from measured costs) |
| How neatlogs identified and resolved the incidents your agent ran into | `arch`, `runtime`, `reasoning` (the failure found in the neatlogs trace); `incident` (neatlogs' triage raised its own incident; its check passes, 8.38 → 3.25 turns, `evidence/neatlogs-incidents.md`); `gate` (every verdict written back); `explorer` |
| Show the critical-incidents feature itself | Done: the `incident` scene shows the real neatlogs Incidents page with the card under Resolved (`video/demo/screens/incident.png`) |

## Required pieces and where they are
| Requirement (official) | Status | Where |
|---|---|---|
| Public code repository | done | https://github.com/thegoodengineers/mend |
| Commits dated during the hackathon | done | first commit holds only pre-event plans (allowed); all code after 10 Oct 13:39 IST |
| Demo video, 3 minutes or less | done (2:58, 17 scenes; 12 Oct cut adds the neatlogs incident, hardware, explorer, fix audit, anti-gaming, second agent) | `video/demo/mend-demo.mp4`, built by `video/demo/build.py` |
| Video covers neatlogs, Entire and cfo.ai: architecture, implementation, runtime, reasoning, result for each | done in the 12 Oct cut | neatlogs: arch, runtime, reasoning, incident, gate, explorer; Entire: entire; cfo.ai: business |
| Evidence: before/after runs with numbers | done | README rounds table, repeats, held-out, real-world; `mend.verify` |
| Evidence: neatlogs traces (links or screenshots) | done | trace read-backs in `evidence/`; the Incidents page with our incident resolved: `docs/img/neatlogs-incident-resolved.png` |
| Evidence: Entire checkpoints or entire-graph output | done | checkpoints for 7e2148e, c07f702 (and round 6); entire-graph enabled in the runner |
| Evidence: cfo.ai business plan (pricing, costs, revenue, runway) | done, refresh pending | `docs/business-plan.md`, `docs/business-plan-cfo-ai.xlsx` |
| Evidence: a failed action and what the agent did next | done | `evidence/t17-recovery-from-timeout.txt`; live recording ("Permission denied", then continues) |
| Evidence: #neatHack posts | 3 so far | [kickoff](https://x.com/theintrodev/status/2108851736765141188), [bug it found in itself](https://x.com/theintrodev/status/2109233575614927163), [hardware](https://x.com/theintrodev/status/2109300098023006412); next ones in `docs/post-pack.html` |

## Pre-flight (Monday, before 7 PM)
- [x] Video under 3:00 (2:58) and served at the Pages link above (YouTube optional)
- [x] `python -m mend.verify` and CI green (checked 12 Oct ~12:10 IST on `6195f3b`: verify 99 numbers, 39 tests, CI and Pages green); re-check after any later commit
- [x] README links: 131 file links exist, 19 web links load, 7 anchors match (checked 12 Oct; X links not checked by script). Live video = latest cut (30,329,358 bytes)
- [x] The 2 leftover leaky checkpoint refs deleted (done 11 Oct; remote now holds only 3A, V2, 9N) (`git ls-remote origin 'refs/entire/*'` shows only clean ones)
- [x] cfo.ai model refreshed with the measured $0.57 per round and re-exported (12 Oct): margin 30.6% → 68.6%; first version kept as `docs/business-plan-cfo-ai-10oct.xlsx`
- [x] ~~At least 4 more #neatHack posts~~ dropped by the team on 12 Oct; any post that does go out still gets listed in `hackathon.md`
- [ ] Freeze: no code changes after 5 PM; docs only
- [ ] 7:00 PM: quote-tweet the launch post with all three tags, then fill in the form; confirm the post shows publicly while logged out
