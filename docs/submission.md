# Submission pack (Monday 12 Oct 2026, window 7:00-11:55 PM IST)

How to submit (official rules, neatlogs.com/hackathon): a **public quote post of the official
neatlogs submission post on X**, via the "Submit on X" button that appears on the event page when
the window opens. Include team, name, project, public repo and demo link. Opening the draft does
not submit; it must be published. Late submissions are not judged. neatlogs and cfo.ai engage with
the first 50 quote posts, so post at 7:00 PM sharp. The final cutoff is announced on Discord.
A human posts this; agents never post.

## Quote-post text (edit the video link in)
Team: The Good Engineers
Project: Mend - an agent that reads its own @neatlogs traces, fixes its own code, and keeps a fix only if a full re-run proves it better
Repo: https://github.com/thegoodengineers/mend
Demo: <YouTube or X video link> · site: https://thegoodengineers.github.io/mend/
8 self-repair rounds (5 kept, 3 reverted by the gate) · held-out 9/10 -> 10/10 · real open-source library 2-3/8 -> 8/8 #neatHack

## Required pieces and where they are
| Requirement (official) | Status | Where |
|---|---|---|
| Public code repository | done | https://github.com/thegoodengineers/mend |
| Commits dated during the hackathon | done | first commit holds only pre-event plans (allowed); all code after 10 Oct 13:39 IST |
| Demo video, 3 minutes or less | first cut done (2:42); polish Monday | `video/demo/mend-demo.mp4`, built by `video/demo/build.py` |
| Video covers neatlogs, Entire and cfo.ai: architecture, implementation, runtime, reasoning, result for each | first cut covers all three; check per-tool depth Monday | scenes arch, runtime, reasoning, entire, guards, business |
| Evidence: before/after runs with numbers | done | README rounds table, repeats, held-out, real-world; `mend.verify` |
| Evidence: neatlogs traces (links or screenshots) | partial | trace read-backs in `evidence/`; **todo: dashboard screenshots** |
| Evidence: Entire checkpoints or entire-graph output | done | checkpoints for 7e2148e, c07f702 (and round 6); entire-graph enabled in the runner |
| Evidence: cfo.ai business plan (pricing, costs, revenue, runway) | done, refresh pending | `docs/business-plan.md`, `docs/business-plan-cfo-ai.xlsx` |
| Evidence: a failed action and what the agent did next | done | `evidence/t17-recovery-from-timeout.txt`; live recording ("Permission denied", then continues) |
| Evidence: #neatHack posts | **only 1** | drafts in `docs/posts.md` |

## Pre-flight (Monday, before 7 PM)
- [ ] Video uploaded (YouTube unlisted or X), under 3:00, link pasted above
- [ ] `python -m mend.verify` and CI green on the final commit
- [ ] README judges' block links all open (check in an incognito window): site, video, checkpoints, business plan
- [x] The 2 leftover leaky checkpoint refs deleted (done 11 Oct; remote now holds only 3A, V2, 9N) (`git ls-remote origin 'refs/entire/*'` shows only clean ones)
- [ ] cfo.ai model refreshed with measured costs and re-exported
- [ ] At least 4 more #neatHack posts published and listed in `hackathon.md`
- [ ] Freeze: no code changes after 5 PM; docs only
- [ ] Post the quote at 7:00 PM, then confirm it shows publicly while logged out
