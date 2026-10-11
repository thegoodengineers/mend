"""Try the hardware transfer test by hand (no API key needed).

    python scripts/hw_demo.py bug HW06          # plant one bug, run the simulation testbenches, see them fail
    python scripts/hw_demo.py bugs              # every hardware bug: does its testbench catch it?
    python scripts/hw_demo.py verilog uart      # print a design as Verilog (needs: pip install amaranth-yosys)
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "hardware"))

from mend.tasks import HARDWARE_FILE, load_tasks, prepare, run_tests  # noqa: E402

DESIGNS = {  # name -> (module, class, constructor args, ports)
    "counter": ("hwlib.counter", "ModCounter", (10,), ["en", "count", "wrap"]),
    "alu": ("hwlib.alu", "ALU", (), ["a", "b", "op", "result", "zero", "carry"]),
    "fifo": ("hwlib.fifo", "SyncFIFO", (8, 4), ["w_en", "w_data", "r_en", "r_data", "level", "empty", "full"]),
    "uart": ("hwlib.uart", "UartTx", (4,), ["start", "data", "tx", "busy"]),
    "pwm": ("hwlib.pwm", "PWM", (8,), ["duty", "out"]),
    "debounce": ("hwlib.debounce", "Debouncer", (4,), ["raw", "out"]),
    "crc": ("hwlib.crc", "Crc8Byte", (), ["crc_in", "data", "crc_out"]),
}


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


def verilog(name: str) -> None:
    import importlib

    from amaranth.back import verilog as backend

    module, cls, args, ports = DESIGNS[name]
    design = getattr(importlib.import_module(module), cls)(*args)
    print(backend.convert(design, ports=[getattr(design, p) for p in ports], name=name, emit_src=False))


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
    elif cmd[0] == "verilog":
        verilog(cmd[1])
    else:
        print(__doc__)
