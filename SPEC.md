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

Sujo **só** sob `skip_paths` (§2) conta como limpo — e o no-op continua mudo. Um
`.dashproject/pending` que o hook da outra skill reescreve a cada commit renderia
uma linha no `cron.log` a cada disparo, para sempre (ADR-011).

### 1.4 Janela quieta
Algum arquivo da árvore modificado (mtime) nos últimos `quiet_window_min` (default
**5**) → **adia** para o próximo disparo. Protege sessão trabalhando agora — inclusive
sessões paralelas de outros agentes no mesmo repo.

Arquivo sob `skip_paths` não segura a janela: `pending` tem mtime de agora depois de
**todo** commit, e um repo com aquele hook instalado ficaria adiando para sempre.

### 1.5 Stage
`git add -A`. O `.gitignore` do repo é a primeira linha de defesa (`.env`, `tmp/`…);
o COMMITTER não julga lixo — se lixo entra, o defeito é do `.gitignore` do repo, e o
achado é do AUDITOR.

Com `skip_paths`, o comando vira `git add -A -- ':(exclude)<path>'…` e o que já
estava no índice sob esses caminhos é des-stageado. São dois pontos porque cobrem
coisas diferentes: o pathspec impede a **entrada** — inclusive a deleção de origem de
um **rename** dentro do caminho, que a limpeza do índice não alcança; a limpeza cobre
o índice **pré-existente**, tipicamente a skill dona tendo feito `git add` e morrido
antes do commit (ADR-011).

### 1.6 Scan de segredo
Padrões vendorizados do `redact.py` do AUDITOR (AWS, tokens de provedor, JWT, PEM,
credencial em URL, `VAR_SECRET=…`) rodando sobre `git diff --cached`. Encontrou →
🔴 **ABORTA a árvore inteira** (ADR-012, supera o ADR-005): nada é commitado, o stage é
desfeito, a árvore fica como estava, e o relatório nomeia **arquivo e regra**.

**Por que não "commita o resto", que era o ADR-005:** commit parcial por decisão de scanner
publica **meia entrega** sem nada acusar. Medido no SHVIA-WEB 2.92.0 — 49 arquivos dentro, 7
fora, entre eles a migration cujos consumidores entraram; HEAD não-deployável por 11 min.

⚠️ **`.env.example` (e `.sample`/`.template`/`.dist`) NÃO conta como caminho sensível** —
é arquivo de convenção, versionado. Sem essa exceção o abort viraria paralisia: encostar no
template travaria todo commit do repo. A regra de **conteúdo** continua valendo neles.

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
   (truncado em 60 KB se preciso) e escreve **uma linha** honesta em **inglês (US)** —
   ADR-014 do repodocs: tudo que vive no repositório é inglês, mensagem de commit
   incluída.
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
  Push bem-sucedido encadeia a §1.11 (tag e Release).
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

### 1.11 Tag e Release
- Roda **só depois de um push que deu certo**. Motivo: uma Release aponta para
  um commit que precisa existir **no remoto** — tag sobre commit local que nunca
  subiu é promessa que o GitHub não consegue cumprir.
- Versão = **primeiro semver do `version.md`**. A skill **não decide** versão
  nenhuma: copia o número que o agente já escreveu (o ADR-002 continua inteiro).
- Tag e título = a versão **pura**, sem prefixo `v`.
- Caminho preferido: **`tools/release.sh --current` do próprio repo** — a
  implementação única da casa, que tira as notas da seção do `CHANGELOG.md`.
  Sem o script, cai num `gh release create --generate-notes`.
- `release: false` no marcador desliga.
- **Falha nunca é fatal.** O `.github/workflows/release.yml` do repo é a segunda
  rede, e os dois guardam pela mesma pergunta — *"a tag já existe?"* —, então
  quem chegar primeiro ganha e o outro vira no-op. Reporta e segue.

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
skip_paths: null         # CSV de caminhos que o ciclo não stagea (ADR-011)
release: true            # false = não cria tag/Release após o push (ADR-013)
```

`skip_paths` é lista em **CSV numa linha** — `skip_paths: .dashproject/, .loop/` —
porque o marcador é um subset YAML plano; lista com `- ` exigiria outro parser e o
arquivo continua YAML válido assim. Casa por **segmento**: `.loop` não pula
`.loopback/`. Caminho absoluto ou com `..` = **marcador inválido** (pathspec para
fora do repo derrubaria o `add` e o repo pararia de ser commitado em silêncio).

Serve para caminho que **outra skill escreve e commita**: `.dashproject/` (o
auditor DASHPROJECT fecha o próprio snapshot com `chore(dashproject)`), `.loop/`.
Sem isso, o hook `post-commit` daquela skill reescreve o estado dela depois de cada
commit, o ciclo empacota esse estado, o hook reescreve de novo — loop perpétuo, e
cada volta queimando uma invocação de fallback (ADR-011).

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
  nenhuma sem ADR. *(Criar a tag/Release da versão que o agente já escreveu
  **não** é bump — ver §1.11 e ADR-013.)*
- Validar build/testes antes de commitar (o commit é checkpoint; validação é do
  agente principal).
