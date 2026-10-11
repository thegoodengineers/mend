# Manual review of the security fixes the audit marked "review" (11 Oct, about 22:30 IST)

The fix audit marks a passing Python fix "review" when it differs from the reference code. For security
fixes, a person read every one of them, because a fix can pass the exploit test and still be insecure.
All are secure. None touched a test.

| Run | Task | What the fix does | Secure? |
|---|---|---|---|
| security (after self-repair) | SE02 | restored `resolve()`, then `target.relative_to(base)` | yes |
| all four runs | SE03 | `json.loads(blob)` on bytes; a leftover unused `import pickle` | yes (the import is cosmetic) |
| security (after self-repair) | SE04 | same condition, terms swapped | yes |
| security (after self-repair) | SE06 | token = sha256(user + 32 random bytes) | yes, 256 random bits |
| security-r2 (after self-repair) | SE06 | `secrets.token_urlsafe(24)`, 32 characters, plus an unused line | yes, 192 random bits |
| r1, r2 (after self-repair), v0-r2 | SE07 | drops one of two redundant host checks (netloc vs `//`) | yes, equivalent |
| security-v0 | SE07 | rejects `/\` only at the start instead of any backslash | yes for the real attack (browsers turn a leading `/\` into `//`); narrower than the reference |
| several | SE08 | the same extension check, restructured | yes |

Raw diffs: the `audit` field of each task in `runs/*security*.json`.
