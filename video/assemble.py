"""Assemble clips + voice-over into final.mp4 using ffmpeg.

Joins clips in order, mixes CC BY ambient music (ducked under voice),
normalises loudness to -14 LUFS, writes video/final.mp4.

Usage:
    python video/assemble.py [--music path/to/ambient.mp3]
    If --music is omitted, the voice track plays with no background music.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

CLIPS_DIR = Path(__file__).parent / "clips"
VO_DIR = Path(__file__).parent / "vo"
OUT = Path(__file__).parent / "final.mp4"
TOTAL_SCENES = 13


def run(args: list[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"ffmpeg error:\n{result.stderr}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--music", help="Path to CC BY ambient audio file")
    opts = parser.parse_args()

    clips = [CLIPS_DIR / f"{i:02d}.mp4" for i in range(1, TOTAL_SCENES + 1)]
    vos = [VO_DIR / f"{i:02d}.mp3" for i in range(1, TOTAL_SCENES + 1)]

    missing = [p for p in clips + vos if not p.exists()]
    if missing:
        sys.exit("Missing files:\n" + "\n".join(str(p) for p in missing))

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # Step 1: mux each clip with its VO
        muxed = []
        for i in range(1, TOTAL_SCENES + 1):
            out = tmp / f"{i:02d}_muxed.mp4"
            run(["ffmpeg", "-y",
                 "-i", str(clips[i - 1]),
                 "-i", str(vos[i - 1]),
                 "-c:v", "copy", "-c:a", "aac", "-shortest",
                 str(out)])
            muxed.append(out)

        # Step 2: concatenate
        concat_list = tmp / "concat.txt"
        concat_list.write_text("\n".join(f"file '{p}'" for p in muxed))
        joined = tmp / "joined.mp4"
        run(["ffmpeg", "-y",
             "-f", "concat", "-safe", "0", "-i", str(concat_list),
             "-c", "copy", str(joined)])

        # Step 3: mix music (optional)
        if opts.music:
            music_path = Path(opts.music)
            if not music_path.exists():
                sys.exit(f"Music file not found: {music_path}")
            mixed = tmp / "mixed.mp4"
            # Duck music to -18 dB under voice; voice at 0 dB
            run(["ffmpeg", "-y",
                 "-i", str(joined),
                 "-stream_loop", "-1", "-i", str(music_path),
                 "-filter_complex",
                 "[1:a]volume=0.12[music];[0:a][music]amix=inputs=2:duration=first[aout]",
                 "-map", "0:v", "-map", "[aout]",
                 "-c:v", "copy", "-c:a", "aac", "-shortest",
                 str(mixed)])
            source = mixed
        else:
            source = joined

        # Step 4: normalise to -14 LUFS
        run(["ffmpeg", "-y",
             "-i", str(source),
             "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
             "-c:v", "copy", "-c:a", "aac",
             str(OUT)])

    print(f"Done — wrote {OUT}")


if __name__ == "__main__":
    main()
