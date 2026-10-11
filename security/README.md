# vault: the security transfer test

A small notes service in the Python standard library. Each module guards against one vulnerability
class:
- SQL injection
- path traversal
- unpickling client data
- broken access control
- stored XSS
- predictable reset tokens
- open redirect
- double-extension uploads

Every module has a functionality test and an **exploit test** (16 tests in all). `tasks/security.json`
plants 8 vulnerabilities, each reported the way a security report would, and the supervisor never sees
them. A fix only counts if the exploit fails and the feature still works. The fix audit flags any patch
that touches the tests.

    python -m pytest -q security        # 16 tests pass on the correct code
    python -m mend.suite --security     # run the worker on the 8 vulnerabilities (uses the API)
