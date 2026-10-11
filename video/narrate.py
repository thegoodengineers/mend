"""Generate one MP3 per script row using edge-tts.

Usage:
    python video/narrate.py
Output: video/vo/00.mp3, 01.mp3, …
"""

import asyncio
import csv
import io
import re
import sys
from pathlib import Path

import edge_tts

VOICE = "en-US-AndrewNeural"
SCRIPT = Path(__file__).parent / "script.md"
OUT = Path(__file__).parent / "vo"


def parse_script(text: str) -> list[tuple[int, str]]:
    """Return list of (scene_number, narration) from the Markdown table."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 4:
            continue
        num_str = cols[0]
        narration = cols[3]
        if not num_str.isdigit():
            continue
        rows.append((int(num_str), narration))
    return rows


async def synthesise(scene: int, text: str) -> None:
    out_path = OUT / f"{scene:02d}.mp3"
    if out_path.exists():
        print(f"  skip {out_path.name} (exists)")
        return
    comm = edge_tts.Communicate(text, VOICE)
    await comm.save(str(out_path))
    print(f"  wrote {out_path.name}")


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = parse_script(SCRIPT.read_text(encoding="utf-8"))
    if not rows:
        sys.exit("No rows found in script.md")
    await asyncio.gather(*(synthesise(n, t) for n, t in rows))
    print(f"Done — {len(rows)} files in {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
