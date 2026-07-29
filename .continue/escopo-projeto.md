# Escopo e fases — skill-COMMITTER

> Fases com critério de pronto. Decisões fechadas em
> [`docs/decisoes.md`](../docs/decisoes.md) (ADR-001 a ADR-007); pendências P-01 a
> P-05 na tabela de lá. Alterar fase = atualizar aqui + bumpar `version.md`.

## F0 — Baseline de documentação ✅ (0.1.0)

Proposta fechada com o Samir (29/07), ADRs registrados, pipeline normativo,
modelo de ameaça, prompt do fallback. Sem implementação.

## F1 — Núcleo determinístico ✅ (0.2.0)

Entregue em 29/07: `skill/committer/committer_cycle.py` (pipeline completo sem
modelo, `--dry-run`, `--quiet-min`) + `secret_scan.py` (vendorizado do AUDITOR) +
parser fail-closed do `.committer.yml` + estado/lock em
`~/.local/state/committer/` + **20 testes** nos dois sentidos, verificados por
mutação (neutralizar o scan derruba 3).

**Critério de pronto atingido via dogfood:** o próprio repo skill-COMMITTER e o
SHVIA-WEB entraram no piloto; ver `estado-atual.md`.

Extrator cobre os dois formatos da casa: entrada com título (`### \`X.Y.Z\` — data —
Título`) → determinístico; `version.md` só-número (formato SHVIA-WEB) → fallback
necessário, reportado com a versão detectada, **stage desfeito e árvore intocada**.

## F2 — Gatilhos ◐ (cron entregue; Stop pendente)

- ✅ **Cron 30 min**: linha de crontab pronta no `SPEC.md` §3 — instalação é do
  Samir (decisão: crontab do Linux; rotinas agendadas do Claude Code são cloud).
- ✅ Lock por repo com stale — testado (disparo concorrente desiste em silêncio).
- ⛔ Hook `Stop` (P-03): mecânica de disparo pós-turno.
- ⛔ Ordenação explícita contra o AUDITOR quando o ciclo dele existir.

**Pronto quando:** turno encerrado num repo piloto → commit aparece sem intervenção;
cron pega árvore suja de sessão morta.

## F3 — Fallback Sonnet

**Objetivo:** o caso sem changelog deixa de ficar parado — no SHVIA-WEB
(`version.md` só-número) é o caso **dominante**.

- Invocação headless com `model: sonnet`, sem tools, prompt de
  [`prompts/committer-fallback.md`](../prompts/committer-fallback.md).
- **Auth configurável (ADR-008):** `subscription` | `api-key` | `shvia` — chave
  sempre no ambiente do serviço, nunca no marcador.
- Validador mecânico da saída (formato `X.Y.Z - …` ou `ABORT`; uma linha).
- Teto diário de invocações (P-04) + fixture com injeção plantada no diff (T-04).

**Pronto quando:** diff sem changelog vira mensagem específica ou `ABORT` reportado;
saída fora do formato é rejeitada; injeção plantada não dirige a mensagem.

## F4 — Piloto e rollout ◐ (piloto armado)

- ✅ Repos do piloto (P-05, decisão do Samir): **skill-COMMITTER + SHVIA-WEB**,
  marcadores instalados, `branch_only: master` nos dois (conservador).
- ⛔ Medir critérios de aprovação: % de ciclos determinísticos, zero segredo
  publicado, zero commit em janela ativa, zero commit-lixo (os 3 zips soltos do
  SHVIA-WEB são o caso de teste natural — hoje ficam de fora porque sem changelog
  não há commit).
- ⛔ **Sweep do bloco PS** nos `CLAUDE.md`/`AGENTS.md` + marcador nos demais repos
  da casa — só depois do piloto aprovado.

**Pronto quando:** os repos da casa operam com o COMMITTER e os agentes principais
pararam de commitar por padrão.

## v2 (fora de escopo até ADR próprio — ADR-007)

Agrupamento por assunto: modelo particiona a árvore em commits lógicos, cada um com
sua mensagem. É onde o custo de modelo passa a valer.
