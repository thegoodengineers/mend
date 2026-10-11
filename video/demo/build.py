"""Build video/demo/mend-demo.mp4: the submission demo (3 minutes or less), generated, never sped up.

    python video/demo/build.py     (system Python with playwright + edge-tts; ffmpeg on PATH)

Each scene = one narration line (edge-tts) + one visual: a clip of the live recording
(video/live/mend-live.mp4, real speed), a screenshot of a real section of the site (index.html),
real CLI output, or a title card. Scene length = narration + a short pause. Every number spoken is
in the README (checked by mend/verify.py), the business plan, or evidence/.
"""

import asyncio
import html
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
LIVE = ROOT / "video" / "live" / "mend-live.mp4"
VOICE, BG, PAD = "en-US-AndrewNeural", "e6e6dd", 0.7
ZOOM, FADE = 0.04, 0.25  # still scenes push in by 4%; 0.25 s fade at each cut
W, H = 1920, 1080

# (id, narration, visual): visual is ("clip", start_s) | ("shot", css_selector) | ("page", file, css_selector | None)
# | ("card", label, title, body) | ("term", file)
SCENES = [
    ("hook", "Our agent just broke working code to fix one line. Then it found out why, and fixed itself.", ("clip", 40.0)),
    ("title", "This is Mend: an agent that fixes itself, and proves it.", ("shot", "header")),
    ("arch", "A worker agent does the job. neatlogs traces every model call and tool call. A supervisor reads those traces back over "
             "the neatlogs MCP server, diagnoses the failure, and has Claude Code patch the worker.", ("shot", "#how")),
    ("runtime", "Here is a live run, at real speed. The worker reads part of a long file, then rewrites all of it, and the test suite breaks.",
     ("clip", 22.0)),
    ("reasoning", "Mend's diagnosis, straight from the trace: it read two hundred of two hundred and thirty-three lines, then rewrote "
                  "the whole file, deleting the rest.",
     ("card", "Diagnosis · from the neatlogs trace", "Read 200 of 233 lines. Rewrote all of them.",
      "The whole-file write silently deleted everything after line 200. Fix: a precise edit tool, and partial reads that say how much is left.")),
    ("entire", "Claude Code writes the fix, and Entire links the commit to the session that wrote it. Mend reads past checkpoints back, "
               "so it never retries a fix that failed. And Entire's blame shows Mend wrote sixty-nine percent of the worker's instructions.",
     ("term", "entire-explain.txt")),
    ("result", "Same task, same model, after the fix: four turns, and it passes.", ("clip", 88.5)),
    ("gate", "Every change must earn its place. Mend re-runs all twenty-nine tasks and keeps a fix only if the numbers improve. "
             "Five fixes were kept. Six were reverted.", ("shot", "#rounds .card")),
    ("ablation", "Take a kept fix out again, and costs rise by up to sixty-one percent.", ("shot", "#ablation")),
    ("heldout", "Is it overfitting? On ten bugs it never saw, it went from nine out of ten to ten out of ten.", ("shot", "#heldout")),
    ("realworld", "On bugs in a real open-source library, from two or three out of eight, to eight out of eight, with eighty-two percent fewer tokens.",
     ("shot", "#realworld")),
    ("hardware", "Then, domains it was never built for. On chip designs and circuits: the same fixes, with about sixty percent fewer tokens. "
                 "On a larger sensor circuit, the original refused some bugs. The repaired worker fixed all eight.",
     ("page", "hardware.html", None)),
    ("explorer", "Every step it took is read back from its neatlogs trace.", ("page", "circuit.html", None)),
    ("honesty", "But a pass isn't proof. Mend audits every passing fix against the correct design, and impossible tasks catch cheating. "
                "Self-repair had made the worker cheat more: six of twelve, up from four.", ("page", "index.html", "#real")),
    ("antigaming", "So Mend repaired that too. Cheating fell from six to two, but tokens rose seventeen percent, and the gate said no. "
                   "That is a judgment call, so a person made it, once, and it is on record.",
     ("card", "Round 11 · anti-gaming", "Cheating 6 → 2 of 12.",
      "Tokens +17%, over the gate's 15% limit, so the gate reverted it. A person accepted the trade-off, once. It is now a precedent every diagnosis follows.")),
    ("second", "And it isn't tied to one agent. On a SQL analyst it had never seen: one round, the same answers, thirty-seven percent cheaper. "
               "Forty-two, on a database it never saw.",
     ("card", "A second agent · SQL data analyst", "Same answers. 37% cheaper.",
      "One Mend round, the same supervisor, the same gate. On a database it never saw: 42% cheaper, and one new mistake, reported.")),
    ("guards", "Every failure becomes a neatlogs detection, and every gate verdict is written back into neatlogs as a trace.",
     ("card", "neatlogs regression guards · audit log", "Failures become detections.",
      "4 detections from Mend's own failures. Every keep or revert is a mend-gate trace. neatroots: 4 of 4 original runs flagged, 0 of 4 repaired.")),
    ("business", "We planned the business in cfo.ai. Self-repair cut our cost per task from four cents to one and a half, "
                 "and a full repair round now costs about fifty-seven cents.",
     ("card", "cfo.ai business plan · measured costs", "$0.040 → $0.015 per task.",
      "A full repair round: about $0.57 (diagnosis $0.13 + re-run $0.44). Pricing, revenue and runway modelled in cfo.ai.")),
    ("close", "Mend. Agents that fix themselves, and prove it.",
     ("card", "github.com/thegoodengineers/mend · thegoodengineers.github.io/mend", "Mend.", "Agents that fix themselves, and prove it.")),
]

CARD = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@800&family=Instrument+Serif:ital@1&family=Inter:wght@600&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>html,body{margin:0;width:1920px;height:1080px;background:#e6e6dd;color:#0f0f0d;font-family:Inter}
.w{padding:150px 160px} p.l{font:600 30px Inter;color:#5d5d55;margin:0 0 30px} h1{font:800 120px/1 'Inter Tight';letter-spacing:-.045em;margin:0 0 36px}
p.b{font:italic 400 54px/1.3 'Instrument Serif',serif;color:#2b2b27;margin:0;max-width:1550px}
pre{font:400 27px/1.55 'JetBrains Mono',monospace;background:#f4f4ee;border-radius:28px;padding:44px 50px;margin:0;white-space:pre-wrap;color:#0f0f0d}</style></head>
<body><div class="w">__BODY__</div></body></html>"""


async def tts() -> list[Path]:
    import edge_tts
    out = []
    for sid, text, _ in SCENES:
        f = HERE / "vo" / f"{sid}.mp3"
        f.parent.mkdir(exist_ok=True)
        await edge_tts.Communicate(text, VOICE).save(str(f))
        out.append(f)
    return out


def duration(f: Path) -> float:
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]))


def stills() -> dict[str, Path]:
    """Render every non-clip visual to a 1920x1080 PNG."""
    from playwright.sync_api import sync_playwright
    img = HERE / "img"
    img.mkdir(exist_ok=True)
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        site = b.new_page(viewport={"width": 1600, "height": 1000}, reduced_motion="reduce", device_scale_factor=1.2)
        site.goto((ROOT / "index.html").as_uri())
        site.wait_for_timeout(1800)
        card = b.new_page(viewport={"width": W, "height": H})
        view = b.new_page(viewport={"width": 1600, "height": 900}, reduced_motion="reduce", device_scale_factor=1.2)  # 1920x1080
        for sid, _, vis in SCENES:
            f = img / f"{sid}.png"
            if vis[0] == "shot":
                site.locator(vis[1]).first.screenshot(path=str(f))
            elif vis[0] == "page":  # one full screen of a page, scrolled to a section
                view.goto((ROOT / vis[1]).as_uri())
                view.wait_for_timeout(1800)
                if vis[2]:
                    view.evaluate("s => document.querySelector(s).scrollIntoView({block: 'start'})", vis[2])
                    view.wait_for_timeout(500)
                view.screenshot(path=str(f))
            elif vis[0] in ("card", "term"):
                if vis[0] == "card":
                    body = f'<p class="l">{html.escape(vis[1])}</p><h1>{html.escape(vis[2])}</h1><p class="b">{html.escape(vis[3])}</p>'
                else:
                    text = (HERE / vis[1]).read_text(encoding="utf-8")
                    text = re.sub(r"<[^>]+@[^>]+>", "", text)  # no email addresses on screen
                    text = "\n".join(text.splitlines()[:18])  # fits the frame
                    body = f'<p class="l">entire checkpoint explain c07f702 · real CLI output</p><pre>{html.escape(text)}</pre>'
                card.set_content(CARD.replace("__BODY__", body))
                card.wait_for_timeout(1200)
                card.screenshot(path=str(f))
            else:
                continue
            out[sid] = f
        b.close()
    return out


def scene_clip(sid: str, vis: tuple, seconds: float, still: Path | None) -> Path:
    out = HERE / "clips" / f"{sid}.mp4"
    out.parent.mkdir(exist_ok=True)
    fit = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x{BG},setsar=1,fps=30"
    # soft dip to the page colour between scenes, so cuts don't jump
    fade = f"fade=t=in:st=0:d={FADE}:c=0x{BG},fade=t=out:st={seconds - FADE:.2f}:d={FADE}:c=0x{BG}"
    if vis[0] == "clip":
        cmd = ["-ss", f"{vis[1]}", "-t", f"{seconds:.2f}", "-i", str(LIVE), "-vf", f"{fit},{fade}", "-an"]
    else:
        # slow push-in (ZOOM over the whole scene), rendered at 2x first so the motion doesn't jitter
        step = ZOOM / (seconds * 30)
        push = (f"scale={W * 2}:{H * 2},zoompan=z='1+{step:.7f}*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d=1:s={W}x{H}:fps=30")
        cmd = ["-framerate", "30", "-loop", "1", "-t", f"{seconds:.2f}", "-i", str(still), "-vf", f"{fit},{push},{fade}"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *cmd, "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def main() -> None:
    voices = asyncio.run(tts())
    images = stills()
    clips, starts, t = [], [], 0.0
    for (sid, _, vis), vo in zip(SCENES, voices):
        seconds = duration(vo) + PAD
        clips.append(scene_clip(sid, vis, seconds, images.get(sid)))
        starts.append(t)
        t += seconds
    listing = HERE / "clips" / "list.txt"
    listing.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    silent = HERE / "clips" / "video.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(silent)], check=True)
    inputs, filt = ["-i", str(silent)], []
    for i, (vo, start) in enumerate(zip(voices, starts), start=1):
        inputs += ["-i", str(vo)]
        ms = int((start + 0.2) * 1000)
        filt.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
    filt.append("".join(f"[a{i}]" for i in range(1, len(voices) + 1)) + f"amix=inputs={len(voices)}:normalize=0,apad[voice]")
    # quiet generated music bed (video/demo/music.py), ducked under the narration
    music = HERE / "music.wav"
    subprocess.run([sys.executable, str(HERE / "music.py"), f"{t + 1:.0f}", str(music)], check=True, capture_output=True)
    inputs += ["-i", str(music)]
    m = len(voices) + 1
    filt.append("[voice]asplit[v1][v2]")
    filt.append(f"[{m}:a]volume=0.10[bed];[bed][v1]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=600[duck]")
    filt.append("[v2][duck]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5[a]")
    out = HERE / "mend-demo.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]",
                    "-t", f"{t:.2f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", str(out)], check=True)
    print(f"wrote {out.relative_to(ROOT)}: {t:.1f} s ({'OK, under 3:00' if t <= 180 else 'TOO LONG'}), {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
