# Invalid analyst runs

Made before the harness fix in agents/analyst/agent.py (an empty tool result was sent as an empty user message, the API returned 400, and the question was scored as failed). The one failure here (A18 in the v0 run) was that crash, not a wrong answer. Kept for the record; not used for any claim.
