# video/

Demo video pipeline for Mend.

## Steps

```
python video/narrate.py          # generates video/vo/00.mp3 … 12.mp3
python video/record.py           # generates video/clips/00.mp4 … 12.mp4
python video/assemble.py         # writes video/final.mp4  (no music)
python video/assemble.py --music ambient.mp3   # with CC BY background
```

## Music credit

Background music must be CC BY licensed. Recommended:

**"Chill Abstract Intention"** by Coma-Media  
Source: https://pixabay.com/music/ambient-chill-abstract-intention-12099/  
License: Pixabay Content License (free to use, attribution appreciated)

If you use a different track, record its title, artist, source URL and license here before publishing.

## Output

`video/final.mp4` — 1920×1080, ≤3 min, −14 LUFS normalised, H.264/AAC.
