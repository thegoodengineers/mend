"""Do hwkit's testbenches catch real mistakes? Plant one mutant at a time in a temp copy and run them.

    python scripts/hwkit_mutants.py        # every mutant must make at least one testbench fail

No API key needed. Each mutant is a single plausible slip (off-by-one, wrong bit order, wrong edge).
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MUTANTS = [  # (file in hwkit/hwkit, find, replace, what it breaks)
    ("uart_rx.py", "timer.eq(self.divisor // 2 - 1)", "timer.eq(self.divisor - 1)", "samples at the end of each bit, not the middle"),
    ("uart_rx.py", "shift.eq(Cat(shift[1:], line))", "shift.eq(Cat(line, shift[:7]))", "bit order reversed (MSB first)"),
    ("uart_rx.py", "with m.If(bit == 7):", "with m.If(bit == 6):", "only 7 data bits"),
    ("uart_rx.py", "m.next = \"IDLE\"  # glitch, not a start bit", "m.d.sync += timer.eq(self.divisor - 1)\n                        m.next = \"DATA\"", "no glitch rejection"),
    ("uart_rx.py", "m.d.sync += self.frame_err.eq(1)\n", "m.d.sync += [self.data.eq(shift), self.valid.eq(1)]\n", "bad stop bit accepted"),
    ("uart_rx.py", "m.d.sync += [meta.eq(self.rx), line.eq(meta)]", "m.d.comb += line.eq(self.rx)", "no synchroniser"),
    ("lfsr.py", "8: (8, 6, 5, 4)", "8: (8, 6, 5)", "8-bit taps not maximal"),
    ("lfsr.py", "self.state.eq(Cat(feedback, self.state[:-1]))", "self.state.eq(Cat(self.state[1:], feedback))", "shifts the wrong way"),
    ("lfsr.py", "with m.If(self.en):", "with m.If(1):", "ignores enable"),
    ("spi.py", "in_shift.eq(Cat(self.miso, in_shift[:7]))", "in_shift.eq(Cat(in_shift[1:], self.miso))", "reads LSB first"),
    ("spi.py", "self.mosi.eq(out_shift[7])", "self.mosi.eq(out_shift[0])", "sends LSB first"),
    ("spi.py", "with m.If(bits_left == 1):", "with m.If(bits_left == 2):", "7-bit transfer"),
    ("spi.py", "with m.Elif(~self.sclk):  # rising edge: sample", "with m.Elif(self.sclk):  # rising edge: sample", "wrong clock phase"),
    ("sevenseg.py", "0x7F, 0x6F, 0x77, 0x7C", "0x7F, 0x67, 0x77, 0x7C", "9 drawn without its bottom segment"),
    ("sevenseg.py", "with m.If(~self.blank):", "with m.If(1):", "blank ignored"),
    ("sync.py", "self.rise.eq(self.level & ~prev)", "self.rise.eq(self.level)", "rise is a level, not a pulse"),
    ("sync.py", "m.d.sync += [meta.eq(self.raw), self.level.eq(meta), prev.eq(self.level)]", "m.d.sync += [self.level.eq(self.raw), prev.eq(self.level)]", "one-flop synchroniser"),
    ("echo.py", "fifo.r_en.eq(~fifo.empty & ~utx.busy)", "fifo.r_en.eq(~fifo.empty)", "drops bytes while transmitting"),
    ("echo.py", "fifo.w_en.eq(urx.valid)", "fifo.w_en.eq(urx.busy)", "writes garbage while receiving"),
]


def run(work: Path) -> bool:
    # Leave out the Verilog up-to-date check: any edit to a design changes its Verilog, so it would
    # "catch" every mutant and say nothing about whether the behavioural testbenches would.
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "-W", "ignore",
                           "--ignore=tests/test_verilog_export.py"],
                          cwd=work / "hwkit", capture_output=True, text=True, timeout=300)
    return proc.returncode == 0


def copy() -> Path:
    work = Path(tempfile.mkdtemp(prefix="hwkit-mutant-"))
    shutil.copytree(ROOT / "hwkit", work / "hwkit", ignore=shutil.ignore_patterns("__pycache__", "verilog"))
    shutil.copytree(ROOT / "hardware", work / "hardware", ignore=shutil.ignore_patterns("__pycache__"))
    return work


def main() -> int:
    work = copy()  # control: the unmutated copy must pass, or every mutant would look caught
    try:
        if not run(work):
            print("the unmutated copy fails its testbenches; fix that first")
            return 2
    finally:
        shutil.rmtree(work, ignore_errors=True)
    caught = 0
    for file, find, replace, why in MUTANTS:
        work = copy()
        try:
            path = work / "hwkit" / "hwkit" / file
            text = path.read_text(encoding="utf-8")
            if text.count(find) != 1:
                print(f"BROKEN MUTANT  {file}: find text must occur exactly once: {find!r}")
                return 2
            path.write_text(text.replace(find, replace), encoding="utf-8")
            ok = run(work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        caught += not ok
        print(f"{'caught ' if not ok else 'MISSED '} {file:12} {why}")
    print(f"\n{caught} of {len(MUTANTS)} mutants caught by hwkit's testbenches")
    return 0 if caught == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
