#!/usr/bin/env python3
"""The page shell every carrychain chart is served in.

One copy, because five copies of a theme drift into five themes. Everything
specific to a chart -- the figure, its key, its notes -- is passed in.

Both themes are token-level: components read `var(--x)` and only the tokens are
redefined, first under `prefers-color-scheme` for the OS setting and then under
`:root[data-theme]` so the viewer's own toggle wins in BOTH directions. Styling
a component inside the media query instead is the bug that makes a toggle work
one way and not the other.
"""

CSS = """
:root{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e6e2d9; --line-2:#cdc7bb; --ink:#191817;
  --dim:#57544e; --faint:#a29d94; --lead-a:#1f3a5f; --lead-b:#c9853a; --grid:#ebe7de; }
@media (prefers-color-scheme:dark){:root{ --paper:#131519; --panel:#1a1d23; --line:#2a2f38;
  --line-2:#3b4250; --ink:#eae7e0; --dim:#a9a49b; --faint:#6c6862;
  --lead-a:#8fb0dd; --lead-b:#e0a048; --grid:#242932; }}
:root[data-theme="dark"]{ --paper:#131519; --panel:#1a1d23; --line:#2a2f38; --line-2:#3b4250;
  --ink:#eae7e0; --dim:#a9a49b; --faint:#6c6862; --lead-a:#8fb0dd; --lead-b:#e0a048;
  --grid:#242932; }
:root[data-theme="light"]{ --paper:#fdfcf9; --panel:#f7f5f0; --line:#e6e2d9; --line-2:#cdc7bb;
  --ink:#191817; --dim:#57544e; --faint:#a29d94; --lead-a:#1f3a5f; --lead-b:#c9853a;
  --grid:#ebe7de; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-size:17px;line-height:1.62}
.wrap{max-width:__MAXW__px;margin:0 auto;padding:56px 22px 90px}
h1{font-size:clamp(27px,4.2vw,38px);line-height:1.12;margin:0 0 14px;
  letter-spacing:-.016em;text-wrap:balance}
.eyebrow{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;
  letter-spacing:.15em;text-transform:uppercase;color:var(--faint);margin:0 0 11px}
.lede{font-size:19.5px;color:var(--dim);margin:0 0 28px;max-width:60ch}
p{margin:0 0 15px;max-width:64ch}
strong{font-weight:650}
.score{display:flex;gap:34px;flex-wrap:wrap;margin:0 0 24px;
  font-family:system-ui,-apple-system,sans-serif}
.score div{display:flex;flex-direction:column;gap:1px}
.score b{font-size:31px;font-weight:600;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums;line-height:1}
.score span{font-size:12px;color:var(--faint);letter-spacing:.03em}
.qc b{color:var(--lead-a)} .pc b{color:var(--lead-b)}
.frame{border:1px solid var(--line);border-radius:5px;background:var(--panel);
  padding:14px 12px 6px;overflow-x:auto}
svg{display:block;width:100%;height:auto}
.tk{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;fill:var(--faint)}
.ax{font-family:system-ui,-apple-system,sans-serif;font-size:12.5px;fill:var(--dim);
  letter-spacing:.02em}
.gl{stroke:var(--grid);stroke-width:1}
.key{display:flex;gap:22px;align-items:center;flex-wrap:wrap;margin:16px 0 0;
  font-family:system-ui,-apple-system,sans-serif;font-size:12.5px;color:var(--dim)}
.sw{display:inline-block;width:17px;height:11px;border-radius:2px;vertical-align:-1px;
  margin-right:7px}
.dt{display:inline-block;width:11px;height:11px;border-radius:50%;vertical-align:-1px;
  margin-right:7px}
.note{font-family:system-ui,-apple-system,sans-serif;font-size:13.5px;color:var(--faint);
  margin-top:22px;max-width:68ch;line-height:1.62}
.note strong{color:var(--dim)}
"""

SHELL = """<title>carrychain &mdash; __TITLE__</title>
<style>__CSS____EXTRA__</style>
<div class="wrap">
  <p class="eyebrow">__EYEBROW__</p>
  <h1>__H1__</h1>
  <p class="lede">__LEDE__</p>
__SCORE__
  <div class="frame">__FIG__</div>
__KEY__
__NOTES__
</div>
"""


def page(title, eyebrow, h1, lede, fig, key="", notes="", score="",
         extra_css="", maxw=1000):
    def block(cls, inner):
        return f'  <div class="{cls}">\n{inner}\n  </div>\n' if inner else ""
    return (SHELL.replace("__CSS__", CSS.replace("__MAXW__", str(maxw)))
                 .replace("__EXTRA__", extra_css)
                 .replace("__TITLE__", title).replace("__EYEBROW__", eyebrow)
                 .replace("__H1__", h1).replace("__LEDE__", lede)
                 .replace("__SCORE__", block("score", score))
                 .replace("__FIG__", fig)
                 .replace("__KEY__", block("key", key))
                 .replace("__NOTES__", notes))


def stat(value, label, cls=""):
    return f'    <div class="{cls}"><b>{value}</b><span>{label}</span></div>'


def note(html):
    return f'  <p class="note">{html}</p>\n'
