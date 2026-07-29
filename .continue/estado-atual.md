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

## Próximo passo

**F2 restante — hook `Stop`** (P-03): disparo pós-turno. Depois F4: medir o piloto
e fazer o sweep do PS + marcadores nos repos da casa.

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
