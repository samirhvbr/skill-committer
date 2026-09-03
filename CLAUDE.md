# skill-COMMITTER — Instruções para Claude Code

> **Leia também:** [README.md](README.md) (o produto) ·
> [SECURITY.md](SECURITY.md) (**leitura obrigatória** — modelo de ameaça) ·
> [SPEC.md](SPEC.md) (pipeline normativo e `.committer.yml`) ·
> [docs/decisoes.md](docs/decisoes.md) (ADR-001 a ADR-011 + pendências) ·
> [prompts/committer-fallback.md](prompts/committer-fallback.md) (prompt do fallback) ·
> [version.md](version.md) (versão + formato de commit).
>
> `CLAUDE.md` e `AGENTS.md` são **espelhados** abaixo do H1 — editar os dois.

---

## 🔄 Antes de começar: `git pull`

**SEMPRE** verifique atualizações remotas antes de escrever ou alterar qualquer
coisa neste repositório:

```bash
git pull          # já está pré-autorizado (allow)
```

---

## O que é este repo

Skill **committer** (comando `/committer`): subagente que tira dos agentes
principais o compromisso de commitar. Em ciclo (hook `Stop` + cron 30 min), lê a
árvore suja dos repos com marcador `.committer.yml`, monta a mensagem
`X.Y.Z - descrição` a partir do `version.md` (determinístico; Sonnet só como
fallback), commita e pusha a branch atual.

Irmão do **AUDITOR** (`~/x/SKILLS/skill-AUDITOR`): mesmo padrão de documentação, mesma política
de scheduler, padrões de segredo vendorizados do `redact.py` de lá.

---

## ⚠️ Estado do projeto: F1 entregue, piloto armado

O que **existe e roda**: `skill/committer/committer_cycle.py` (pipeline completo,
`--dry-run`), `secret_scan.py` (vendorizado do skill-AUDITOR), `fallback.py`
(F3: modos `subscription`/`api-key`/`shvia`, validador mecânico, teto diário) e
**61 testes** verificados por mutação (scan, validador, backoff, teto e changelog).

**Participantes (29/07, F4 concluída):** **43 repos** com marcador — 40 ativos e 3
desligados (`ai-usagebar`, `BLUE3-LINUX`, `GITHUB-DESKTOP`: forks/derivados de
upstream, fluxo de PR). O balde `000/` fica fora na origem, pelo `run.sh`. O cron não
lista caminho nenhum: chama `~/x/GIT/run.sh`, que **descobre** quem tem
`.committer.yml` (`SPEC.md` §3). O **bloco PS** está nos `CLAUDE.md`/`AGENTS.md` de
todos os participantes com doc de agente — é ele que faz os agentes pararem de
commitar.

**Custo (revisado na 0.5.0):** o caminho determinístico custa **zero tokens** e é o
normal; o fallback Sonnet é exceção. Se um repo cai sempre no fallback, o defeito é
falta de entrada de changelog — não da skill. Os 16 participantes que não tinham
`version.md` ganharam um em 30/07, e repos que commitam sem modelo foram de 1 → 16.

⚠️ **Ainda em fallback:** os repos cujo `version.md` é só-número (SHVIA-WEB, AREA81,
SSHVTERM-*, …). O caminho barato para eles é criar um **`CHANGELOG.md`** — a skill
procura a entrada lá também (ADR-009), sem tocar no `version.md` que a produção lê.

O que **não existe**: hook `Stop` (F2 restante), agrupamento por assunto (v2).

```bash
python3 -m unittest discover -s tests -v          # 61 testes, sem modelo real
python3 skill/committer/committer_cycle.py <repo> --dry-run --quiet-min 0
```

Envs do fallback: `COMMITTER_FALLBACK_AUTH` (`subscription`|`api-key`|`shvia`),
`COMMITTER_FALLBACK_DAILY_CAP` (24 global) e `COMMITTER_FALLBACK_REPO_CAP` (6 por repo),
`COMMITTER_FALLBACK_CMD` (test-hook). Chave **nunca** no marcador.

Ao trabalhar aqui:

- **Não descreva como pronto** o que é spec. `SPEC.md` marca com ⛔ o que falta.
- **Não feche pendência dentro de um how-to** — decisão nova vira ADR
  em [docs/decisoes.md](docs/decisoes.md).
- **Não confunda "escrito" com "implementado"** — regra herdada do AUDITOR: controle
  só conta com teste que **falha quando o controle é desligado**.

---

## Padrão de Commits (obrigatório)

Formato: `X.Y.Z - Descrição curta em português`. A versão **sempre** vem de
[`version.md`](version.md), bumpada **no mesmo commit**. Critério resumido: **Z** =
entrega que muda regra/spec/prompt/segurança; **Y** = fase concluída, quebra de
contrato, ADR que muda direção; **X** = skill estável operando. **Proibido**
`feat:`/`fix:`/`chore:` e mensagens vagas.

(Sim: este repo define a skill que commita pelos outros e, enquanto ela não opera,
os commits daqui seguem o fluxo manual da casa.)

---

## Regras do produto (não relitigar sem ADR)

1. Repo próprio, v1 = **commit-checkpoint**, um commit por repo por ciclo (ADR-001).
2. Mensagem **changelog-first**; fallback Sonnet só sem entrada nova; **nunca bumpa
   versão**; vago é proibido → `ABORT` (ADR-002).
3. Gatilho híbrido: `Stop` primário + cron 30 min + janela quieta 5 min + lock
   (ADR-003).
4. Opt-in **por marcador** `.committer.yml` no repo participante; marcador só
   restringe, nunca amplia (ADR-004).
5. Segredo no staged → **ABORTA a árvore inteira**, nomeando arquivo e regra (ADR-012,
   supera o ADR-005). `.env.example` e afins não contam como caminho sensível — senão o
   abort viraria paralisia.
6. Push da **branch atual**, nunca force/amend/rebase; falha de push não é fatal e
   nunca escala (ADR-006).
7. Agrupamento por assunto = **v2**, com modelo (ADR-007).
8. Changelog **desacoplado** do `version.md`: entrada vale em `CHANGELOG.md`,
   `docs/VERSION.md` ou `version.md` (ADR-009).
9. **Backoff por árvore inalterada** + teto por repo; só falha do diff memoriza,
   transitória não (ADR-010).
10. **Estado de outra skill tem dono, e não é este ciclo:** `skip_paths` no marcador
    tira o caminho do stage, da janela quieta e da conta de "árvore suja" (ADR-011).

E o que o COMMITTER **nunca** faz: bumpar versão, editar conteúdo de arquivo,
resolver conflito/merge, trocar de branch, mensagem vaga, commit em repo sem
marcador.

---

## Regras de escrita

- **Idioma do repositório: PT-BR.** Artefatos que a skill produz (mensagens de
  commit) também são em português — é o padrão da casa.
- Documentação durável → `docs/`. Notas de trabalho → `.continue/`. Contrato
  normativo → `SPEC.md`. Prompt do produto → `prompts/` (nunca na raiz com nome que
  ferramenta carrega sozinha — lição do ADR-007 do AUDITOR).
- Sem link para arquivo inexistente; futuro se descreve em texto.
- Distinguir **fato observado**, **inferência** e **recomendação**.

---

## Como o Claude Code deve operar aqui

- **Planeje antes de editar** (`defaultMode: plan`).
- Mudanças pequenas e atômicas; ao concluir entrega, **atualize `version.md`** e
  `.continue/estado-atual.md`.
- Decisão pendente bloqueia? Faça o que não depende dela e pergunte — não escolha
  por conta própria.
- Fixtures de teste **nunca** usam formato real de chave de provedor — montar por
  concatenação (push protection barra, e com razão).

---

## Referências rápidas

- Versão e commits: [version.md](version.md)
- Modelo de ameaça: [SECURITY.md](SECURITY.md)
- Pipeline e config: [SPEC.md](SPEC.md)
- Decisões: [docs/decisoes.md](docs/decisoes.md)
- Escopo e fases: [.continue/escopo-projeto.md](.continue/escopo-projeto.md)
- Estado atual: [.continue/estado-atual.md](.continue/estado-atual.md)
- Perfil do agente: [.claude/README.md](.claude/README.md)
- Irmão: `~/x/SKILLS/skill-AUDITOR` (padrões de segredo, política de scheduler)
- Remoto: `github.com/samirhvbr/skill-COMMITTER` (privado) · branch `master`

---

<!-- COMMIT-RULE:repodocs -->

## Commits — you commit, and nothing is delivered until you have

> Marked echo. The single source is **[samirhvbr/repodocs](https://github.com/samirhvbr/repodocs/blob/master/docs/versioning.md#who-commits-and-when)**
> — change it there, not here. This block is regenerated.

**Committing is your job.** Not "leave the tree ready and something downstream
packages it" — you run `git commit`, and `git push`, as the last step of the work
you were asked to do. The COMMITTER skill that used to commit on an agent's
behalf is `enabled: false` in every repository of this fleet since 03/09/2026;
what is left of it is a kill-switch, not a scheduler. **If you do not commit,
nobody does.**

**Do not report a task as finished before the commit exists.** "Done",
"delivered", "concluded" mean the work is in `git log` — never that it is sitting
uncommitted where only this session can see it. The commit is the last step *of
the task*, not a follow-up for someone else. If you are about to write
"finished", commit first, then write it.

**Every commit obeys the versioning rules**, with no exception:

- Subject `X.Y.Z - short description in English (US)`, the version taken from
  `version.md` and **bumped in the same commit**.
- The `CHANGELOG.md` entry is written first — its `## X.Y.Z - description`
  heading *is* the subject.
- No Conventional Commits prefix (`feat:`, `fix:`, `chore:`) and no vague
  subject ("update", "ajuste", "wip", "changes", "several improvements").

**One subject per commit.** The subject has to describe the whole commit
honestly. The moment your description needs an "and" to be true, it is two
commits.

**Split a large delivery into blocks.** A complex task is committed as a series
of commits grouped by subject, each small enough to be described in one line and
read on its own. They may share a version — bump `version.md` in the first and
repeat the number in the rest; two commits carrying one version is expected, not
a mistake. **Splitting is the default** for anything non-trivial, because the
history is the documentation of *how* the work was done, and one commit touching
six unrelated subjects documents none of them.

**The standard you are keeping:** someone reading `git log` alone — a year from
now, without the conversation that produced the work — can say what happened,
when, why, and at which version. If your commit would fail that test, it is too
big or its subject is too vague, and both are fixed the same way.

<!-- /COMMIT-RULE -->

---

<!-- RELEASES-RULE:repodocs -->

## Releases — the `version.md` on GitHub is what the Releases show

> Marked echo. The single source is **[samirhvbr/repodocs](https://github.com/samirhvbr/repodocs/blob/master/docs/versioning.md)**
> — change it there, not here. This block is regenerated.

**The `version.md` of the default branch, on GitHub, is what the GitHub Releases
must show.** The local checkout does not enter the calculation: it can be behind,
ahead or mid-work, and none of that is published — GitHub cannot tag a commit it
does not have.

**The bump and the Release are one act.** A commit that bumps `version.md` is not
finished until that version has a tag, a published Release, and the **`Latest`
badge on it** — the same push, not "later". A badge sitting on an older release
tells whoever looks that the project is at a version it is not.

- `.github/workflows/release.yml` does it on any push that touches `version.md`.
- `./tools/release.sh` does it by hand. It is **idempotent and self-healing**:
  it publishes whatever is missing and moves a drifted badge back. Running it is
  always safe, so it is both the check and the fix.

A PR publishes nothing while it is a PR. The moment it merges, the push moves
`version.md` on the default branch and the Release becomes that version.

Tag and Release title are the **bare version — no `v` prefix**.

## Language — English (US), everywhere in the repository

**Everything that lives in this repository, or in GitHub's interface around it,
is written in English (US)**: documents, **commit messages**, pull request titles
and bodies, issues, code comments, changelog entries, release notes.

Commit format: `X.Y.Z - short description in English`. The version comes from
`version.md` and is bumped in the same commit. Conventional Commits prefixes
(`feat:`, `fix:`, `chore:`) and vague one-word messages are forbidden.

**Exactly one carve-out:** end-user-facing strings — UI text, transactional
email, product copy. That is product i18n for a Brazilian audience, not
repository content.

History is not rewritten: Portuguese messages already in the log stay as they
are.

<!-- /RELEASES-RULE -->
