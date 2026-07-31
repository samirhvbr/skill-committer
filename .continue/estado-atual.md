# Estado atual — skill-COMMITTER

- **2026-07-29 — `0.1.0` (F0):** nasce o repo com a proposta fechada — ADR-001 a
  ADR-007, SPEC, SECURITY, prompt do fallback. Detalhe em `git log` e `version.md`.

- **2026-07-29 — `0.2.0` (F1 + piloto armado):**
  - **Núcleo determinístico entregue**: `skill/committer/committer_cycle.py` +
    `secret_scan.py` (vendorizado do AUDITOR). Pipeline completo sem modelo,
    `--dry-run` e `--quiet-min` para uso manual.
  - **20 testes** nos dois sentidos, verificados por **mutação** (neutralizar o scan
    de segredo derruba 3 testes).
  - **ADR-008** — auth da invocação de modelo (`subscription`/`api-key`/`shvia`),
    da pergunta do Samir sobre API key + "outro user agent". Implementação na F3;
    chave nunca no marcador.
  - **P-01** fechada (estado em `~/.local/state/committer/`), **P-05** fechada
    (piloto = este repo + SHVIA-WEB, decisão do Samir), **P-03** meio fechada
    (cron = **crontab do Linux**; hook `Stop` pendente).
  - **Piloto armado**: marcador `.committer.yml` nos dois repos
    (`branch_only: master`); linha de crontab pronta no `SPEC.md` §3 — instalação é
    do Samir. Este próprio commit `0.2.0` foi feito **pelo committer** (dogfood: o
    título veio da entrada de changelog; trailer `Committed-By` no corpo).

- **2026-07-29 — `0.3.0` (F3):** fallback entregue — `fallback.py` com três modos
  de auth (ADR-008), validador mecânico anti-injeção (versão esperada
  obrigatória), teto diário (P-04 fechada: 24/dia, kill-switch), test-hook
  `COMMITTER_FALLBACK_CMD`. Modo `subscription` **validado ao vivo** (Sonnet real
  gerou mensagem válida num fixture). 43 testes; mutação no validador derruba 2.

---

## Onde o projeto está

**F1 ✅ · F2 ◐ (cron sim, Stop não) · F3 ✅ · F4 ◐ (armado, sem medição).**

Piloto com F3:

- **skill-COMMITTER**: entregas com changelog → determinístico (zero tokens);
  fallback ativo como rede.
- **SHVIA-WEB**: o fallback destrava o caso de lá (`version.md` só-número), MAS o
  marcador está com **`fallback: off` até o Samir decidir os zips soltos** — com
  fallback ligado, o primeiro ciclo commitaria os 4 zips (`SHVIA-md*.zip`,
  `shvia.zip`) que o `.gitignore` de lá não cobre. O committer não julga lixo por
  desenho; a decisão é humana.

- **2026-07-30 — `0.4.0` (F4): rollout na casa.** 43 repos com marcador (40 ativos),
  bloco PS em 42 `CLAUDE.md`/`AGENTS.md`, AUDITOR no piloto de 2 repos. Quatro
  desligados com motivo escrito: `ai-usagebar`, `BLUE3-LINUX`, `GITHUB-DESKTOP`
  (forks/derivados) e **`EOP`** — descoberto no rollout que ele é governado por
  ruleset do GitHub (PR + review + code owner + `docs-lint`), então push direto é
  recusado por regra e commit autônomo não pertence ao fluxo de lá.

- **2026-07-30 — `0.5.0`: revisão pós-rollout.** A F4 mostrou que o desenho não
  estava se cumprindo: **18 de 24 participantes** caíam sempre no fallback (o
  `version.md` deles é só-número), e um bug fazia repo travado **reinvocar o modelo
  a cada ciclo sobre o mesmo diff**, esgotando o teto de todos. ADR-009 (changelog
  desacoplado do `version.md`) + ADR-010 (backoff e teto por repo). Criados os 16
  `version.md` que faltavam. Repos que commitam **sem modelo: 1 → 16**.

---

## Próximo passo

**F2 restante — hook `Stop`** (P-03): disparo pós-turno, para o commit sair ao fim
do trabalho em vez de esperar até 55 min.

Depois: **medir a F4 em operação** — proporção determinístico × fallback, zero
segredo publicado, zero commit em janela ativa.

## Trabalho barato que sobrou (alto retorno)

**Criar `CHANGELOG.md` nos repos que ainda caem no fallback** — SHVIA-WEB, AREA81,
BLUE3-INTRANET, BLUE3-SITE-FRONT, ONLINE, GIT, LINUX, SAMIRHV, SHVIA-BENCH,
SHVIA-CODE, SHVIA-DESKTOP, SHVIA-MOBILE, SSHVTERM-*. Cada um vira determinístico
(commit sem custo, mensagem melhor) **sem tocar no `version.md`** que a produção lê
— é exatamente para isso que o ADR-009 existe. É criar um arquivo por repo.

## Achados do rollout (valem registro)

- **O prompt precisa declarar os limites que o validador aplica.** As duas primeiras
  rejeições em repo real (SHVIA-WEB 170 chars, SHVIA-DESKTOP 155, contra teto de
  140) eram mensagens **boas, só compridas** — e o prompt nunca dizia o limite ao
  modelo. Teto subiu para 160, o prompt passou a declará-lo, e um teste agora
  **falha se os dois divergirem de novo**. Divergência silenciosa entre prompt e
  validador queima teto e trava repo sem explicar.
- **Mudar o validador invalida o backoff.** Depois de corrigir o limite, as falhas
  memorizadas não valiam mais e precisaram ser limpas do estado à mão. Se validador
  ou prompt mudarem de novo, limpar `fallback_failed_tree` faz parte da entrega.

- **EOP** tem ruleset no GitHub que recusa push direto na master. O marcador dele já
  estava versionado com `enabled: true` (sweep anterior) — o override local está por
  `git update-index --skip-worktree`, que faz a árvore ficar limpa e o ciclo
  respeitar o desligamento. **A correção durável é um PR** mudando o marcador no
  remoto; enquanto não for, uma máquina nova voltaria a ter EOP ativo.
- Marcadores de fork são **local-only** (`.git/info/exclude`): um `.committer.yml`
  versionado num fork apareceria no diff de PRs futuros para o upstream de terceiro.
- Dois `AGENTS.md` da casa são **symlinks** para `CLAUDE.md` (BLUE3-INTRANET,
  SSHVTERM-WEB) — quem editar em massa precisa saber, ou duplica conteúdo.

## Precisa do Samir

- **Instalar o cron** (linha no `SPEC.md` §3; rodar 1× manual antes — já feito
  nesta máquina, o diretório de estado existe).
- **Zips do SHVIA-WEB**: ignorar (`*.zip` no `.gitignore`), remover, ou commitar —
  destrava o `fallback: on` lá.
- Modo de auth do fallback no cron: `subscription` (default) funciona já;
  `api-key`/`shvia` = exportar envs na crontab (`shvia` depende da prova de fio do
  inbound 2.42.0).

## Contexto de ambiente

- `~/x` tem auto-pusher ("Version X (clean)" + `pull --rebase`): nunca reescrever
  histórico; conferir `git log` antes de assumir entrega registrada.
- SHVIA-WEB: remote **HTTPS** (ponte `gh` — o `credential_bridge: auto` resolve),
  filtros LFS configurados **sem** `.gitattributes` (nenhum arquivo casa; push
  normal funciona; `lfs_bypass: false` lá).
- Estado local: `~/.local/state/committer/` (`state.json`, `locks/`, `cron.log`).
