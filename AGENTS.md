# skill-COMMITTER — Guia do Agente (AGENTS.md)

> **Leia também:** [README.md](README.md) (o produto) ·
> [SECURITY.md](SECURITY.md) (**leitura obrigatória** — modelo de ameaça) ·
> [SPEC.md](SPEC.md) (pipeline normativo e `.committer.yml`) ·
> [docs/decisoes.md](docs/decisoes.md) (ADR-001 a ADR-007 + pendências) ·
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
**50 testes** verificados por mutação (scan, validador, backoff, teto e changelog).

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
python3 -m unittest discover -s tests -v          # 50 testes, sem modelo real
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
5. Segredo no staged → **exclui o arquivo, commita o resto, reporta** (ADR-005).
6. Push da **branch atual**, nunca force/amend/rebase; falha de push não é fatal e
   nunca escala (ADR-006).
7. Agrupamento por assunto = **v2**, com modelo (ADR-007).
8. Changelog **desacoplado** do `version.md`: entrada vale em `CHANGELOG.md`,
   `docs/VERSION.md` ou `version.md` (ADR-009).
9. **Backoff por árvore inalterada** + teto por repo; só falha do diff memoriza,
   transitória não (ADR-010).

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

## PS — Commits: a skill COMMITTER cuida disso

**Existe `.committer.yml` na raiz deste repositório** — é o opt-in da skill
**COMMITTER**, que roda em ciclo (cron, via `~/x/GIT/run.sh`). Enquanto esse arquivo
existir com `enabled: true`, **commitar e pushar não é trabalho seu**.

**O que muda para você:**

- **Não commite nem pushe por padrão.** Conclua a entrega bumpando o `version.md`
  **com a entrada de changelog** e deixe a árvore pronta. É dali que a mensagem do
  commit sai — o changelog virou o artefato de handoff entre você e a skill.
- A skill monta `X.Y.Z - descrição`, commita e pusha a branch atual sozinha. Ela
  **nunca bumpa versão** (isso continua sendo julgamento seu) e nunca inventa
  mensagem: sem entrada de changelog ela cai num fallback Sonnet, e sem conseguir
  descrever com honestidade ela aborta e espera.

**Você ainda commita quando:**

- o Samir pedir explicitamente;
- a tarefa exigir o SHA na hora (deploy, abrir PR, referência cruzada);
- o `.committer.yml` sumir ou estiver `enabled: false` — aí vale o fluxo antigo,
  você bumpa, commita e pusha.

**Por que isso existe:** tirar de um modelo caro (Opus/Fable) o trabalho mecânico de
empacotar commit, que um Sonnet — ou, na maioria das vezes, nenhum modelo — resolve.
Economiza token e devolve tempo de desenvolvimento.
