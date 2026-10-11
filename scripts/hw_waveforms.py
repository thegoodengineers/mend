"""Capture simulation waveforms of hardware designs, correct and with a planted bug -> evidence/waveforms.json

    python scripts/hw_waveforms.py

Each case simulates one design twice in the Amaranth simulator: the correct design, and a copy with one
task's bug planted (from tasks/hardware.json). Every listed signal is sampled once per clock cycle.
The hardware page draws these as timing diagrams and highlights the cycles where the bug shows.
"""

import json
import os
import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mend.tasks import HARDWARE_FILE, load_tasks, prepare  # noqa: E402

# Run inside a sandbox copy so `import hwlib` picks up that copy (correct, or with the bug planted).
PROBES = {
    "uart": ("HW06", "UartTx(1) sends 0x31 (ASCII '1'), one bit per cycle", """
from amaranth.sim import Simulator
from hwlib.uart import UartTx
dut = UartTx(1); rows = []
async def bench(ctx):
    ctx.set(dut.data, 0x31); ctx.set(dut.start, 1)
    for cyc in range(13):
        rows.append({"start": ctx.get(dut.start), "busy": ctx.get(dut.busy), "tx": ctx.get(dut.tx)})
        await ctx.tick(); ctx.set(dut.start, 0)
"""),
    "pwm": ("HW07", "PWM(8) with duty 3: high for 3 of every 8 cycles", """
from amaranth.sim import Simulator
from hwlib.pwm import PWM
dut = PWM(8); rows = []
async def bench(ctx):
    ctx.set(dut.duty, 3)
    for cyc in range(16):
        rows.append({"out": ctx.get(dut.out)}); await ctx.tick()
"""),
    "counter": ("HW01", "ModCounter(4), enabled: counts 0-3, wrap pulses on 3", """
from amaranth.sim import Simulator
from hwlib.counter import ModCounter
dut = ModCounter(4); rows = []
async def bench(ctx):
    ctx.set(dut.en, 1)
    for cyc in range(10):
        rows.append({"count": ctx.get(dut.count), "wrap": ctx.get(dut.wrap)}); await ctx.tick()
"""),
}
TAIL = """
sim = Simulator(dut); sim.add_clock(1e-6); sim.add_testbench(bench); sim.run()
import json; print(json.dumps(rows))
"""


def capture(work: Path, code: str) -> list[dict]:
    env = {**os.environ, "PYTHONPATH": str(work)}
    out = subprocess.run([sys.executable, "-c", code + TAIL], cwd=work, env=env, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
    tasks = {t["id"]: t for t in load_tasks(HARDWARE_FILE)}
    result = {}
    for name, (task_id, caption, code) in PROBES.items():
        task = tasks[task_id]
        broken = prepare(task)
        result[name] = {"caption": caption, "task": task_id, "title": task["title"], "report": task["report"],
                        "correct": capture(ROOT / "hardware", code), "buggy": capture(broken, code)}
        shutil.rmtree(broken, ignore_errors=True)
        diff = sum(a != b for a, b in zip(result[name]["correct"], result[name]["buggy"]))
        print(f"{name}: {len(result[name]['correct'])} cycles, {diff} differ ({task_id})")
    (ROOT / "evidence" / "waveforms.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
