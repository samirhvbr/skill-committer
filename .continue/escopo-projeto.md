# Escopo e fases — skill-COMMITTER

> Fases com critério de pronto. Decisões fechadas em
> [`docs/decisoes.md`](../docs/decisoes.md) (ADR-001 a ADR-007); pendências P-01 a
> P-05 na tabela de lá. Alterar fase = atualizar aqui + bumpar `version.md`.

## F0 — Baseline de documentação ✅ (0.1.0)

Proposta fechada com o Samir (29/07), ADRs registrados, pipeline normativo,
modelo de ameaça, prompt do fallback. Sem implementação.

## F1 — Núcleo determinístico

**Objetivo:** o pipeline inteiro **sem modelo** — a maioria dos ciclos reais.

- Script `committer-cycle` (Python 3, zero dependências): elegibilidade → sanidade →
  sujo? → janela quieta → stage → **scan de segredo** (padrões vendorizados do
  `redact.py` do AUDITOR) → mensagem determinística via `version.md` → commit com
  trailer → push conforme marcador.
- Parser do `.committer.yml` + validador (P-02) e extrator do título do changelog.
- Estado local + lock (P-01).
- **Testes nos dois sentidos** (regra do AUDITOR): fixture-repo com segredo plantado,
  entrega com changelog, entrega sem changelog, estados abortivos, janela quieta.
  Verificar por mutação.

**Pronto quando:** num fixture-repo, uma entrega com changelog vira commit+push com a
mensagem do topo, sem nenhuma invocação de modelo; o segredo plantado fica de fora e
é reportado; e cada teste falha com seu controle desligado.

## F2 — Gatilhos

**Objetivo:** disparar sozinho, do jeito decidido no ADR-003.

- Hook `Stop` (mecânica exata = P-03: hook dispara o script ou agenda?).
- Cron/rotina de 30 min como rede.
- Lock funcionando entre os dois e contra o AUDITOR.

**Pronto quando:** turno encerrado num repo piloto → commit aparece sem intervenção;
cron pega uma árvore suja deixada por sessão morta; dois disparos simultâneos → um
desiste em silêncio.

## F3 — Fallback Sonnet

**Objetivo:** o caso sem changelog deixa de ficar parado.

- Invocação headless com `model: sonnet`, sem tools, prompt de
  [`prompts/committer-fallback.md`](../prompts/committer-fallback.md).
- Validador mecânico da saída (formato `X.Y.Z - …` ou `ABORT`; uma linha).
- Teto diário de invocações (P-04) + fixture com injeção plantada no diff (T-04).

**Pronto quando:** diff sem changelog vira mensagem específica ou `ABORT` reportado;
saída fora do formato é rejeitada; injeção plantada não dirige a mensagem.

## F4 — Piloto e rollout

**Objetivo:** operar de verdade, depois espalhar.

- Piloto em 2 repos (P-05; sugestão: este + um de movimento real).
- Critérios de aprovação medidos no piloto: % de ciclos determinísticos, zero
  segredo publicado, zero commit em janela ativa.
- **Sweep do bloco PS** nos `CLAUDE.md`/`AGENTS.md` dos repos da casa + marcador
  `.committer.yml` em cada um — só depois do piloto aprovado.

**Pronto quando:** os repos da casa operam com o COMMITTER e os agentes principais
pararam de commitar por padrão.

## v2 (fora de escopo até ADR próprio — ADR-007)

Agrupamento por assunto: modelo particiona a árvore em commits lógicos, cada um com
sua mensagem. É onde o custo de modelo passa a valer.
