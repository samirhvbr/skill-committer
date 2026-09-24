# Technical documentation — skill-COMMITTER

Index of `docs/`. **Durable** documentation lives here; working notes, scope and
state in [`.continue/`](../.continue/); the normative contract in [`SPEC.md`](../SPEC.md);
the product prompt in [`prompts/`](../prompts/).

> The project is at **F0**: the proposal is closed, with no implementation. Anything
> marked ⛔ in `SPEC.md` is a known gap, not an oversight.

## In this folder

| File | What it is |
|---|---|
| [decisoes.md](decisoes.md) | **ADRs.** ADR-001 to ADR-007 (every decision from the 29/07 conversation) plus open questions P-01 to P-05. A new decision goes here. |

## Outside this folder

| File | What it is |
|---|---|
| [../README.md](../README.md) | The product: purpose, pipeline summary, declared limitations, PS block for the house repos. |
| [../SPEC.md](../SPEC.md) | **Normative.** The 10-stage pipeline, `.committer.yml`, triggers, state. |
| [../SECURITY.md](../SECURITY.md) | Threat model (T-01 to T-07). **Required reading.** |
| [../prompts/committer-fallback.md](../prompts/committer-fallback.md) | The Sonnet fallback prompt — a product artifact. |
| [../version.md](../version.md) | Source of truth for the version, bump triggers, commit format. |
| [../CLAUDE.md](../CLAUDE.md) / [../AGENTS.md](../AGENTS.md) | Rules for whoever develops this repo. Mirrored — edit both. |
| [../.continue/escopo-projeto.md](../.continue/escopo-projeto.md) | Phases F0–F4 plus v2, each with its done criterion. |
| [../.continue/estado-atual.md](../.continue/estado-atual.md) | Where the project stands and what needs Samir. |
| [../.claude/README.md](../.claude/README.md) | Effort and permissions posture. The model is not set here — it is the user's choice via `/model`, and subagents inherit it (repodocs ADR-027). |

## Where to start

- **Understand the product** → `../README.md`, then `decisoes.md`.
- **Going to implement (F1)** → `../SPEC.md` + `../SECURITY.md`, and the `redact.py`
  of its sibling AUDITOR (`~/x/SKILLS/skill-AUDITOR/skill/auditor/lib/redact.py`) to vendor.
- **Going to touch the fallback prompt** → T-04 of `../SECURITY.md` first.

## Conventions

- Language: existing documentation stays PT-BR; **new text, every edit, and commit
  messages — including the ones the skill produces — are English (US)** since
  03/09/2026 (repodocs ADR-014; see *Regras de escrita* in `../CLAUDE.md` and
  `../prompts/committer-fallback.md`).
- A new document here enters **this index** in the same commit.
- No link to a file that does not exist.
- Observed fact ≠ inference ≠ recommendation.
