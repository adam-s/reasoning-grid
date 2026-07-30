# `.claude/` Anthropic conventions — quick reference

Distilled from Anthropic's official Claude Code docs and
`github.com/anthropics/skills`. **Authoritative source** is the official docs;
this file only exists so we don't reinvent formats. Re-research if formats
change.

- Skills: https://code.claude.com/docs/en/skills
- Hooks: https://code.claude.com/docs/en/hooks
- Sub-agents: https://code.claude.com/docs/en/sub-agents
- Settings: https://code.claude.com/docs/en/settings
- Settings JSON Schema: https://json.schemastore.org/claude-code-settings.json
- Examples: https://github.com/anthropics/skills

---

## Skills — `SKILL.md` in a named folder

Required frontmatter: `name`, `description`. Everything else is optional.

```markdown
---
name: my-skill
description: What it does + when to use it. Description is keyword-matched for auto-discovery — front-load the trigger phrases.
allowed-tools: Bash(uv run *), Read, Write     # pre-approve specific tools/commands
disable-model-invocation: false                # true = user-invoked only (no auto-triggering)
user-invocable: true                           # false = Claude-only, hidden from slash menu
model: sonnet                                  # override session model for this skill's work
effort: high                                   # low | medium | high | xhigh | max
context: fork                                  # 'fork' = run in subagent, isolated context
agent: Explore                                 # which subagent type if context: fork
paths: src/**/*.py                             # auto-load skill when files matching glob are touched
argument-hint: "[label]"                       # CLI autocomplete hint
---

# Skill body — the instructions Claude follows

Keep the main SKILL.md focused (target ~500 lines max). For long supporting
material, bundle alongside and reference:

- `reference/<topic>.md` — detailed docs, lazy-loaded
- `scripts/<helper>.sh` — executable utilities
- `templates/<file>.template` — scaffolding inputs
```

**Folder layout** (this repo puts skills under `.agents/skills/`, see Drift
check below):

```
.agents/skills/my-skill/
├── SKILL.md        # required
├── reference/      # optional
├── scripts/        # optional
└── templates/      # optional
```

**Two patterns:**

1. **Skill-as-prompt-template** — the SKILL.md body is a template the agent
   fills in and hands to the `Agent` tool. No scripts.
2. **Skill-as-procedure** — the body documents a sequence the agent walks, with
   the gates and stops made explicit.

---

## Hooks — configured in `settings.json`, NOT separate files

Hooks live in `.claude/settings.json` under the `hooks` key. A `.agents/hooks/`
directory holds the *referenced* shell scripts, not config. They live under
`.agents/` rather than `.claude/` because a shell script is portable; only the
wiring that names it is Claude-Code-specific.

```jsonc
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.agents/hooks/guard-raw-writes.sh",
            "timeout": 10,
            "statusMessage": "Checking raw-data immutability"
          }
        ]
      }
    ]
  }
}
```

**Hook types:** `command` (shell), `http` (POST), `prompt` (Claude evaluates),
`agent` (spawn subagent).

**Event types:** `PreToolUse`, `PostToolUse`, `SessionStart`, `CwdChanged`,
`FileChanged`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `WorktreeCreate`.

**Hooks are how an automated behavior becomes deterministic.** Prose in a skill
cannot make the harness run something every time; a hook can.

---

## Sub-agents — `.agents/agents/<name>.md` (`.claude/agents` symlinks to it)

```markdown
---
name: reviewer-agent
description: Reviews a run's harness and manifest. Use before trusting a result.
tools: Read, Bash, Grep, Glob                # whitelist
disallowedTools: Write, Edit                 # blacklist (read-only enforcement)
model: sonnet
maxTurns: 5
isolation: worktree                          # run in a fresh git worktree
permissionMode: default
---

You are a senior reviewer. Return specific, actionable findings.
```

**Custom agent vs inline `Agent` call:** a custom agent is for *recurring*
delegation the maintainer wants visible in the agent picker. One-off delegation
uses an inline `Agent` call.

---

## Rules — `.agents/rules/<name>.md` with `paths:` frontmatter

The `paths:` mechanism is Claude-Code-specific: rules load *conditionally*, by
glob, when matching files are touched. The procedures themselves are not
Claude-specific, so they live under `.agents/` with `.claude/rules` symlinked
for auto-discovery. Another agent reads them as plain path-scoped documents.

```markdown
---
description: One line shown when the rule loads
paths:
  - "harness/**"
---
```

A rule with no `paths:` is ambient — it loads every session, so it competes with
AGENTS.md for the same budget. Prefer scoping. A single flat AGENTS.md is fine
until the tree has genuinely separate procedures per area.

**Division of labor, so the files don't drift into each other:**

| File | Holds |
|---|---|
| `AGENTS.md` | Generalized principles and policy. No specific fact, path, constant, or recipe. |
| `.agents/rules/*.md` | Path-scoped *procedures* — the steps for work in one part of the tree. |
| Code comments | Anything guarding a specific implementation. |
| Script docblocks | Bounds, usage, and the exact commands. Enforced, not described. |

---

## Settings — `.claude/settings.json` (committed) and `settings.local.json` (gitignored)

```jsonc
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": ["Bash(uv run *)"],
    "deny":  ["Read(./.env*)"]
  },
  "env":     { "DEBUG_LOGGING": "true" },
  "hooks":   { /* see Hooks section */ },
  "model":   "opus",
  "effort":  "high"
}
```

**Scope precedence (higher wins):**

1. `~/.claude/settings.json` (user, all projects)
2. `.claude/settings.json` (project, committed)
3. `.claude/settings.local.json` (project, gitignored — local overrides)
4. Org/managed settings (above all)

---

## Drift check — what's in this repo

**Every agent-shared artifact lives in `.agents/` (canonical) so it works across
coding agents.** Root `AGENTS.md` holds the project instructions and root
`CLAUDE.md` imports it via `@AGENTS.md`. `.claude/` keeps only what is genuinely
Claude-Code-specific, plus directory symlinks so auto-discovery still resolves.
Hook scripts need no symlink: `settings.json` names them by path.

The test that a change respects this: a coding agent that has never heard of
`.claude/` can read `AGENTS.md`, follow it into `.agents/`, and find everything.

Rows are claims. Re-verify them against the tree before relying on them.

| Artifact | Status | Notes |
|---|---|---|
| `AGENTS.md` (root) | ✓ aligned | Canonical project instructions, cross-agent |
| `CLAUDE.md` (root) | ✓ aligned | Thin `@AGENTS.md` import + entry-point note |
| `.claude/CLAUDE.md` | ✓ absent | Deliberate. A memory file loads by path, so a symlink is a second full copy in context rather than a pointer; the root `CLAUDE.md` already imports the canon. |
| `.claude/skills` → `.agents/skills` | ✓ aligned | Symlink; skills directory is empty until a real recurring procedure earns one |
| `.agents/reference/anti-slop.md` | ✓ aligned | Byte-identical across sibling repos — do not fork it locally |
| `.agents/reference/anthropic-conventions.md` | ✓ aligned | This file |
| `.agents/rules/` | not used | Single flat AGENTS.md is sufficient at this size |
| `.agents/agents/` | not used | Inline `Agent` calls cover one-off delegation |
| `.agents/hooks/` | not used | Candidate: a `PreToolUse` guard on raw-data writes once the layout settles |
| `.claude/settings.json` | not used | Candidate: an allow-list for the run scripts once their flags settle |
| `.agents/assets/` | not used | Sibling repos play operator chimes; not adopted here |

## When to update this file

- A skill, hook, agent, rule, or settings field doesn't behave the way this doc
  says
- Anthropic ships a new artifact type or deprecates one
- A pattern here diverges from the canonical shape and needs recording as a
  deliberate exception

Everything here rots silently, so re-read it when the tree changes. If in doubt,
re-fetch the official docs URLs at the top.
