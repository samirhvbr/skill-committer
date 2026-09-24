# Claude Code profile — skill-COMMITTER

This project's `.claude/` follows the Blue3/samirhvbr house pattern: **effort and
permissions posture**. It does **not** choose a model — see below. The core is
planned in Python 3 with no external dependency; the allow-list stays lean until
F1 exists.

| File | Role |
|---------|-------|
| `settings.json` | **Active** profile (versioned). `effortLevel: xhigh`, `defaultMode: plan`, security deny-list. No model key. |
| `README.md` | This file. |

## The model is not set here

**The model is the user's choice, made per session with `/model`, and a subagent
inherits it** (repodocs ADR-027). This repository pins nothing: `settings.json`
carries no `model` or `fallbackModel`, and its `env` carries no
`ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_*_MODEL` or `CLAUDE_CODE_SUBAGENT_MODEL`.
There are no stand-by profile files to copy over `settings.json` — `/model` does
that job. The context window is whatever the chosen model provides; the
repository neither guarantees nor overrides it.

## Rules worth remembering

- **Effort `max` goes per session** (`/effort max`); the JSON field accepts up to
  `xhigh`.
- `crontab`/`systemctl` are on **ask** on purpose: the product installs a
  scheduling trigger (F2) — nobody installs persistence on the machine without
  Samir seeing it. Same posture as its sibling AUDITOR.
- `git filter-branch`/`filter-repo` denied: the `~/x` auto-pusher runs
  `pull --rebase` and undoes a rewrite — rewriting here only breaks the repo.
- **Important distinction:** the product (the skill) commits and pushes in the
  **target** repos when it is operating; *this* repository follows the normal
  manual house flow until then.

## Product model vs development model

- Developing this repo: whichever model the user picked with `/model`; this
  `.claude/` pins none.
- **Product fallback: `sonnet`** — defined in `SPEC.md` §4 and in the
  `.committer.yml` marker (`fallback: sonnet`); it is not configured by this
  `.claude/`.
