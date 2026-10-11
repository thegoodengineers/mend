"""Build docs/post-pack.html: every #neatHack post ready to publish, one click to open X with the text filled in.

    python scripts/post_pack.py

A human publishes each post (attach the image, press Post); this script never posts anything.
Fails if a post is over X's 280-character limit (links count as 23 characters, as X counts them).
"""

import html
import re
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://thegoodengineers.github.io/mend/"
REPO = "https://github.com/thegoodengineers/mend"

# (when, title, text, attachment path relative to the repo or "")
POSTS = [
    ("Now", "The bug it found in itself",
     "our agent found a bug in itself: it read 200 of 233 lines, then rewrote the whole file to change one word, "
     "deleting the rest. it saw this in its own @neatlogs traces and gave itself an edit tool.\n"
     f"same task, live: failed in 15 turns -> passed in 4 #neatHack\n{SITE}",
     "video/live/mend-live.mp4"),
    ("+1 hour", "Is it overfitting?",
     "does self-repair just overfit? we tested on bugs it never saw.\n10 held-out bugs: 9/10 -> 10/10\n"
     f"8 bugs in a real open-source library: 2-3/8 -> 8/8, 82% fewer tokens\n#neatHack\n{SITE}#heldout",
     "docs/img/post-realworld.png"),
    ("+2 hours", "The gate said no, four times",
     "our agent has tried to change itself 9 times. it kept 5. it reverted 4, including one that saved a real 12% "
     "but missed the 15% bar we wrote down in advance. a gate that bends for a near miss isn't a gate #neatHack\n"
     f"{SITE}#rounds",
     "docs/img/post-rounds.png"),
    ("This evening", "69% of its own instructions",
     "ran `entire blame` on our agent's system prompt: 9 of 13 lines were written by its own self-repair sessions. "
     "each line traces to an @EntireHQ checkpoint, the diagnosis behind it, and the @neatlogs traces it read "
     f"#neatHack\n{SITE}#provenance",
     "docs/img/post-11-provenance.png"),
    ("This evening", "Answering 'self-healing is self-defeating'",
     "@neatlogs' founder argues self-healing agents drift unless someone defines \"better\". so our agent only "
     "auto-fixes what has an objective answer, stops and asks a person when a fix is a choice, and follows that "
     f"answer forever after #neatHack\n{SITE}#judgment",
     "docs/img/post-10-judgment.png"),
    ("Tonight", "Error bars on our own gate",
     "we put error bars on every keep/revert decision our agent made about itself, then removed each kept fix "
     "one at a time. two fixes carry the savings (+61% and +39% tokens without them). one barely matters. we say "
     f"so #neatHack\n{SITE}#ablation",
     "docs/img/post-12-ablation.png"),
    ("Monday afternoon", "Verdicts written back into neatlogs",
     "every keep/revert verdict our agent makes about itself now lands in @neatlogs as its own trace, one span "
     "per rule, with a detection on every revert. its observability tool doubles as its audit log #neatHack\n"
     f"{REPO}",
     "your neatlogs dashboard screenshot of the mend-gate workflow"),
]

URL = re.compile(r"https?://\S+")


def x_length(text: str) -> int:
    """Characters as X counts them: every link is 23."""
    return len(URL.sub("x" * 23, text))


def card(i: int, when: str, title: str, text: str, attach: str) -> str:
    n = x_length(text)
    assert n <= 280, f"post {i} '{title}' is {n} characters"
    intent = "https://x.com/intent/post?text=" + urllib.parse.quote(text)
    path = ROOT / attach
    preview = ""
    if path.suffix == ".png" and path.exists():
        preview = f'<img src="../{html.escape(attach)}" alt="">'
    elif path.suffix == ".mp4" and path.exists():
        preview = f'<video src="../{html.escape(attach)}" controls preload="metadata"></video>'
    return f"""<article><p class="when">{i}. {html.escape(when)}</p><h2>{html.escape(title)}</h2>
<pre>{html.escape(text)}</pre><p class="meta">{n}/280 characters · attach: <code>{html.escape(attach)}</code></p>
{preview}<p><a class="btn" href="{html.escape(intent)}" target="_blank" rel="noopener">Open in X with this text</a>
<button onclick="navigator.clipboard.writeText(this.dataset.t)" data-t="{html.escape(text)}">Copy text</button></p></article>"""


if __name__ == "__main__":
    cards = "\n".join(card(i, *p) for i, p in enumerate(POSTS, 1))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mend post pack</title><style>
body{{margin:0;background:#e6e6dd;color:#0f0f0d;font:16px/1.5 Inter,system-ui,sans-serif}} main{{max-width:760px;margin:0 auto;padding:32px 16px}}
article{{background:#f4f4ee;border-radius:20px;padding:22px;margin:18px 0}} h1{{font-size:28px;margin:0 0 6px}} h2{{margin:4px 0 12px;font-size:22px}}
.when{{margin:0;font-weight:600;color:#5d5d55}} pre{{white-space:pre-wrap;font:15px/1.5 inherit;background:#fff;border-radius:12px;padding:14px;margin:0}}
.meta{{color:#5d5d55;font-size:13px}} img,video{{max-width:100%;border-radius:12px;display:block;margin:8px 0}}
.btn,button{{display:inline-block;background:#0f0f0d;color:#fff;border:0;border-radius:999px;padding:9px 16px;font:600 14px inherit;text-decoration:none;cursor:pointer;margin-right:8px}}
button{{background:#5d5d55}}</style></head><body><main>
<h1>#neatHack posts, ready to publish</h1>
<p>For each card: press <b>Open in X</b>, attach the file listed, press Post, then paste the post link into
<code>hackathon.md</code>. Every number is from the README. Built by <code>scripts/post_pack.py</code>; nothing here posts on its own.</p>
{cards}</main></body></html>"""
    (ROOT / "docs" / "post-pack.html").write_text(page, encoding="utf-8")
    for i, (when, title, text, _) in enumerate(POSTS, 1):
        print(f"{i}. {x_length(text):3d} chars  {when}: {title}")
