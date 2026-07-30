# Versão — skill-COMMITTER

**Versão atual:** `0.4.0`

> Este arquivo é a **fonte da verdade** da versão do projeto. Qualquer lugar que
> precise exibir ou reportar a versão extrai o **primeiro número semver (`X.Y.Z`)**
> encontrado aqui. Mantenha a linha **"Versão atual"** sempre como a primeira
> ocorrência de um número de versão. Mesma mecânica dos projetos-irmãos (AUDITOR,
> SHVIA-WEB, SSHVTERM-DESKTOP).
>
> Ironia registrada: este repositório define a skill que commita pelos outros — e o
> `version.md` dele segue exatamente o contrato que a skill consome.

---

## 1. Convenção de Versionamento (`X.Y.Z`)

| Componente | Significado | Como sobe |
|---|---|---|
| **X** | Release estável — skill instalada e operando nos repos da casa | Manual |
| **Y** | Mudança estrutural — fase concluída, mudança de contrato (`.committer.yml`, pipeline), ADR aceito que muda a direção | Manual |
| **Z** | Incremento a cada entrega (ver gatilhos) | A cada entrega |

Enquanto `X` for `0`, contratos podem quebrar entre versões `0.Y`.

### Gatilhos de bump do `Z`

- Criar ou alterar documento em `docs/`, `SPEC.md` ou `prompts/` que **muda uma
  regra** (não vale corrigir redação).
- Alterar o pipeline, o esquema do `.committer.yml` ou o formato do relatório.
- Alterar o prompt do fallback.
- Alterar **política de segurança**: scan de segredo, allowlist, regras de push.
- Alterar `.claude/settings.json` (permissões, perfil de modelo).
- Adicionar ou mudar comportamento de script/hook, quando existirem.
- Adicionar ou alterar testes que definem comportamento esperado.

### Gatilhos de bump do `Y`

- Fase concluída (ver `.continue/escopo-projeto.md`).
- Quebra de compatibilidade no `.committer.yml` ou no estado.
- ADR novo com status **Aceito** que muda a direção.

> Correções de texto, typo e formatação **não** exigem bump.

---

## 2. Formato de Commit Obrigatório

```
X.Y.Z - Descrição curta em português
```

**Regras inegociáveis:**

1. A versão **sempre** vem deste `version.md` — bumpe **no mesmo commit** da mudança.
2. Mensagem em **português**, descritiva o suficiente para `git log --grep`.
3. **Proibido** Conventional Commits (`feat:`, `fix:`, `chore:`…) e mensagens vagas.
4. Um objetivo por commit; mudanças pequenas e atômicas.

O bump entra em **um único commit** por entrega (o primeiro). Commits adicionais da
mesma entrega repetem a versão sem novo bump — regra que, aliás, é o que permite ao
COMMITTER usar a versão atual no fallback sem inventar número (ADR-002).

---

## 3. Changelog

> Ordem decrescente (mais recente no topo).

### `0.3.1` — 2026-07-29 — Sweep de marcadores nos 24 repos da casa; o cron passa a chamar o run.sh

- **Marcadores instalados** em 24 repositórios (todos os nossos com `version.md`;
  forks de terceiro e o balde `000/` ficam fora por regra, não por esquecimento).
  Repos sem `version.md` **não** receberam marcador: sem ele não há formato da casa
  e o ciclo pararia em "fallback necessário" em todo disparo.
- **Gatilho deixa de carregar caminhos** (`SPEC.md` §3): a crontab chama
  `~/x/GIT/run.sh`, que varre a árvore e entrega ao ciclo só quem tem marcador.
  Antes a lista era fixa na linha do cron — a skill só rodava nos dois repos do
  piloto, e repo novo exigia editar a crontab.
- §1.1 registra a divisão: a **varredura** é do sweeper, a **elegibilidade**
  continua sendo do marcador.
- Doc de estado corrigida: a F4 ainda deve o **bloco PS** nos `CLAUDE.md`/
  `AGENTS.md` — enquanto ele não for, os agentes seguem commitando como antes.

### `0.4.0` — 2026-07-29 — F4: rollout na casa — 43 repos com marcador e o bloco PS nas docs

Bump de **`Y`**: fase F4 concluída. A skill deixa de ser piloto de 2 repos e passa a
valer para a casa inteira.

**Marcadores — 43 repos** (`~/x/GIT/run.sh --list` confirma)
- **40 ativos**: todos os nossos repos com clone local nos dois orgs.
- **3 desligados** com `enabled: false` e o motivo escrito no próprio arquivo:
  `ai-usagebar` e `BLUE3-LINUX` (forks) e `GITHUB-DESKTOP` (derivado do upstream do
  GitHub Desktop, 39k+ commits). Fluxo lá é PR, não commit direto — ADR-004/T-03.
- **Nossos forks em `000/`** (ai-memory, claude-desktop-debian, FRANK_KARAOKE,
  hermes-agent, mtzSpider, sinalrf, Vitals, ai-usagebar-samir, matomo-blue3) também
  receberam marcador desligado, mas **local-only** (via `.git/info/exclude`): o
  arquivo documenta a decisão nesta máquina sem entrar em PR para o upstream de
  terceiro. O `run.sh` já exclui `000/` inteiro na origem.
- **Terceiros puros** (litellm, headroom, 9router, CSL-Redes, speedtest, TDAH,
  github-visualize, docsys_blue3, upstream do ai-usagebar) não receberam nada.

**Bloco PS nas documentações — 42 arquivos**
- `## PS — Commits: a skill COMMITTER cuida disso` nos `CLAUDE.md`/`AGENTS.md` de
  todos os participantes com doc de agente.
- O condicional ficou **verificável**: o gatilho é a presença de `.committer.yml` na
  raiz — o mesmo arquivo que é o opt-in — e não uma referência vaga a "se a skill
  existir". Marcador ausente ou `enabled: false` → o próprio bloco manda voltar ao
  fluxo antigo.
- Dois `AGENTS.md` são **symlinks** para `CLAUDE.md` (BLUE3-INTRANET,
  SSHVTERM-WEB) — detectados, sem duplicação.

**AUDITOR (piloto próprio, decisão do Samir)**
- `.auditor/config.yml` + `.auditor/README.md` + `.claude/skills/auditor/` em
  **skill-AUDITOR e SHVIA-WEB**. Hook `PreToolUse` do gate registrado no
  `settings.json` dos dois **preservando os hooks existentes** (o SHVIA-WEB tem
  PostToolUse/Stop do impeccable). Smoke test nos dois sentidos: transparente fora
  de um ciclo, bloqueia dentro.
- Continua **sem executor headless** — o `run.sh` só lista quem optou.

**Limitação declarada**
- **16 participantes não têm `version.md`**: sem ele não há o formato da casa, e o
  ciclo reporta sem commitar. Adotar o versionamento em cada um é decisão do
  projeto, não da skill — o marcador diz isso no próprio comentário.

_Gatilhos:_ fase concluída (Y), mudança de alcance da skill, alteração de
documentação normativa em 42 arquivos.

---

### `0.3.0` — 2026-07-29 — F3: fallback com validador anti-injeção, três modos de auth e teto diário

Bump de **`Y`**: fase F3 concluída. O caso sem changelog (dominante no SHVIA-WEB,
cujo `version.md` é só-número) deixa de ficar parado.

**Código**
- `skill/committer/fallback.py` — orquestra o fallback: teto diário → prompt do
  produto (corpo de `prompts/committer-fallback.md`, sem o header humano) →
  invocação por modo → **validador mecânico** → mensagem ou motivo.
  - **Modos de auth (ADR-008):** `subscription` (default) = `claude -p --model
    sonnet --tools "" --strict-mcp-config` em **cwd sandbox vazio** — sem tools,
    sem MCP, sem o contexto do repo alvo; `api-key` e `shvia` = HTTP direto pela
    stdlib (`urllib`) para `$ANTHROPIC_BASE_URL/v1/messages` — sem tools por
    construção. Chave só do ambiente do serviço, nunca do marcador.
  - **Validador**: exatamente uma linha `X.Y.Z - descrição` com a **versão
    esperada** — qualquer outra versão é rejeitada, que é a defesa anti-injeção
    que não depende do modelo obedecer o prompt; descrição ≥10 chars, linha ≤140,
    sem Conventional Commits, sem segredo ecoado (`scan_text` na mensagem).
  - **Teto diário (P-04, fechada):** 24/dia global, `COMMITTER_FALLBACK_DAILY_CAP`
    ajusta, `0` = kill-switch; contador no `state.json` com poda de dias antigos.
    Estourou/indisponível/ABORT/rejeitado → stage desfeito, árvore intocada.
  - Test-hook `COMMITTER_FALLBACK_CMD` (payload JSON no stdin → linha no stdout),
    usado pela suíte e utilizável para gerador local; passa pelo mesmo validador.
- `committer_cycle.py` — integração: precondições (`fallback:` ≠ `off`,
  `version.md` legível — sem ele nem invoca), `--dry-run` anuncia sem invocar,
  trailer de fallback com `(fallback <modelo>)` + `Co-Authored-By: Claude Sonnet 5`.
- `prompts/committer-fallback.md` — entrada ganha `STAT` completo e a nota do
  validador; diff truncado em 60 KB com marcador.

**Validação ao vivo (modo subscription)**
- O Sonnet real gerou, num fixture sem changelog, `"2.88.6 - Cria app.py com
  atribuição da variável y"` — formato, versão e idioma certos, aprovada pelo
  validador e commitada. (Descoberto por acidente de suíte antes do guarda-corpo
  `COMMITTER_FALLBACK_CMD=false` entrar nos testes do ciclo — os testes nunca mais
  chamam modelo real.)

**Testes — 43, sem modelo real**
- `tests/test_fallback.py`: validador (aceita boa; rejeita versão inventada,
  multilinha, vazio, Conventional, curta, gigante, segredo ecoado), truncamento,
  header do prompt não vai ao modelo, teto com poda e kill-switch, e integração
  com fakes — incluindo **um que obedece a injeção plantada no diff** (pior caso)
  e morre na checagem de versão.
- Mutação: neutralizar a checagem de versão derruba 2 testes; scan da F1 segue
  derrubando 3.

**Limite declarado (SECURITY T-04)**
- A garantia mecânica cobre versão, formato, tamanho e segredo ecoado. **Não cobre
  semântica** — descrição enganosa com a versão certa passa; essa defesa é do
  prompt. O diff chega ao fallback já depois do scan de segredo do estágio 1.6.

_Gatilhos:_ fase concluída (Y), comportamento novo de script, política de
segurança nova em código (validador + teto), prompt do produto alterado.

---

### `0.2.0` — 2026-07-29 — F1: núcleo determinístico do ciclo, scan de segredo e piloto armado

Bump de **`Y`**: fase F1 concluída. Este commit foi feito **pelo próprio committer**
(dogfood) — o título desta entrada é a mensagem, e o trailer `Committed-By` está no
corpo.

**Código**
- `skill/committer/committer_cycle.py` — pipeline completo do SPEC §1 sem modelo:
  marcador fail-closed (chave desconhecida = nada feito), sanidade
  (merge/rebase/bisect/conflito/detached/branch_only), no-op silencioso, janela
  quieta por mtime, `git add -A`, scan de segredo com exclusão do arquivo (ADR-005),
  mensagem determinística via changelog do `version.md` staged, commit com trailer
  `Committed-By: committer/<versão>`, push da branch atual com ponte `gh` automática
  p/ HTTPS e 3-strikes sem force (ADR-006), estado + lock com stale em
  `~/.local/state/committer/` (P-01). `--dry-run` e `--quiet-min` para uso manual.
- `skill/committer/secret_scan.py` — padrões **vendorizados** do `redact.py` do
  AUDITOR (fonte da verdade dos regexes é lá), adaptados para detecção nas linhas
  **adicionadas** do diff staged — segredo antigo já commitado não bloqueia o
  arquivo para sempre.
- Extrator cobre os dois formatos da casa: entrada com título → determinístico;
  `version.md` só-número (SHVIA-WEB) → "fallback necessário", com versão detectada
  reportada, stage desfeito e árvore intocada. Sem changelog o committer **nunca
  inventa mensagem** (ADR-002).

**Achado do dogfood (e por que ele valida o desenho)**
- O primeiro `--dry-run` no próprio repo marcou `committer_cycle.py` como segredo:
  o padrão `assigned-secret` casava `tokens = out.split("\0")` — linha de parser.
  Falso positivo de classe que bloquearia o arquivo do produto para sempre.
- Correção **na fonte da verdade** (`redact.py` do skill-AUDITOR, com teste de
  regressão lá) e re-vendorizada aqui: valor sem `()` + lookahead de fronteira —
  expressão de código tem parêntese, segredo real (AWS/JWT/base64/hex) não. Só
  excluir da classe não bastava: o motor casava um **prefixo** do valor.

**Testes** — 21, nos dois sentidos, sem dependência externa
- `tests/test_cycle.py`: opt-in invisível, kill-switch, marcador inválido
  fail-closed, no-op mudo, janela quieta, merge/detached/branch_only, mensagem do
  topo do changelog, duas entradas → topo, bump-sem-título não commita, segredo
  plantado fica fora e o resto entra, caminho sensível, só-segredo = nada, push
  falho mantém commit e conta strike, push off, lock concorrente, dry-run.
- Verificado por **mutação**: neutralizar o scan derruba 3 testes.

**Decisões**
- **ADR-008** — auth da invocação de modelo (pergunta do Samir sobre API key +
  "outro user agent"): `subscription` | `api-key` | `shvia` (gateway da casa);
  chave nunca no marcador; implementação na F3.
- **P-01** e **P-05** fechadas (estado XDG; piloto = skill-COMMITTER + SHVIA-WEB);
  **P-03** meio fechada (cron = crontab do Linux — rotinas agendadas do Claude Code
  são cloud e não enxergam `~/x`).

**Piloto**
- Marcadores `.committer.yml` nos dois repos (`branch_only: master`).
- Linha de crontab pronta no `SPEC.md` §3 (instalação é do Samir; rodar 1× manual
  antes). Enquanto F3 não existe, o SHVIA-WEB fica em modo vigia: reporta, trava
  segredo, não commita.

_Gatilhos:_ fase concluída (Y), comportamento novo de script, política de segurança
exercida em código, ADR aceito.

---

### `0.1.0` — 2026-07-29 — Baseline: pipeline, ADRs e modelo de ameaça

Nasce o repositório com a proposta fechada em conversa de 29/07 — decisões
registradas, sem implementação. Padrão da casa aplicado (mesmo baseline do AUDITOR).

**Documentação**
- `README.md` — objetivo, pipeline resumido, limitações declaradas e o bloco PS para
  os `CLAUDE.md` dos repos participantes.
- `SPEC.md` — pipeline normativo em 10 estágios, esquema do `.committer.yml`, estado
  local e relatório.
- `SECURITY.md` — modelo de ameaça (T-01 a T-07) com os controles exigidos.
- `docs/decisoes.md` — ADR-001 a ADR-007: escopo e repo próprio; mensagem
  changelog-first sem bump; gatilho híbrido Stop+cron com janela quieta; opt-in por
  marcador `.committer.yml`; segredo → exclui arquivo e commita o resto; push da
  branch atual sem force; agrupamento por assunto adiado para v2.
- `prompts/committer-fallback.md` — prompt do fallback Sonnet (conteúdo do diff é
  dado, nunca instrução; vago é proibido; ABORT quando não der para descrever).
- `CLAUDE.md` + `AGENTS.md` (espelhados), `.continue/` (escopo F0–F4 + estado),
  `.claude/` (perfil opus[1m] + permissões), `.gitignore`.

_Gatilhos:_ baseline de documentação/versionamento + política de segurança +
configuração do agente.
