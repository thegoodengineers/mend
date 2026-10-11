"""Record each scene for its narration duration + 1.2 s using Playwright.

Usage:
    python video/record.py
Output: video/clips/NN.mp4
"""

import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

SCENES_HTML = (Path(__file__).parent / "scenes" / "scenes.html").resolve().as_uri()
VO_DIR = Path(__file__).parent / "vo"
CLIPS_DIR = Path(__file__).parent / "clips"
TOTAL_SCENES = 13
TAIL_SECONDS = 1.2


def mp3_duration(path: Path) -> float:
    """Return duration in seconds via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


async def record_scene(page, scene: int, duration: float) -> None:
    out = CLIPS_DIR / f"{scene:02d}.mp4"
    if out.exists():
        print(f"  skip {out.name} (exists)")
        return
    await page.goto(f"{SCENES_HTML}?scene={scene}")
    await page.wait_for_load_state("networkidle")
    frames: list[bytes] = []
    fps = 25
    total_frames = int((duration + TAIL_SECONDS) * fps)
    interval = 1000 / fps
    for _ in range(total_frames):
        frames.append(await page.screenshot(type="png"))
        await asyncio.sleep(interval / 1000)
    # Write frames to ffmpeg via stdin
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-f", "image2pipe", "-vcodec", "png", "-i", "pipe:0",
        "-vf", "scale=1920:1080",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(out),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    for frame in frames:
        proc.stdin.write(frame)
    proc.stdin.close()
    await proc.wait()
    print(f"  wrote {out.name}  ({duration + TAIL_SECONDS:.1f}s)")


async def main() -> None:
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    durations: dict[int, float] = {}
    for i in range(1, TOTAL_SCENES + 1):
        vo = VO_DIR / f"{i:02d}.mp3"
        if not vo.exists():
            print(f"  WARNING: {vo.name} not found — using 4 s fallback")
            durations[i] = 4.0
        else:
            durations[i] = mp3_duration(vo)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        for i in range(1, TOTAL_SCENES + 1):
            print(f"Recording scene {i}/{TOTAL_SCENES}…")
            await record_scene(page, i, durations[i])
        await browser.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
