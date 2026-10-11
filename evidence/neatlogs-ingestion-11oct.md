# neatlogs: traces created on 11 Oct are not readable over MCP (checked ~11:25 IST)

Project tier: free (`whoami`). `ping` answers. Everything below was run from this repo with the
project key; trace IDs are real.

| Trace | Created (sent) | How sent | `get_trace_context` result |
|---|---|---|---|
| last task of run [13-28-51](../runs/2026-10-10T13-28-51.json) | 10 Oct 13:34 UTC | SDK | `success`, 15 spans |
| `b814c1ca…` last task of run [04-40-58-after](../runs/2026-10-11T04-40-58-after.json) | 11 Oct ~04:50 UTC | SDK | `not_found` |
| `bf209101…` last task of run [05-18-22-after](../runs/2026-10-11T05-18-22-after.json) | 11 Oct ~05:25 UTC | SDK | `not_found` |
| last task of ablation run (round 5 removed) | 11 Oct ~04:57 UTC | SDK | HTTP 409 `conflict` |
| `c8c77581…` gate audit, round 1 | 11 Oct 05:36 UTC | MCP `log_trace` (answered `queued`) | `processing`, 0 spans, then HTTP 409 |
| `a037d6d0…` minimal test trace | 11 Oct ~05:45 UTC | MCP `log_trace` (answered `queued`) | `processing`, 0 spans, then HTTP 409 |
| `c50aa9c2…`, `10da82d4…` gate audit, rounds 1 and 6 | 11 Oct ~05:50 UTC | SDK | `processing`, 0 spans |
| `684cb30d…` gate audit, round 8 | 11 Oct ~05:50 UTC | SDK | `not_found` |

`get_trace_context` with `created_after` also returns HTTP 409 once the newest trace is one of
these. `search_traces` returns 0 results (as it always has for this project).

**Effect on Mend.** Diagnoses read the traces of the run they start from. Rounds 7 and 8 started
from run 13-28-51 (10 Oct), which is readable, so their diagnoses were unaffected. A round that
starts from a run made today would get "trace unavailable" for every task. The supervisor catches
that per task, but the diagnosis would have nothing to read.

## Message for the neatlogs Discord support channel (a human posts it)

> Hi! On our project (free tier) traces sent since about 04:40 UTC today don't become readable:
> `get_trace_context` returns `not_found`, or `processing` with 0 spans and then HTTP 409. That
> happens for SDK traces and for MCP `log_trace` (which answers `queued`). Traces from yesterday
> read fine. Is that a free-tier limit or an ingestion delay? Example trace IDs:
> b814c1ca3a927f957cce9f8c3f538066, c8c7758186f80eee8fc53ce8d1288dbe. Thanks!
