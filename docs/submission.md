# Submission pack (Monday 12 Oct 2026, window 7:00-11:55 PM IST)

How to submit (official rules, neatlogs.com/hackathon): a **public quote post of the official
neatlogs submission post on X**, via the "Submit on X" button that appears on the event page when
the window opens. Include team, name, project, public repo and demo link. Opening the draft does
not submit; it must be published. Late submissions are not judged. neatlogs and cfo.ai engage with
the first 50 quote posts, so post at 7:00 PM sharp. The final cutoff is announced on Discord.
A human posts this; agents never post.

## Quote-post text (279/280 as X counts it, links = 23)
The demo link is the video served by GitHub Pages (checked 12 Oct: HTTP 200, `video/mp4`, 32.5 MB), so no
upload is needed. X itself only takes videos up to 2:20 from non-Premium accounts, so do not attach the
2:59 file; link it. A YouTube link can replace it, if you upload one.

```
Team: The Good Engineers
Project: Mend, an agent that reads its own @neatlogs traces, fixes its own code, and keeps a fix only if a re-run proves it
Repo: https://github.com/thegoodengineers/mend
Demo: https://thegoodengineers.github.io/mend/video/demo/mend-demo.mp4
bugs it never saw 9/10 -> 10/10, a real library 2-3/8 -> 8/8 #neatHack
```

Shorter fallback (253/280), if X counts differently:

```
Team: The Good Engineers
Project: Mend, an agent that reads its own @neatlogs traces, fixes its own code, and keeps a fix only if a full re-run proves it
Repo: https://github.com/thegoodengineers/mend
Demo: https://thegoodengineers.github.io/mend/video/demo/mend-demo.mp4
Site: https://thegoodengineers.github.io/mend/
#neatHack
```

## Required pieces and where they are
| Requirement (official) | Status | Where |
|---|---|---|
| Public code repository | done | https://github.com/thegoodengineers/mend |
| Commits dated during the hackathon | done | first commit holds only pre-event plans (allowed); all code after 10 Oct 13:39 IST |
| Demo video, 3 minutes or less | done (2:59, 19 scenes; 12 Oct cut adds hardware, explorer, fix audit, anti-gaming, second agent) | `video/demo/mend-demo.mp4`, built by `video/demo/build.py` |
| Video covers neatlogs, Entire and cfo.ai: architecture, implementation, runtime, reasoning, result for each | done in the 12 Oct cut | neatlogs: arch, runtime, reasoning, explorer, guards; Entire: entire; cfo.ai: business |
| Evidence: before/after runs with numbers | done | README rounds table, repeats, held-out, real-world; `mend.verify` |
| Evidence: neatlogs traces (links or screenshots) | partial | trace read-backs in `evidence/`; **todo: dashboard screenshots** |
| Evidence: Entire checkpoints or entire-graph output | done | checkpoints for 7e2148e, c07f702 (and round 6); entire-graph enabled in the runner |
| Evidence: cfo.ai business plan (pricing, costs, revenue, runway) | done, refresh pending | `docs/business-plan.md`, `docs/business-plan-cfo-ai.xlsx` |
| Evidence: a failed action and what the agent did next | done | `evidence/t17-recovery-from-timeout.txt`; live recording ("Permission denied", then continues) |
| Evidence: #neatHack posts | 3 so far | [kickoff](https://x.com/theintrodev/status/2108851736765141188), [bug it found in itself](https://x.com/theintrodev/status/2109233575614927163), [hardware](https://x.com/theintrodev/status/2109300098023006412); next ones in `docs/post-pack.html` |

## Pre-flight (Monday, before 7 PM)
- [x] Video under 3:00 (2:59) and served at the Pages link above (YouTube optional)
- [ ] `python -m mend.verify` and CI green on the final commit
- [ ] README judges' block links all open (check in an incognito window): site, video, checkpoints, business plan
- [x] The 2 leftover leaky checkpoint refs deleted (done 11 Oct; remote now holds only 3A, V2, 9N) (`git ls-remote origin 'refs/entire/*'` shows only clean ones)
- [ ] cfo.ai model refreshed with measured costs and re-exported
- [ ] At least 4 more #neatHack posts published and listed in `hackathon.md`
- [ ] Freeze: no code changes after 5 PM; docs only
- [ ] Post the quote at 7:00 PM, then confirm it shows publicly while logged out
