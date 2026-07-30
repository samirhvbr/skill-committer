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

## F3 — Fallback Sonnet ✅ (0.3.0)

Entregue em 29/07: `skill/committer/fallback.py` + integração no ciclo.

- ✅ Modo `subscription` via `claude -p --tools "" --strict-mcp-config` em sandbox
  (**validado ao vivo** — o Sonnet real gerou mensagem válida que passou no
  validador e virou commit num fixture); modos `api-key`/`shvia` por HTTP stdlib.
- ✅ Validador mecânico: versão esperada obrigatória (anti-injeção que não depende
  do modelo), uma linha, formato, tamanho, sem Conventional Commits, sem segredo.
- ✅ Teto diário (P-04): 24/dia, `COMMITTER_FALLBACK_DAILY_CAP`, `0` = kill-switch.
- ✅ Fixture de injeção: fake que **obedece** a injeção morre no validador.
- ✅ 43 testes; mutação no validador de versão derruba 2.

**Pronto quando — atingido:** diff sem changelog vira mensagem específica ou
`ABORT`/rejeição reportados; injeção plantada não dirige a mensagem.

## F4 — Piloto e rollout ✅ (0.4.0)

- ✅ Repos do piloto (P-05, decisão do Samir): **skill-COMMITTER + SHVIA-WEB**,
  marcadores instalados, `branch_only: master` nos dois (conservador).
- ✅ **Sweep do bloco PS** feito, com o condicional verificável (presença do
  marcador na raiz, não "se a skill existir no ambiente").
- ⛔ **Medir em operação**: % de ciclos determinísticos vs fallback, zero segredo
  publicado, zero commit em janela ativa. Só o tempo de cron dá esse número.
- ⛔ **16 participantes sem `version.md`** — reportam e não commitam. Adotar o
  versionamento em cada um é decisão do projeto.

**Pronto quando:** os repos da casa operam com o COMMITTER e os agentes principais
pararam de commitar por padrão.

## v2 (fora de escopo até ADR próprio — ADR-007)

Agrupamento por assunto: modelo particiona a árvore em commits lógicos, cada um com
sua mensagem. É onde o custo de modelo passa a valer.
