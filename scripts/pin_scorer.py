"""Pin the scorer: record a sha256 of every task file and every test suite -> evidence/scorer-pin.json

    python scripts/pin_scorer.py      (run only when a task or test change is intended, and say so in the commit)

`python -m mend.verify` (run in CI on every push) recomputes these hashes and fails if any file changed
without the pin being updated, so the tests and tasks that judge the worker cannot drift quietly.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = ["tasks/*.json", "sandbox/tests/*.py", "hardware/tests/*.py", "schematics/tests/*.py", "security/tests/*.py",
            "realworld/inflection/tests/*.py", "agents/analyst/shop.db"]  # the analyst's reference answers come from the db


def pins() -> dict[str, str]:
    out = {}
    for pat in PATTERNS:
        for p in sorted(ROOT.glob(pat)):
            out[str(p.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return out


if __name__ == "__main__":
    (ROOT / "evidence" / "scorer-pin.json").write_text(json.dumps(pins(), indent=1), encoding="utf-8")
    print(f"pinned {len(pins())} files")
