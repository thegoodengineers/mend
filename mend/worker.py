"""The worker agent: fixes one planted bug in a sandbox copy using four tools.

Manual tool-use loop (not the SDK's beta tool runner) so neatlogs' wrap() traces every
`messages.create` call and each tool call gets its own TOOL span.

The caller must run `neatlogs.init(...)` before calling `solve` (init must precede the
anthropic import, so the client is created lazily).
"""

import difflib
import os
import time
from pathlib import Path

import neatlogs

from mend.tasks import run_tests

# A cheap worker that Mend makes reliable; the supervisor runs on a stronger model.
MODEL = os.environ.get("MEND_WORKER_MODEL", "claude-haiku-4-5")
MAX_TURNS = 15
PROMPT_FILE = Path(__file__).parent / "prompts" / "worker.md"

_AUTO_TEST_NOTE = (
    "After any turn containing a successful edit, the full test suite is run automatically and its result is "
    "returned to you; do not call run_tests yourself to verify. If the change needs several edits, make them all "
    "in this same turn so the automatic run sees the complete fix."
)

TOOLS = [
    {
        "name": "list_files",
        "description": "List all files in the project, relative to its root.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "read_file",
        "description": "Read a text file. Returns numbered lines starting at `start` (1-based), at most `lines` lines. "
        "Each line is prefixed with its number and a TAB; the code starts right after the TAB.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start": {"type": "integer", "minimum": 1},
                "lines": {"type": "integer", "minimum": 1},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "write_file",
        "description": "Create a new file or replace the WHOLE content of a file. Anything you omit is deleted. "
        "To change part of an existing file use edit_file instead. " + _AUTO_TEST_NOTE,
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "edit_file",
        "description": "Edit a file by replacing one exact occurrence of `old` with `new`. `old` must match the file's "
        "current text exactly (including indentation; do not include the line-number-and-TAB prefix shown by read_file) "
        "and must occur exactly once - include enough surrounding lines to make it unique. "
        "Prefer this over write_file for any change to an existing file. " + _AUTO_TEST_NOTE,
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
            "required": ["path", "old", "new"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_tests",
        "description": "Run the pytest suite. Optional `pattern` is passed to pytest -k. Returns pass/fail and output.",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "additionalProperties": False,
        },
    },
]

_client = None


def client():
    global _client
    if _client is None:
        from anthropic import Anthropic

        _client = neatlogs.wrap(Anthropic())
    return _client


def _safe_path(work: Path, rel: str) -> Path:
    """Resolve a tool-supplied path, refusing anything outside the sandbox copy."""
    path = (work / rel).resolve()
    if not path.is_relative_to(work.resolve()):
        raise ValueError(f"path outside the project: {rel}")
    return path


@neatlogs.span(kind="TOOL", tool_name="list_files")
def list_files(work: Path) -> str:
    return "\n".join(
        str(p.relative_to(work)).replace("\\", "/")
        for p in sorted(work.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    )


@neatlogs.span(kind="TOOL", tool_name="read_file")
def read_file(work: Path, path: str, start: int = 1, lines: int = 200) -> str:
    text = _safe_path(work, path).read_text(encoding="utf-8").splitlines()
    chunk = text[start - 1 : start - 1 + lines]
    out = "\n".join(f"{start + i}\t{line}" for i, line in enumerate(chunk))
    remaining = len(text) - (start - 1 + len(chunk))
    if remaining > 0:
        out += f"\n... ({remaining} more lines; file has {len(text)} lines total)"
    return out


@neatlogs.span(kind="TOOL", tool_name="write_file")
def write_file(work: Path, path: str, content: str) -> str:
    target = _safe_path(work, path)
    if "tests" in target.relative_to(work.resolve()).parts:
        raise ValueError("editing tests is not allowed")
    target.write_text(content, encoding="utf-8")
    return f"wrote {path} ({len(content)} chars)"


@neatlogs.span(kind="TOOL", tool_name="edit_file")
def edit_file(work: Path, path: str, old: str, new: str) -> str:
    target = _safe_path(work, path)
    if "tests" in target.relative_to(work.resolve()).parts:
        raise ValueError("editing tests is not allowed")
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        return _edit_ignoring_whitespace(target, path, text, old, new)
    if count > 1:
        raise ValueError(f"`old` occurs {count} times; include more surrounding context")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"edited {path}: replaced {old.count(chr(10)) + 1} line(s) with {new.count(chr(10)) + 1} line(s)"


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _edit_ignoring_whitespace(target: Path, path: str, text: str, old: str, new: str) -> str:
    """Fallback when `old` has no exact match: match line by line ignoring surrounding whitespace,
    re-indent `new` to fit, or explain precisely how `old` differs from the file."""
    old_lines = old.rstrip("\n").split("\n")
    file_lines = text.split("\n")
    stripped = [line.strip() for line in file_lines]
    want = [line.strip() for line in old_lines]
    n = len(old_lines)
    hits = [i for i in range(len(file_lines) - n + 1) if stripped[i : i + n] == want]
    if len(hits) > 1:
        starts = ", ".join(str(i + 1) for i in hits)
        raise ValueError(f"`old` matches (ignoring whitespace) at lines {starts}; include more surrounding context")
    first = next((k for k, w in enumerate(want) if w), None)
    if not hits:
        match = difflib.get_close_matches(want[first], stripped, n=1, cutoff=0) if first is not None else []
        if not match:
            raise ValueError("`old` not found in file; re-read the exact lines and copy them verbatim")
        line_no = stripped.index(match[0])
        actual, mine = file_lines[line_no], old_lines[first]
        raise ValueError(
            f"`old` not found. Closest line in the file is line {line_no + 1}: {actual!r} "
            f"(leading spaces: {_indent(actual)}); your first line was {mine!r} (leading spaces: {_indent(mine)}). "
            "Copy the text exactly as shown."
        )
    i = hits[0]
    delta = 0 if first is None else _indent(file_lines[i + first]) - _indent(old_lines[first])
    new_lines = new.rstrip("\n").split("\n") if new.rstrip("\n") else []
    if delta > 0:
        new_lines = [" " * delta + line if line.strip() else line for line in new_lines]
    elif delta < 0:
        new_lines = [line[min(-delta, len(line) - len(line.lstrip(" "))) :] for line in new_lines]
    file_lines[i : i + n] = new_lines
    target.write_text("\n".join(file_lines), encoding="utf-8")
    return (
        f"edited {path}: replaced {n} line(s) with {len(new_lines)} line(s) (note: your `old` had different "
        f"indentation than the file; matched ignoring whitespace and re-indented `new` by {delta:+d} spaces)"
    )


@neatlogs.span(kind="TOOL", tool_name="run_tests")
def run_tests_tool(work: Path, pattern: str = "") -> str:
    passed, output = run_tests(work, pattern)
    return f"{'PASSED' if passed else 'FAILED'}\n{output}"


HANDLERS = {"list_files": list_files, "read_file": read_file, "write_file": write_file, "edit_file": edit_file, "run_tests": run_tests_tool}


def current_trace_id() -> str | None:
    """The active neatlogs trace id, read from the W3C traceparent the SDK can inject."""
    carrier: dict[str, str] = {}
    if neatlogs.inject_trace_context(carrier) and "traceparent" in carrier:
        return carrier["traceparent"].split("-")[1]
    return None


@neatlogs.span(kind="WORKFLOW")
def solve_task(task_id: str, report: str, work: Path) -> dict:
    """Run the agent loop on one task. Returns turns, tokens, stop reason and the trace id."""
    result = {"task_id": task_id, "trace_id": current_trace_id(), "turns": 0,
              "input_tokens": 0, "output_tokens": 0, "stop": None, "summary": ""}
    files = list_files(work)
    messages = [{"role": "user", "content": f"Bug report: {report}\n\nProject files:\n{files}"}]
    system = PROMPT_FILE.read_text(encoding="utf-8")
    edited = False
    while result["turns"] < MAX_TURNS:
        result["turns"] += 1
        extra = {} if MODEL.startswith("claude-haiku-4-5") else {"output_config": {"effort": "medium"}}  # Haiku 4.5 rejects effort
        response = client().messages.create(
            model=MODEL, max_tokens=16000, system=system, tools=TOOLS, messages=messages, **extra,
        )
        result["input_tokens"] += response.usage.input_tokens
        result["output_tokens"] += response.usage.output_tokens
        result["stop"] = response.stop_reason
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            result["summary"] = next((b.text for b in response.content if b.type == "text"), "")
            return result
        tool_results = []
        suite_passed = edited_this_turn = ran_full_suite_this_turn = False
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                content, is_error = HANDLERS[block.name](work, **block.input), False
            except Exception as exc:  # report tool failures back to the model, don't crash the run
                content, is_error = f"Error: {exc}", True
            if not is_error and block.name in ("edit_file", "write_file"):
                edited = edited_this_turn = True
            if block.name == "run_tests" and not block.input.get("pattern"):
                ran_full_suite_this_turn = True
                if content.startswith("PASSED"):
                    suite_passed = True
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error})
        if edited_this_turn and not ran_full_suite_this_turn:  # verify edits ourselves, saving the model a turn
            auto = run_tests_tool(work)
            tool_results.append({"type": "text", "text": "Automatic full test run after your edit(s):\n" + auto})
            if auto.startswith("PASSED"):
                suite_passed = True
        messages.append({"role": "user", "content": tool_results})
        if suite_passed and edited:  # full suite green after an edit: done, skip the verify/summary turn
            result["stop"] = "suite_passed"
            text = "".join(b.text for b in response.content if b.type == "text")
            result["summary"] = text or "Fixed the bug; full test suite passes."
            return result
    result["stop"] = "max_turns"
    return result


def solve(task: dict, work: Path) -> dict:
    """Solve one task in `work`, then judge it ourselves: pass = the full test suite passes."""
    started = time.time()
    result = solve_task(task["id"], task["report"], work)
    result["passed"], _ = run_tests(work)
    result["duration_s"] = round(time.time() - started, 1)
    return result
