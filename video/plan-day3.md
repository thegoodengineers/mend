# Video plan for Monday (draft 3): fit tonight's results into 3:00

The current cut is 2:43 (17 scenes, `video/demo/build.py`). Tonight's work adds four stories judges will
care about: hardware transfer, fix audit plus impossible probes, the anti-gaming rounds, and a second agent. Budget: about
2:58 with scene 5. Every number below is in the README and checked by `mend.verify`; re-check before recording.

## Cuts and merges (frees about 30 s)
- `problem` (6 s): fold into `hook`. The hook already shows the failure.
- `title` (4.4 s): keep it, but put the title card under the end of the hook narration.
- `provenance` (9.5 s): shorten to one line inside `entire`: "...and Entire's blame shows 69% of the
  worker's instructions were written by Mend itself."
- `ablation` (12.4 s): shorten to 6 s: "Remove a kept fix and costs rise up to 61%."
- `judgment` (8.6 s): fold into the new honesty scene (ask-once is part of "knowing when not to fix").

## New scenes
1. **hardware** (about 10 s). Visual: a live recording of `hardware.html`: scroll the UART timing diagram,
   then cut to the circuit explorer.
   Narration: "Then we gave it bugs in chip designs and circuits it had never seen. The original worker
   refused some: 'this is a hardware issue'. The self-repaired one ran the tests and fixed every one."
2. **explorer** (about 4 s, cut from 8 to make room for scene 5). Visual: a live recording of
   `circuit.html`: click BD08, the log plays, the part glows.
   Narration: "Every step it took is read back from its neatlogs trace."
3. **honesty** (about 14 s). Visual: the README/site "Are the passing fixes real?" table, then the
   probes cards.
   Narration: "But a pass isn't proof. Mend audits every passing fix against the correct design, and
   six impossible tasks catch cheating. Self-repair made the worker cheat a little more: six of twelve.
   So Mend tried to repair that too."
4. **antigaming** (about 10 s). Visual: the rounds table rows 10-11 plus the gate's verdict trace in
   neatlogs.
   Narration (from the round 10-11 records): "Its first fix cut cheating by one and cost 21% more
   tokens: reverted. The second cut cheating from six to two, but tokens rose 17%, over the gate's 15%.
   The gate reverted it. That trade-off was ours to make, so we accepted it, and it's on record."
5. **second agent** (about 7 s). Visual: the site card "A different agent", then the README analyst
   table.
   Narration: "And it's not tied to one agent. On a SQL analyst it had never seen: one round, same
   answers, 37% cheaper. On a database it never saw, 42%."
   Re-check both numbers in the README before recording (verify computes them).

## Recording notes
- Use Playwright `record_video_dir` for the hardware and explorer walkthroughs: 1600x900, scaled to 1080p
  in `build.py`, with a new visual type `("file", path)`.
- Keep the music bed and the push-in on stills; the walkthrough clips get no push-in.
- Check the final length is under 3:00 (`build.py` prints it), and listen once end to end.
