# Mend - business plan (built with cfo.ai)

The model was built in cfo.ai on 10 Oct 2026 and exported to
[`business-plan-cfo-ai.xlsx`](business-plan-cfo-ai.xlsx). It has three sheets: base vs growth,
an 18-month forecast, and the model inputs. This page summarises it. Every number below is in
the sheet.

## Inputs
| Input | Value | Source |
|---|---|---|
| Price | $49 per team per month, 20 repair rounds included, $2 per extra round | assumption |
| Cost per repair round | $1.50 (28 Haiku tasks at about $0.04, plus an Opus diagnosis at about $0.38) | built from our measured runs; the round total is an estimate |
| Infrastructure | $200 per month | assumption |
| Founders | 4; cfo.ai's model pays $2,000 per month each from April 2027 | assumption added in cfo.ai |
| Starting cash | $10,000 | assumption |
| Customers | Base: 50 teams, flat. Growth: 50 teams, +10% per month | assumption |

## What the model shows
- **Gross margin is 31%.** 20 included rounds at $1.50 is $30 of model cost per $49 team.
  Gross profit is $750 per month at 50 teams.
- **Runway:** Base closing cash peaks at $14,500 (March 2027), reaches $0 in May 2027 once
  founder pay starts, and ends at -$72,500 in March 2028. Growth reaches 252 teams and
  $12,383 monthly revenue by March 2028, but cash goes negative in June 2027 and ends at
  -$46,281.

## What we take from it
At $49 per team with 20 rounds at $1.50 each, the price leaves only a 31% gross margin. Each team
adds about $15 of gross profit per month, so roughly 550 teams would be needed to cover $8,200 per
month of payroll and infrastructure (our arithmetic from the model's inputs). Two levers:
1. **Cheaper rounds.** Self-repair already cut our own cost (measured, below).
2. **Higher price.** At $99 per team with the same costs, gross profit is about $69 per team,
   so roughly 120 teams cover the same $8,200 (same arithmetic, not yet in cfo.ai).

## Measured since the model was built (10 Oct, evening)
Worker cost per suite run, from token counts in the run files at Claude list prices (Haiku 4.5:
$1 per million input tokens, $5 per million output tokens):

| Run | Solved | Input / output tokens | Cost per run | Cost per task |
|---|---|---|---|---|
| Original worker ([09-15-17](../runs/2026-10-10T09-15-17.json)) | 27/28 | 885,631 / 47,550 | $1.12 | $0.040 |
| After round 3 ([10-41-18](../runs/2026-10-10T10-41-18-after.json)) | 29/29 | 592,694 / 26,212 | $0.72 | $0.025 |
| After round 4 ([10-59-46](../runs/2026-10-10T10-59-46-after.json)) | 29/29 | 410,096 / 22,762 | $0.52 | $0.018 |
| After round 5 ([11-50-52](../runs/2026-10-10T11-50-52-after.json)) | 29/29 | 324,978 / 22,982 | $0.44 | $0.015 |
| Held-out, original ([11-25-59](../runs/2026-10-10T11-25-59-heldout-v0.json)) | 9/10 | 357,846 / 24,487 | $0.48 | $0.048 |
| Held-out, after 4 rounds ([11-30-57](../runs/2026-10-10T11-30-57-heldout.json)) | 10/10 | 146,059 / 7,729 | $0.19 | $0.019 |

So the cost of re-running a suite in a repair round fell by about 61% ($1.12 -> $0.44). The
supervisor's diagnosis call was measured in round 6 ([round record](../runs/2026-10-10T13-08-47-after.round.json)):
Claude Opus 5.5, 20,954 input / 2,394 output tokens = about $0.13 at $4 / $20 per million. A whole
repair round therefore costs about $0.57 today, against the $1.50 the cfo.ai model assumed. Next step: rebuild the cfo.ai model with these measured costs.

## Customer scenarios (from cfo.ai model inputs)

| Customers | Monthly revenue | Monthly model cost | Gross profit | Covers payroll? |
|---|---|---|---|---|
| 50 (base) | $2,450 | $1,690 | $760 (31%) | No — need ~550 teams |
| 200 | $9,800 | $6,760 | $3,040 (31%) | No — need ~550 teams |
| 1,000 | $49,000 | $33,800 | $15,200 (31%) | Yes — covers payroll + infra |

At the **updated measured cost** of $0.57/round (vs $1.50 assumed), margin improves:

| Customers | Monthly model cost (updated) | Gross profit (updated) | Gross margin (updated) |
|---|---|---|---|
| 50 | $570 | $1,880 | 77% |
| 200 | $2,280 | $7,520 | 77% |
| 1,000 | $11,400 | $37,600 | 77% |

Break-even at updated costs: each team adds $49 − 20 × $0.57 = $37.60 of gross profit per month, so about
6 teams cover the $200 infrastructure and about 218 teams cover the $8,200 of payroll and infrastructure
(our arithmetic from the model's inputs, not yet in cfo.ai).
