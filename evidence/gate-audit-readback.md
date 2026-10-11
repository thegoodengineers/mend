# Gate verdicts read back from neatlogs (get_trace_context over MCP, 11 Oct 12:35 IST)

Round 8 trace 684cb30df2268caf0897d8d5bb697f5d (workflow mend-gate), spans as neatlogs returns them:

    tool_call gate_rule | more tasks pass: NOT met (29 -> 29 of 29)
    tool_call gate_rule | same tasks pass with >=15% fewer tokens: NOT met (302,153 -> 368,440 tokens (x1.219))
    tool_call gate_rule | amendment 1: no passing task broke: met (0 fixed, 0 broke)
    workflow gate_round | {"trace_id":"684cb30df2268caf0897d8d5bb697f5d","verdict":"GATE REVERTED badd7dd"}
    tool_call gate_rule | amendment 1: paired 95% interval below 1.0: NOT met (tokens x1.219 [1.099, 1.355])
    tool_call gate_verdict | GATE REVERTED badd7dd

Readable at this time: rounds 3, 4 (GATE KEPT), 7, 8 (GATE REVERTED). Rounds 1, 2, 5, 6 were still finalizing (HTTP 409, see neatlogs-ingestion-11oct.md).

Detection created in group "Mend regression guards": "Mend: gate reverted a self-repair" (regex GATE REVERTED on gate_verdict spans), preview matched 2 spans.

## Update (15:28 IST): all 8 verdicts readable

| Round | Trace status | Spans | Verdict span output |
|---|---|---|---|
| 1 | success | 4 | GATE KEPT e8a6baf |
| 2 | success | 4 | GATE KEPT f9dae91 |
| 3 | success | 4 | GATE KEPT 931ea51 |
| 4 | success | 4 | GATE KEPT 7e2148e |
| 5 | success | 4 | GATE KEPT c07f702 |
| 6 | success | 4 | GATE REVERTED 49c99e2 |
| 7 | success | 4 | GATE REVERTED 723015f |
| 8 | success | 6 | GATE REVERTED badd7dd |

Each verdict matches its round record. Round 8 has 2 extra spans for the amendment-1 rules.

## Second agent (read back 11 Oct, ~23:40 IST)

| Round | Trace status | Spans | Verdict span output |
|---|---|---|---|
| analyst-1 | success | 6 | GATE KEPT 9931774 |

Trace `ccef269f420e5fe1aacf5ac469e92c2e`: the round span, 4 rule spans (the same rules as worker round 8 on),
and the verdict. Read back over the neatlogs MCP server (`get_trace_context`) a few minutes after it was sent.
