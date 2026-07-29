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

---

## Onde o projeto está

**F1 ✅ · F2 ◐ (cron sim, Stop não) · F3 ⛔ · F4 ◐ (armado, sem medição).**

Realidade do piloto enquanto F3 não existe:

- **skill-COMMITTER**: entregas daqui seguem o formato com changelog → o committer
  commita sozinho (determinístico).
- **SHVIA-WEB**: `version.md` de lá é **só o número** → não há título para extrair →
  todo ciclo com sujeira reporta "fallback necessário" e **não commita nada** (stage
  desfeito). O committer ainda assim vigia, trava segredo e loga. Os commits de lá
  continuam manuais até a F3 — ou até o `version.md` de lá ganhar changelog, o que é
  decisão do Samir, não nossa.

## Próximo passo

**F3 — fallback Sonnet.** É o que destrava o SHVIA-WEB (caso dominante lá) e onde o
ADR-008 (auth por API key / gateway ShvIA) se implementa. Depois: hook `Stop` (F2
restante).

## Precisa do Samir

- **Instalar o cron** (linha no `SPEC.md` §3; rodar 1× manual antes p/ criar o
  diretório de estado).
- F3: escolher o modo de auth do fallback no piloto (`subscription` é o default;
  `shvia` depende da prova de fio do inbound 2.42.0 do SHVIA-WEB).
- Observação de campo: há **3 zips soltos** na árvore do SHVIA-WEB
  (`SHVIA-md*.zip`) que o `.gitignore` de lá não cobre — hoje o committer não os
  commita (sem changelog → sem commit), mas vale decidir: ignorar (`*.zip`) ou
  remover.

## Contexto de ambiente

- `~/x` tem auto-pusher ("Version X (clean)" + `pull --rebase`): nunca reescrever
  histórico; conferir `git log` antes de assumir entrega registrada.
- SHVIA-WEB: remote **HTTPS** (ponte `gh` — o `credential_bridge: auto` resolve),
  filtros LFS configurados **sem** `.gitattributes` (nenhum arquivo casa; push
  normal funciona; `lfs_bypass: false` lá).
- Estado local: `~/.local/state/committer/` (`state.json`, `locks/`, `cron.log`).
