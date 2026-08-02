# voice/ — how Adam actually writes

Four files, copied here rather than linked, because a reference that lives in
another repo is one an agent will eventually be told to go and edit. They are
inputs to [../../skills/prose-review/SKILL.md](../../skills/prose-review/SKILL.md).

| file | |
|---|---|
| `voice-profile.md` | the identity: analytical, explanation-first, layered |
| `style-rules.md` | eight positive rules and the operational guidance under them |
| `anti-patterns.md` | what looks like the voice but is platform noise |
| `task-overrides.md` | how the register shifts by mode — explanatory, argument, and so on |

## Where they came from

Derived by `~/Projects/language/hn-scraper` from **434 Hacker News comments** by
`dataviz1000`, clustered into five writing modes: compact_explanatory (234),
extended_explanatory (122), deep_explanatory (34), inquisitive (30),
structured_analytic (14). The raw derivation — `mode_clusters.csv`,
`style_summary.json`, `style_scorecard.md` — stays in that repo; only the
conclusions are here.

**This is a description, not a specification.** It says how Adam writes on a
forum. It does not say how carrychain's artifacts should read, and in one place
the two genuinely disagree.

## Where it conflicts with this repo, and who wins

The profile is drawn from forum comments, which are idea-dense and
medium-to-long. [AGENTS.md](../../../AGENTS.md) asks for chat replies at a
10th–11th grade reading level: plain sentences, common words, short paragraphs.
Both cannot be satisfied at once.

**The repo rule wins on surface, the voice wins on reasoning.**

- Sentence length, paragraph length and reading level are carrychain's call.
  Shorten without apology.
- Explanation over slogan, context before the claim, support instead of naked
  assertion, structural punctuation, no hype and no lecturing — those are the
  voice, and they survive the shortening. They also happen to agree with
  [anti-slop.md](../anti-slop.md), which is why the two coexist at all.

If a rewrite makes prose shorter *and* removes a reason, it obeyed the wrong
one of these.
