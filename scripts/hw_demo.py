"""Try the hardware transfer test by hand (no API key needed).

    python scripts/hw_demo.py bug HW06          # plant one bug, run the simulation testbenches, see them fail
    python scripts/hw_demo.py bugs              # every hardware bug: does its testbench catch it?
    python scripts/hw_demo.py list              # every design, hwlib (benchmark) and hwkit (extensions)
    python scripts/hw_demo.py verilog uart      # print a design as Verilog (needs: pip install amaranth-yosys)
    python scripts/hw_demo.py verilog all       # write every design to hwkit/verilog
    python scripts/hw_demo.py stats             # flip-flops and logic per design (writes hwkit/RESOURCES.md)
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "hardware"))
sys.path.insert(0, str(ROOT / "hwkit"))

from mend.tasks import HARDWARE_FILE, load_tasks, prepare, run_tests  # noqa: E402

DESIGNS = {  # name -> (module, class, constructor args, ports)
    "counter": ("hwlib.counter", "ModCounter", (10,), ["en", "count", "wrap"]),
    "alu": ("hwlib.alu", "ALU", (), ["a", "b", "op", "result", "zero", "carry"]),
    "fifo": ("hwlib.fifo", "SyncFIFO", (8, 4), ["w_en", "w_data", "r_en", "r_data", "level", "empty", "full"]),
    "uart": ("hwlib.uart", "UartTx", (4,), ["start", "data", "tx", "busy"]),
    "pwm": ("hwlib.pwm", "PWM", (8,), ["duty", "out"]),
    "debounce": ("hwlib.debounce", "Debouncer", (4,), ["raw", "out"]),
    "crc": ("hwlib.crc", "Crc8Byte", (), ["crc_in", "data", "crc_out"]),
    "bin2gray": ("hwlib.gray", "BinToGray", (8,), ["bin", "gray"]),
    "gray2bin": ("hwlib.gray", "GrayToBin", (8,), ["gray", "bin"]),
    # hwkit: designs outside the pinned benchmark sandbox
    "uart_rx": ("hwkit.uart_rx", "UartRx", (4,), ["rx", "data", "valid", "frame_err", "busy"]),
    "spi": ("hwkit.spi", "SpiMaster", (2,), ["start", "tx_data", "miso", "sclk", "mosi", "cs_n", "busy", "rx_data", "done"]),
    "lfsr": ("hwkit.lfsr", "LFSR", (16, 0xACE1), ["en", "state", "out"]),
    "edge": ("hwkit.sync", "EdgeDetect", (), ["raw", "level", "rise", "fall"]),
    "sevenseg": ("hwkit.sevenseg", "SevenSeg", (), ["digit", "blank", "segments"]),
    "uart_echo": ("hwkit.echo", "UartEcho", (4, 16), ["rx", "tx", "overflow", "frame_err"]),
}

YOSYS_PASSES = "proc\nflatten\nopt -full\nmemory_collect\nsimplemap\nopt -full\nclean -purge\nwrite_json\n"


def try_bug(task_id: str) -> bool:
    task = next(t for t in load_tasks(HARDWARE_FILE) if t["id"] == task_id)
    edit = task["edits"][0]
    print(f"{task['id']}: {task['title']}\nbug report: {task['report']}")
    print(f"planted in {edit['file']}:\n  - {edit['find']}\n  + {edit['replace']}")
    work = prepare(task)
    ok, out = run_tests(work)
    shutil.rmtree(work, ignore_errors=True)
    failed = [line.split(" - ")[0].removeprefix("FAILED ") for line in out.splitlines() if line.startswith("FAILED")]
    print("testbenches:", "all pass (bug NOT caught)" if ok else f"{len(failed)} fail -> " + ", ".join(failed))
    return not ok


def build(name: str):
    import importlib

    module, cls, args, ports = DESIGNS[name]
    design = getattr(importlib.import_module(module), cls)(*args)
    return design, [getattr(design, p) for p in ports]


def signature(name: str) -> str:
    _, cls, args, _ = DESIGNS[name]
    return f"{cls}({', '.join(map(str, args))})"


def to_verilog(name: str) -> str:
    from amaranth.back import verilog as backend

    design, ports = build(name)
    return backend.convert(design, ports=ports, name=name, emit_src=False)


def verilog(name: str) -> None:
    if name != "all":
        print(to_verilog(name))
        return
    # Not hardware/verilog: hardware/ is the benchmark sandbox and the worker sees its file list.
    for design in DESIGNS:
        out = ROOT / "hwkit" / "verilog" / f"{design}.v"
        out.write_text(to_verilog(design) + "\n", encoding="utf-8", newline="\n")  # same bytes as `verilog <name> > file`
        print(f"wrote {out.relative_to(ROOT).as_posix()}")


def resources(name: str) -> dict:
    """Map a design to generic cells with the Yosys bundled in amaranth-yosys. That build has no
    `synth` or `techmap`, so flip-flops and simple gates are exact per bit, while arithmetic and
    wide muxes stay whole word-level cells (reported by type, not guessed as gate counts)."""
    import json
    from collections import Counter

    from amaranth._toolchain.yosys import find_yosys
    from amaranth.back import rtlil

    design, ports = build(name)
    il = rtlil.convert(design, ports=ports, name=name, emit_src=False)
    script = f"read_rtlil <<rtlil\n{il}\nrtlil\n{YOSYS_PASSES}"
    out = find_yosys(lambda v: v >= (0, 10)).run(["-q", "-"], script, ignore_warnings=True)
    modules = json.loads(out[out.index("{"):])["modules"].values()
    cells = Counter(c["type"] for m in modules for c in m["cells"].values() if c["type"] != "$scopeinfo")  # metadata, not logic
    return {
        "flip_flops": sum(n for t, n in cells.items() if "DFF" in t),
        "gates": sum(n for t, n in cells.items() if t.startswith("$_") and "DFF" not in t),
        "word_cells": {t.lstrip("$"): n for t, n in sorted(cells.items()) if not t.startswith("$_")},
    }


def stats() -> None:
    rows = ["| Design | Built as | Flip-flops | 1-bit gates | Word-level cells |", "|---|---|---|---|---|"]
    for name in DESIGNS:
        r = resources(name)
        words = ", ".join(f"{t} x{n}" for t, n in r["word_cells"].items()) or "-"
        rows.append(f"| {name} | `{signature(name)}` | {r['flip_flops']} | {r['gates']} | {words} |")
    table = "\n".join(rows)
    print(table)
    (ROOT / "hwkit" / "RESOURCES.md").write_text(
        "# Resources per design\n\n"
        "Generated by `python scripts/hw_demo.py stats` with the Yosys build bundled in amaranth-yosys\n"
        "(proc, flatten, opt, simplemap). Flip-flop counts are exact. That Yosys has no `synth` or `techmap`,\n"
        "so adders, comparators and wide muxes stay as word-level cells; they are listed by type instead of\n"
        "being turned into a guessed gate count. This is not an FPGA LUT count.\n\n" + table + "\n",
        encoding="utf-8", newline="\n")


if __name__ == "__main__":
    cmd = sys.argv[1:] or ["bugs"]
    if cmd[0] == "bug":
        try_bug(cmd[1])
    elif cmd[0] == "bugs":
        caught = []
        for t in load_tasks(HARDWARE_FILE):
            print()
            caught.append(try_bug(t["id"]))
        print(f"\n{sum(caught)} of {len(caught)} hardware bugs caught by the simulation testbenches")
    elif cmd[0] == "list":
        for design, (module, *_) in DESIGNS.items():
            print(f"{design:10} {module}.{signature(design)}")
    elif cmd[0] == "stats":
        stats()
    elif cmd[0] == "verilog" and len(cmd) > 1 and (cmd[1] == "all" or cmd[1] in DESIGNS):
        verilog(cmd[1])
    else:
        print(__doc__)
