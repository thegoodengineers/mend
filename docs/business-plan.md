# Mend - business plan (built with cfo.ai)

We built the model in cfo.ai on 10 Oct 2026 with an estimated cost per repair round. On 12 Oct we
measured that cost, put the measured value into cfo.ai, and let it recompute the forecast.
- **Current export:** [`business-plan-cfo-ai.xlsx`](business-plan-cfo-ai.xlsx) (12 Oct, measured cost),
  with three sheets: base vs growth, an 18-month forecast, and the model inputs.
- **Its inputs page:** [`business-plan-cfo-ai-assumptions-12oct.xlsx`](business-plan-cfo-ai-assumptions-12oct.xlsx).
- **The first version:** [`business-plan-cfo-ai-10oct.xlsx`](business-plan-cfo-ai-10oct.xlsx), kept for comparison.

Every number below comes from those sheets, unless it is marked as our own arithmetic.

## Inputs
| Input | Value | Source |
|---|---|---|
| Price | $49 per team per month, 20 repair rounds included, $2 per extra round | assumption |
| Cost per repair round | **$0.57** measured: $0.13 supervisor diagnosis + $0.44 full re-run (10 Oct model: $1.50 estimate) | measured from our run files (below) |
| Infrastructure | $200 per month | assumption |
| Founders | 4; cfo.ai's model pays $2,000 per month each from April 2027 | assumption added in cfo.ai |
| Starting cash | $10,000 | assumption |
| Customers | Base: 50 teams, flat. Growth: 50 teams, +10% per month | assumption |

## What the model shows, before and after the measured cost
| From cfo.ai's exports | 10 Oct ($1.50 per round, estimate) | 12 Oct ($0.57 per round, measured) |
|---|---|---|
| Monthly model fees at 50 teams (1,000 rounds) | $1,500 | $570 |
| Gross profit at 50 teams (after $200 infrastructure) | $750 per month | $1,680 per month |
| Gross margin at 50 teams | 30.6% | 68.6% |
| Cash reaches $0, base (flat 50 teams) | May 2027 | July 2027 |
| Closing cash March 2028, base | −$72,500 | −$55,760 |
| Cash reaches $0, growth (+10% a month) | June 2027 | September 2027 |
| Closing cash March 2028, growth | −$46,281 | −$3,874 |

In both versions the cash cliff is founder pay, which starts in April 2027, not model cost.

## What we take from it
Measured self-repair more than doubled the margin, from 30.6% to 68.6%. On its own it does not pay
four founders. Our arithmetic from the model's inputs:
- each team now adds $49 − 20 × $0.57 = **$37.60** of gross profit per month, against $19.00 at $1.50;
- so about **218 teams** cover the $8,200 per month of payroll and infrastructure, against about 432 at
  $1.50.

The next lever is price. At $99 per team with the same costs, each team adds about $87.60, so about 94
teams cover the same $8,200. That is our arithmetic and is not in cfo.ai yet.

## How the repair cost was measured
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

- Re-running a suite in a repair round fell by about 61% ($1.12 → $0.44).
- The supervisor's diagnosis call was measured in round 6
  ([round record](../runs/2026-10-10T13-08-47-after.round.json)): Claude Opus 5.5, 20,954 input / 2,394
  output tokens, about $0.13 at $4 / $20 per million.
- So a whole repair round costs about $0.57. That is the value now in the cfo.ai model.

## Customer scenarios
Our arithmetic with the cfo.ai inputs, counting the $200 of infrastructure in cost of revenue the way
cfo.ai does:

| Teams | Monthly revenue | Model cost + infrastructure | Gross profit | Gross margin | Covers $8,200 payroll + infra? |
|---|---|---|---|---|---|
| 50 (base) | $2,450 | $770 | $1,680 | 68.6% | No (need about 218 teams) |
| 200 | $9,800 | $2,480 | $7,320 | 74.7% | Not quite |
| 1,000 | $49,000 | $11,600 | $37,400 | 76.3% | Yes |

(An earlier version of this page said 77% for every row, because it left infrastructure out. The table
above uses the same method as cfo.ai and as the 30.6% figure.)
