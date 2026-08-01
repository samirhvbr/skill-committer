# SPEC.md — Pipeline e configuração do COMMITTER

> **Normativo.** O que está fechado vem sem marca; lacuna restante é marcada com ⛔ e
> o que a bloqueia. Decisões em [docs/decisoes.md](docs/decisoes.md); ameaças e
> controles em [SECURITY.md](SECURITY.md).
>
> Nomes: repositório `skill-COMMITTER` · skill `committer` · comando `/committer`.

---

## 1. Pipeline por repositório (ordem obrigatória)

A cada disparo, para cada repo participante:

### 1.1 Elegibilidade
Só entra no ciclo o repo com `.committer.yml` na raiz (ADR-004). Sem marcador → o
repo **não existe** para o COMMITTER. Nunca varrer `~/x` incondicionalmente.

Quem descobre os candidatos é o **`~/x/GIT/run.sh`** (§3): ele varre a árvore, mas
entrega ao ciclo **apenas** os repos com marcador, e nunca os do balde de terceiros
(`000/`) — nem que um marcador apareça lá por engano num clone. A varredura é do
sweeper; a elegibilidade continua sendo do marcador.

### 1.2 Sanidade
Qualquer um destes → **no-op com aviso**, nunca tentativa de resolver:
- merge, rebase, cherry-pick ou bisect em andamento (`.git/MERGE_HEAD`,
  `.git/rebase-merge/`, `.git/rebase-apply/`, `.git/BISECT_LOG`);
- conflito não resolvido no índice;
- detached HEAD;
- `enabled: false` no marcador (kill-switch local sem apagar o arquivo).

### 1.3 Sujo?
`git status --porcelain` vazio → **no-op silencioso**: sem relatório, sem estado além
de `last_checked`. (Mesma regra de quiescência do AUDITOR.)

### 1.4 Janela quieta
Algum arquivo da árvore modificado (mtime) nos últimos `quiet_window_min` (default
**5**) → **adia** para o próximo disparo. Protege sessão trabalhando agora — inclusive
sessões paralelas de outros agentes no mesmo repo.

### 1.5 Stage
`git add -A`. O `.gitignore` do repo é a primeira linha de defesa (`.env`, `tmp/`…);
o COMMITTER não julga lixo — se lixo entra, o defeito é do `.gitignore` do repo, e o
achado é do AUDITOR.

### 1.6 Scan de segredo
Padrões vendorizados do `redact.py` do AUDITOR (AWS, tokens de provedor, JWT, PEM,
credencial em URL, `VAR_SECRET=…`) rodando sobre `git diff --cached`. Encontrou →
**des-stagea o(s) arquivo(s) ofensor(es), commita o resto, reporta visível**
(ADR-005). O COMMITTER nunca edita conteúdo — bloqueia o arquivo inteiro.

### 1.7 Mensagem
1. **Determinístico (caminho feliz, zero tokens):** um dos **arquivos de changelog**
   está entre os staged **e** o diff dele adiciona entrada nova no topo →
   mensagem = `X.Y.Z - <título da entrada>`. O próprio diff denuncia que o agente
   principal preparou o handoff.

   Arquivos procurados, em ordem: **`CHANGELOG.md`** → **`docs/VERSION.md`** →
   **`version.md`**. O marcador pode fixar outro com `changelog_file:`.

   > **Por que a entrada não precisa estar no `version.md`** (ADR-009): a maioria dos
   > repos da casa lê o `version.md` em **runtime**, e vários com
   > `trim(file_get_contents())` — que devolve o arquivo inteiro. Transformar aquele
   > arquivo em markdown quebraria a versão exibida em produção. Um `CHANGELOG.md`
   > novo não tem esse acoplamento: o repo vira determinístico sem tocar em código.
   > A **versão** continua saindo do `version.md`; o changelog só guarda o título.
2. **Fallback (Sonnet):** senão → o subagente recebe `VERSION` (a atual do
   `version.md`, repetida — sancionado, ADR-002), `STAT` completo e `DIFF`
   (truncado em 60 KB se preciso) e escreve **uma linha** honesta em português.
   Prompt em [prompts/committer-fallback.md](prompts/committer-fallback.md). Se não
   conseguir descrever com especificidade, retorna `ABORT` e o repo fica para o
   próximo ciclo com aviso — **mensagem vaga é proibida**.

   Toda saída passa pelo **validador mecânico** (`fallback.py::validate_output`):
   exatamente uma linha, `X.Y.Z - descrição` com a **versão esperada** (qualquer
   outra é rejeitada — é a defesa anti-injeção que não depende do modelo), descrição
   ≥10 chars, linha ≤140, sem Conventional Commits, sem segredo ecoado
   (`scan_text`). Rejeitado/`ABORT`/indisponível → stage desfeito, árvore intocada,
   nunca degrada para mensagem inventada.

   Precondições: `fallback:` ≠ `off` no marcador **e** o repo tem `version.md`
   legível (sem ele não há formato da casa — nem se invoca o modelo). O commit de
   fallback ganha trailer `(fallback <modelo>)` +
   `Co-Authored-By: Claude Sonnet 5`.

O COMMITTER **nunca bumpa versão**. Quando o diff claramente merecia bump (mudança de
comportamento sem entrada de changelog), anota a pendência no relatório.

### 1.75 Trava de versão reutilizada
Vale para os DOIS caminhos (determinístico e fallback): se o assunto começa com
`X.Y.Z - ` e o histórico da branch já contém commit com o mesmo prefixo de
versão, o commit é **recusado** (stage desfeito, árvore intocada) e o relatório
aponta o sha conflitante. A cura é sempre a mesma: bumpar o `version.md` (com a
entrada de changelog) para versão inédita.

Motivação (01/08/2026): sessões paralelas + fallback produziram dois `0.5.4` no
SHVIA-MOBILE e dois `1.1.11` no SHVIA-DESKTOP — versão repetida quebra o
`git log --grep` como índice e mente sobre o que cada versão contém.

### 1.8 Commit
- Autoria: a configuração git do ambiente (como qualquer commit local).
- Trailer obrigatório identificando a origem, para auditoria via `git log --grep`:
  - caminho determinístico: `Committed-By: committer/<versão da skill>`
  - fallback: `Committed-By: committer/<versão> (fallback sonnet)` +
    `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`

### 1.9 Push
- **Branch atual**, e somente ela. Nunca `--force`, nunca amend, nunca rebase.
- `push: false` no marcador → só commita (repos onde o push é sensível).
- Remote HTTPS → ponte `gh` (`-c credential.helper='!gh auth git-credential'`).
- `lfs_bypass: true` → variação de push que a casa já usa em SHVIA-WEB/matomo.
- Push falhou (rede, auth, non-fast-forward) → **commit fica local**, reporta,
  retenta no próximo ciclo. Falha de push não é fatal e **nunca** escala para force.
  Non-fast-forward persistente (3 ciclos) → para de tentar e marca para humano.

### 1.10 Relatório e estado
- Uma linha por repo tocado: repo, branch, commit, mensagem, nº de arquivos,
  bloqueios de segredo, resultado do push.
- Estado **local, fora dos repos participantes e não versionado** — diferente do
  AUDITOR (lá o estado é checkpoint de auditoria compartilhável; aqui o git já é a
  fonte durável — o último commit é consultável). Guarda apenas `last_checked`,
  `last_commit`, `push_fails` por repo e locks.
- Caminho (P-01, fechada): **`$XDG_STATE_HOME/committer/`** —
  `~/.local/state/committer/` com `state.json`, `locks/` e `cron.log`. Lock por repo
  com `O_EXCL`; stale (>30 min) é quebrado e retomado.

---

## 2. `.committer.yml` (o marcador de opt-in)

A **presença** do arquivo é o opt-in. Todas as chaves têm default:

```yaml
enabled: true            # false = kill-switch local sem apagar o marcador
push: true               # false = só commita, não pusha
quiet_window_min: 5      # janela quieta
branch_only: null        # ex.: master — se setado, só commita nessa branch
credential_bridge: auto  # auto = ponte gh só quando o remote é http(s) | gh | none
lfs_bypass: false        # true onde os filtros LFS existem sem git-lfs (caso matomo)
fallback: sonnet         # modelo do fallback; "off" = só caminho determinístico
changelog_file: null     # null = tenta CHANGELOG.md → docs/VERSION.md → version.md
```

Chave desconhecida ou tipo errado = **marcador inválido = nada feito** (fail-closed:
um typo em `enabled` não pode virar silêncio).

> Nota de campo (29/07): no SHVIA-WEB os filtros LFS estão configurados mas não há
> `.gitattributes` — nenhum arquivo casa com o filtro, push normal funciona e o
> marcador de lá vai com `lfs_bypass: false`. A chave existe para o caso matomo.

Regra herdada do AUDITOR (ADR-009 de lá): o marcador só pode **restringir** o
comportamento, nunca ampliar — não existe chave que libere force, outra branch ou
bump.

⛔ Esquema JSON formal na F1, junto com o validador.

---

## 3. Gatilhos (ADR-003)

| Gatilho | Papel |
|---|---|
| Hook `Stop` do agente principal | **Primário** — fim de turno é árvore em ponto de descanso; dispara o pipeline do repo da sessão. ⛔ Mecânica na F2 (P-03) |
| Cron **30 min** | Rede de segurança — pega sessões mortas sem `Stop` e trabalho manual. **Decidido: crontab do Linux** (rotinas agendadas do Claude Code rodam na nuvem, não enxergam `~/x`) |
| Janela quieta 5 min | Guarda transversal dos dois |

Linha de crontab — **na crontab do usuário `samir`** (`crontab -e` sem sudo), nunca
na do root: os repos, o `gh auth`, a chave SSH e o login do Claude (modo
`subscription`) são do usuário, e o estado em `~/.local/state/committer/` sairia com
dono errado.

```cron
*/30 * * * * PATH=/home/samir/.local/bin:/usr/bin:/bin /home/samir/x/GIT/run.sh >> /home/samir/.local/state/committer/cron.log 2>&1
```

O cron chama o **`run.sh`** (repo `GIT`, o mesmo lugar do `git_pull.sh`), não o ciclo
direto. O ciclo recebe repositórios por argumento, então a linha antiga carregava a
lista fixa do piloto — **a skill só rodava onde o cron apontava**, e repo novo exigia
editar a crontab. O `run.sh` descobre os participantes a cada disparo pelo marcador
`.committer.yml` (e pula o balde de terceiros `000/` sempre). Entrar na varredura
passa a ser criar o marcador; a crontab não se toca mais.

(`PATH` explícito porque o PATH do cron é mínimo: a ponte de credencial invoca
`gh` — `/usr/bin` — e o fallback `subscription` invoca `claude` —
`/home/samir/.local/bin`, um symlink por versão. Sem esse primeiro diretório o
fallback falharia **só no cron**, nunca no teste manual — o modo de falha mais caro
de diagnosticar que esta linha tem.)

Lock por repo (arquivo em estado local): dois disparos simultâneos (Stop + cron) →
o segundo desiste em silêncio. O mesmo lock ordena COMMITTER × AUDITOR — nunca os
dois ciclos no mesmo repo ao mesmo tempo.

---

## 4. Modelo

- Caminho determinístico: **nenhum modelo**.
- Fallback: `sonnet` (aliases `sonnet`/`haiku`/`opus` ou id `claude-…` completo),
  entrada = `VERSION`+`STAT`+`DIFF`, saída = uma linha ou `ABORT`. **Sem tools, sem
  MCP** — no modo `subscription`, garantido por `--tools "" --strict-mcp-config` e
  cwd sandbox vazio (o contexto do repo alvo não carrega); nos modos HTTP, por
  construção.
- **Auth do fallback (ADR-008)** — env `COMMITTER_FALLBACK_AUTH`:
  - `subscription` (default) — CLI `claude -p` com o login local. Validado ao vivo
    em 29/07.
  - `api-key` — HTTP direto (stdlib) com `ANTHROPIC_API_KEY` do ambiente.
  - `shvia` — idem, com `ANTHROPIC_BASE_URL` → gateway ShvIA + chave `shvia_usr_…`
    (auditoria/custo no painel; depende da prova de fio do inbound 2.42.0).
  - **Chave nunca no `.committer.yml`** — o marcador é versionado no repo alvo;
    credencial vem do ambiente do serviço.
- **Tetos diários (P-04, fechada):** **24/dia global**
  (`COMMITTER_FALLBACK_DAILY_CAP`) **e 6/dia por repo**
  (`COMMITTER_FALLBACK_REPO_CAP`); `0` em qualquer um = kill-switch. Contadores no
  `state.json`. O teto por repo existe porque o global sozinho tem **starvation**:
  um repo movimentado consumiria a cota de todos (ADR-010).
- **Backoff por árvore inalterada (ADR-010):** falha em que o modelo **viu o diff**
  (`ABORT`, saída rejeitada) grava o hash do diff no estado e **não reinvoca até a
  árvore mudar** — sem isso, ~26 tentativas/dia sobre o mesmo diff esgotavam o teto.
  Falha **transitória** (teto, rede, CLI ausente, auth) **não** gera backoff: seria
  bloqueio permanente por problema passageiro. Sucesso limpa o registro.
- **Test-hook/extensão:** env `COMMITTER_FALLBACK_CMD` = comando que lê o payload
  JSON no stdin e imprime a linha — usado pela suíte (fakes, inclusive um que
  obedece injeção) e serve para plugar gerador local. Passa pelo **mesmo**
  validador.

---

## 5. Fora de escopo da v1 (não relitigar sem ADR)

- Agrupar a árvore em múltiplos commits por assunto → **v2** (ADR-007).
- Bump de versão, resolução de conflito, force push, amend — **nunca**, em versão
  nenhuma sem ADR.
- Validar build/testes antes de commitar (o commit é checkpoint; validação é do
  agente principal).
