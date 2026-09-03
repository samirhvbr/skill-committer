# skill-COMMITTER — Decisões (ADRs)

Formato ADR. **Não relitigar direção já decidida dentro de um how-to** — linkar o
ADR. Decisão nova entra aqui, com data e status, no mesmo commit da mudança.

> Todas as decisões abaixo foram fechadas com o Samir na conversa de 2026-07-29.

---

## ADR-001 — Nasce o COMMITTER: subagente de commits em repo próprio

- **Data:** 2026-07-29 · **Status:** Aceito
- **Contexto:** o fluxo da casa manda o agente que produz também commitar. Isso gasta
  tokens de modelo caro (Opus/Fable) em tarefa mecânica, interrompe o desenvolvimento
  e, na prática, gera commits fora do padrão (colisões de versão, mensagens de sweep
  sem versão).
- **Decisão:**
  1. Skill própria que roda **em ciclo**, lê o que ficou sem commit nos repos
     participantes, monta a mensagem no padrão `X.Y.Z - descrição`, commita e pusha.
  2. **Repositório separado** (`skill-COMMITTER`), com o mesmo padrão de documentação
     do AUDITOR — decisão do Samir; a alternativa (segunda skill dentro do AUDITOR)
     foi descartada. Custo aceito: os padrões de segredo do `redact.py` vão
     **vendorizados** (copiados), não compartilhados.
  3. Nomes: repo `skill-COMMITTER` (grafia com 2 T confirmada) · skill `committer` ·
     comando `/committer`.
  4. v1 é **commit-checkpoint**: um commit por repo por ciclo. A degradação de "um
     objetivo por commit" quando há entregas misturadas é aceita e declarada.
- **Objetivo declarado:** economizar tokens dos agentes caros e devolver tempo de
  desenvolvimento — o commit deixa de ser compromisso de quem produz.

---

## ADR-002 — Mensagem changelog-first; o COMMITTER nunca bumpa versão

- **Data:** 2026-07-29 · **Status:** Aceito
- **Contexto:** o contrato da casa já produz a mensagem pronta: quem produz bumpa o
  `version.md` e escreve a entrada de changelog. E decidir se algo é bump de `Z` ou
  `Y` exige entender a mudança — julgamento de quem produziu, não de quem empacota.
- **Decisão:**
  1. **Caminho feliz (determinístico, zero tokens):** `version.md` staged com entrada
     nova no topo → mensagem = `X.Y.Z - título da entrada`. Sem modelo.
  2. **Fallback (Sonnet):** sem entrada nova → o subagente resume o diff em uma linha
     honesta; **versão = a atual, repetida** — sancionado pelo padrão da casa
     ("commits adicionais da mesma entrega repetem a versão"), confirmado pelo Samir:
     não há problema em commits com a mesma versão, desde que o conteúdo seja outro.
  3. O COMMITTER **nunca bumpa**. Bump que parecia devido → anota no relatório.
  4. **Mensagem vaga é proibida.** Fallback sem especificidade honesta → `ABORT`, o
     repo espera o próximo ciclo, com aviso.
- **Consequência:** o fallback existir é sinal de handoff malfeito — o incentivo
  aponta para o hábito certo (changelog em dia), e o custo de modelo tende a zero.

---

## ADR-003 — Gatilho híbrido: hook Stop primário, cron 30 min como rede, janela quieta 5 min

- **Data:** 2026-07-29 · **Status:** Aceito
- **Contexto:** timer puro dispara no meio do trabalho — arquivo pela metade, estado
  quebrado. O momento perfeito de commit é "o agente terminou o turno".
- **Decisão:**
  1. **Hook `Stop`** do agente principal como disparo primário — fim de turno é
     árvore em ponto de descanso por definição.
  2. **Cron de 30 min** como rede de segurança, para sessões mortas sem `Stop` e
     trabalho manual.
  3. **Janela quieta de 5 min** (mtime) como guarda transversal — protege contra
     sessões paralelas no mesmo repo.
  4. Lock por repo: disparos concorrentes desistem em silêncio; o mesmo lock ordena
     COMMITTER × AUDITOR.
- **Nota:** responde na prática a P-11 do AUDITOR ("relógio, atividade ou os dois"):
  os dois, com papéis diferentes.

---

## ADR-004 — Opt-in por marcador `.committer.yml` no repositório participante

- **Data:** 2026-07-29 · **Status:** Aceito (decidido pelo Samir entre três opções)
- **Contexto:** `~/x` mistura repos da casa (commit direto na master é o fluxo) com
  forks de terceiros (fluxo de PR — commit autônomo lá é inaceitável). A allowlist
  não pode depender de memória.
- **Decisão:** a **presença** de `.committer.yml` na raiz do repo é o opt-in. Sem
  marcador, o repo não existe para o COMMITTER.
  - Fork de terceiro nunca terá o marcador — exclusão **por construção**.
  - A config viaja com o repo (clone novo já funciona) e fica versionada nele.
  - `enabled: false` é o kill-switch local sem apagar o arquivo.
  - Alternativas descartadas: lista central na skill (esquece-se de atualizar; fork
    entra por acidente de path) e o híbrido (complexidade sem ganho na v1).
- **Regra herdada do AUDITOR (ADR-009 de lá):** o marcador só **restringe**, nunca
  amplia — não existe chave que libere force, outra branch ou bump.

---

## ADR-005 — Segredo no staged: exclui o arquivo, commita o resto, reporta

> ⛔ **SUPERADO pelo [ADR-012](#adr-012--segredo-no-staged-aborta-a-árvore-inteira) em
> 2026-08-27.** A alternativa que este ADR descartou — abortar o repo inteiro — é a que
> vale hoje, e o motivo alegado para descartá-la (*"um arquivo esquecido seguraria todo o
> resto"*) foi resolvido tirando `.env.example` da regra de caminho, não commitando pela
> metade. Mantido na íntegra: a decisão de 27/08 só faz sentido contra o que se pensava aqui.

- **Data:** 2026-07-29 · **Status:** ~~Aceito~~ **Superado** (ADR-012)
- **Contexto:** `git add -A` autônomo captura arquivo novo com chave que o
  `.gitignore` não conhece; push publica; histórico é permanente.
- **Decisão:** scan mecânico do `git diff --cached` (padrões vendorizados do
  `redact.py` do AUDITOR) antes de todo commit. Encontrou →
  1. **des-stagea o(s) arquivo(s) ofensor(es)** — o arquivo inteiro, nunca edição de
     conteúdo;
  2. **commita o resto** — o trabalho não fica refém de um `.env` esquecido;
  3. **reporta visível**, com aviso persistente enquanto o arquivo seguir bloqueado
     (senão falso positivo vira arquivo esquecido para sempre).
  - Alternativa descartada: abortar o commit do repo inteiro (mais conservador, mas
    um arquivo esquecido seguraria todo o resto — contra o objetivo da skill).

---

## ADR-006 — Push: branch atual, nunca force; falha de push não é fatal

- **Data:** 2026-07-29 · **Status:** Aceito
- **Decisão:**
  1. Push **da branch checked-out**, e somente dela. Nunca `--force` (nem
     `--force-with-lease`), nunca amend, nunca rebase, nunca criar/trocar branch.
  2. Falha de push (rede, auth, non-fast-forward) → commit fica local, reporta,
     retenta no próximo ciclo. Non-fast-forward por 3 ciclos → para e marca para
     humano. **Nunca** escala para force.
  3. Particularidades por repo no marcador: `push: false` (só commita),
     `credential_bridge: gh` (remotes HTTPS), `lfs_bypass` (SHVIA-WEB/matomo).
- **Razão:** o COMMITTER publica em ciclo sem supervisão; toda operação que reescreve
  o remoto fica proibida por construção, não por prudência.

---

## ADR-007 — Agrupamento por assunto é a v2, aí sim com modelo

- **Data:** 2026-07-29 · **Status:** Aceito (direção aprovada pelo Samir)
- **Contexto:** a v1 faz commit-checkpoint — árvore com duas entregas misturadas vira
  um commit só. É onde "um objetivo por commit" degrada.
- **Decisão:** a v2 usa modelo para **particionar a árvore em commits lógicos** (por
  assunto/entrega), cada um com sua mensagem — é aí que o custo de modelo passa a
  valer, não na descrição de um checkpoint.
- **Fora de escopo até existir ADR próprio detalhando:** como agrupar arquivos
  interdependentes, ordem dos commits, interação com o caminho determinístico.

---

## ADR-008 — Auth da invocação de modelo: assinatura, API key dedicada ou gateway ShvIA

- **Data:** 2026-07-29 · **Status:** Aceito (direção; implementação na F3)
- **Contexto:** pergunta do Samir — "podemos incluir em ambas as skills o uso por
  API KEY também, usando um outro user agent?". Não viajou: execução headless via
  cron não deve depender da sessão logada, e isolar identidade e custo do trabalho
  autônomo é higiene.
- **Decisão:** a invocação de modelo (aqui, **só o fallback** — o caminho
  determinístico não usa modelo nenhum) suporta três modos:
  1. `subscription` (default) — login local do Claude Code; sem custo extra, mas
     consome a franquia da assinatura e exige sessão válida na máquina.
  2. `api-key` — `ANTHROPIC_API_KEY` dedicada no **ambiente do cron/serviço**;
     paga por token, isola a franquia, gasto medível e chave revogável.
  3. `shvia` — `ANTHROPIC_BASE_URL` apontando para o gateway ShvIA
     (inbound Anthropic-compat do SHVIA-WEB 2.42.0) + chave `shvia_usr_…`: o
     fallback roda **pela infra da casa**, com auditoria e custo no painel.
     ⚠️ Pré-requisito: a prova de fio real do inbound ainda está pendente lá.
- **Identidade ("outro user agent"):** não precisa de usuário de sistema separado —
  identidade = **chave dedicada** + trailer `Committed-By` no commit (já decidido).
  Autor git separado fica como opção futura, não default.
- **Regra dura:** chave **NUNCA** no `.committer.yml` — o marcador é versionado no
  repo alvo. Credencial vem do ambiente do cron/serviço, e de mais lugar nenhum.
- **Consequência:** o AUDITOR ganha a mesma pendência (registrada lá como P-12) —
  lá afeta o ciclo inteiro, não só um fallback.

---

## ADR-009 — Changelog desacoplado do `version.md`

- **Data:** 2026-07-30 · **Status:** Aceito
- **Contexto:** o rollout da F4 expôs que o caminho determinístico — o coração do
  desenho, "zero tokens no caminho feliz" — **quase não existia na prática**: de 24
  participantes, **18 tinham `version.md` em formato só-número**, então todo commit
  neles caía no fallback e custava uma chamada Sonnet.
- **O que impedia a correção óbvia:** converter os 18 `version.md` para markdown com
  changelog quebraria produção. **14 deles são lidos em runtime** (PHP, Rust,
  Python, TypeScript, shell) e vários com `trim(file_get_contents())`, que devolve o
  **arquivo inteiro** — o SHVIA-WEB passaria a exibir um documento markdown como
  número de versão. Consertar 14 parsers de produção para uma melhoria de fluxo de
  commit é risco desproporcional.
- **Decisão:** a entrada de changelog **não precisa estar no `version.md`**. A skill
  procura, nesta ordem: `CHANGELOG.md`, `docs/VERSION.md`, `version.md` — e o
  marcador pode apontar outro via `changelog_file:`.
- **Consequência:** um repo cujo `version.md` é lido em runtime vira determinístico
  **criando um arquivo novo**, sem tocar em código. A versão continua saindo do
  `version.md` (fonte da verdade); o changelog é só onde o **título** da entrega mora.
- **Alternativa descartada:** aceitar `version.md` só-número e gerar a mensagem do
  diff sempre pelo modelo — mantinha o custo, que é justamente o que se quer evitar.

---

## ADR-010 — Backoff por árvore inalterada e teto de fallback por repo

- **Data:** 2026-07-30 · **Status:** Aceito
- **Contexto (bug real, achado ao revisar a F4):** quando o fallback não produzia
  mensagem — `ABORT`, saída rejeitada, modelo fora do ar — o ciclo desfazia o stage
  e retornava **sem memorizar nada**. No disparo seguinte, a árvore era a mesma, o
  diff era o mesmo, e o modelo era invocado de novo. Com cron a cada 55 min, são
  **~26 tentativas por dia sobre o mesmo diff**, contra um teto de 24. Um único repo
  travado **esgotava o teto e deixava todos os outros sem fallback**.
- **Decisão:**
  1. **Backoff por árvore inalterada** — o hash do diff staged que falhou fica no
     estado; enquanto a árvore não mudar, o modelo não é reinvocado.
  2. **Só falha do diff gera backoff.** `generate_message` passa a devolver se a
     falha veio do modelo ter visto aquele diff (`ABORT`, saída rejeitada) ou se foi
     **transitória** (teto, rede, CLI ausente, auth). Memorizar transitória viraria
     bloqueio permanente por problema passageiro — defeito achado pelo próprio teste
     ao escrever esta mudança.
  3. **Teto diário por repo** (`COMMITTER_FALLBACK_REPO_CAP`, default 6) **além do
     global** (24). O teto global sozinho tem starvation: um repo movimentado
     consome a cota de todos.
- **Consequência:** sucesso limpa o backoff; mudar a árvore libera nova tentativa.
  Um repo com diff indescritível fica quieto até alguém agir, sem custo recorrente.

---

## ADR-011 — O ciclo não é dono de estado de outra skill: `skip_paths` no marcador

- **Data:** 2026-08-22 · **Status:** Aceito
- **Contexto (loop real, achado no EOP):** o DASHPROJECT instala um hook
  `post-commit` que escreve `.dashproject/pending` e `.dashproject/last-commit-ts`
  **depois de cada commit**, e no EOP esse diretório é versionado por decisão do
  Samir (ADR-086 de lá: "tudo se versiona, exceto segredo"). O efeito é que **todo
  commit deixa a árvore suja no instante seguinte**, sem ninguém trabalhar. O ciclo
  acorda, vê sujeira, `add -A`, commita — e o hook reescreve os dois arquivos, o que
  suja de novo. Uma volta por ciclo de cron, para sempre, com a máquina parada.
  Pior: como não há entrada de changelog nova, cada volta cai no **fallback**, cuja
  mensagem sai com a versão corrente e é **recusada pela trava do §1.75** (versão
  reutilizada) — que não gera backoff, porque o modelo não errou o diff. Cota de
  6/dia por repo queimada em algumas horas, zero commits produzidos.
- **Decisão:** chave `skip_paths` no marcador — CSV de caminhos que o ciclo **não
  stagea**. Aplicada em três pontos:
  1. **§1.3/§1.4** — sujeira sob esses caminhos não conta como árvore suja (nem para
     acordar o ciclo, nem para segurar a janela quieta) e o no-op segue **mudo**;
     uma linha por ciclo sobre `pending` seria ruído perpétuo no `cron.log`.
  2. **§1.5** — `git add -A -- ':(exclude)<path>'`: não entra no índice. É o
     pathspec, não a limpeza do índice, que fecha o **rename** dentro do caminho
     ignorado — `staged_files()` devolve o destino e não a origem, e a deleção
     vazaria para o commit.
  3. **Índice pré-existente** — o que já estava staged antes do ciclo (a skill dona
     fez `git add` e morreu antes do commit) é des-stageado.
- **Alternativas descartadas:** (a) *tirar `.dashproject/` do git* — resolveria o
  loop, mas o Samir mantém o versionamento porque o EOP roda em **duas estações** e
  o estado de medição precisa atravessar; (b) *só o auto-commit do DASHPROJECT* —
  fecha a árvore depois da revisão, mas deixa aberta a janela do debounce (10 min) e
  qualquer falha da outra skill reabre o loop. `skip_paths` é a única camada que não
  depende de a outra skill ter rodado com sucesso.
- **Consequência:** o marcador continua só **restringindo** (ADR-004) — não existe
  valor de `skip_paths` que faça o ciclo commitar mais. Quem escreve o caminho passa
  a ser o único dono dele: se o DASHPROJECT não commitar o próprio snapshot, ele
  fica sujo indefinidamente, e isso é visível no `git status` — não silencioso.
  Caminho absoluto ou com `..` é **marcador inválido**: pathspec para fora do repo
  derrubaria o `add` inteiro e o repo pararia de ser commitado sem uma linha de log.

---

## Decisões pendentes

| # | Pendência | Bloqueia | Fase |
|---|---|---|---|
| **P-02** | Esquema JSON formal do `.committer.yml` + validador | Robustez | F1 |
| **P-03** | Mecânica exata do hook `Stop` (o hook dispara o script ou agenda?) — a metade do cron está decidida: **crontab do Linux**, porque as rotinas agendadas do Claude Code rodam na nuvem e não enxergam `~/x` | Gatilhos | F2 |

**Resolvidas em 29/07:** **P-01** — estado local em `$XDG_STATE_HOME/committer/`
(`~/.local/state/committer/`), lock por repo com stale de 30 min · **P-05** —
piloto = **skill-COMMITTER + SHVIA-WEB** (decisão do Samir); critérios de aprovação
no escopo F4 — **ampliado no mesmo dia** (decisão do Samir) para os **24 repos** da
casa com `version.md`, via sweep de marcadores + `~/x/GIT/run.sh`; o que a F4 ainda
deve é o **bloco PS** nos `CLAUDE.md`/`AGENTS.md`, que é o que muda o hábito dos
agentes · **P-04** — teto diário **global de 24** invocações do fallback,
`COMMITTER_FALLBACK_DAILY_CAP` ajusta, `0` = kill-switch; contador no `state.json`,
estourou = indisponível (o repo espera, nunca degrada para mensagem inventada).

---

## ADR-012 — Segredo no staged: **aborta a árvore inteira**

- **Data:** 2026-08-27 · **Status:** Aceito (decidido pelo Samir) · **Supera:** ADR-005

### Contexto — o que o ADR-005 produziu em produção

Medido no SHVIA-WEB em 27/08/2026, rodando o `secret_scan.py` **desta skill** contra o
diff real da entrega 2.92.0 (`d823771`):

- O commit levou **49 arquivos e deixou 7**. Entre os que ficaram, a migration
  `create_managed_provider_keys_table` — **cujos consumidores entraram** (o model e a tela
  `/gestao`). HEAD ficou **não-deployável** até o complemento manual `c1a67dd`, 11 min
  depois. O CI pegou (vermelho em 2m31s), então o alarme existiu.
- Os **seis** arquivos de conteúdo acusam: `.env.example` por caminho sensível, e cinco por
  `assigned-secret`.
- 🔴 **Os cinco são falso-positivo, e todos pela mesma razão: a entrega ERA sobre
  credenciais.** Casaram um comentário citando a constante de chaves sensíveis de um
  redator de log, uma chave de objeto JS chamada `password` e fixtures de teste. O scanner
  não separa *"código que lida com segredo"* de *"um segredo"* — então **quanto mais a
  entrega for sobre credencial, mais completa é a amputação**.

**E o caso barulhento é o menos grave.** Migration derrubada quebra o CI e alguém vê. Os
silenciosos não: **teste** derrubado deixa a suíte verde com menos cobertura, e **doc**
derrubada viola a regra de doc-no-mesmo-commit sem acender nada.

### Decisão — e são DUAS mudanças, não uma

1. **Achou suspeita → aborta a árvore inteira.** Nada é commitado, o stage é desfeito, a
   árvore fica como estava. Commit parcial por decisão de scanner é o defeito: não existe
   caso em que amputar metade de uma entrega seja melhor que não commitar.
2. **`.env.example` (e `.sample`/`.template`/`.dist`) sai da regra de CAMINHO.** O padrão
   `\.env\..*$` casa `.env.example`, que é versionado **por convenção** e citado
   nominalmente na doc de agente dos repos. Ele **continua sujeito à regra de conteúdo** —
   que é justamente a que pegaria uma chave real colada ali por engano.

⚠️ **As duas andam juntas, e a (2) não é detalhe.** Sem ela, a (1) troca amputação
silenciosa por **paralisia frequente**: encostar no template de env travaria todo commit
do repo. Com as duas, o COMMITTER aborta só quando há motivo.

3. **O abort nomeia ARQUIVO e REGRA.** *"Abortei e esperei"* sem isso devolve o problema ao
   humano sem a informação para resolvê-lo.

### O que fica em observação, e não foi resolvido preventivamente

Os cinco falso-positivos de `assigned-secret` **vão continuar disparando** — e agora viram
trava, não amputação. Se acontecer duas vezes, a regra de conteúdo precisa de contexto
(extensão do arquivo, se está sob `tests/`). **Não foi inventado agora**: regra de
segurança com exceção especulativa é como se perde a regra.

### Verificação por mutação

- Voltar o *"commita o resto"* → **4 testes vermelhos**.
- Voltar `.env.example` à regra de caminho → **1 teste vermelho**.
- Suíte: **63 testes, 0 falhas**.

---

## ADR-013 — O ciclo cria a tag e a Release, e isso **não** é bumpar versão

**Status:** `ACEITA` · 02/09/2026

### Contexto

Medição da frota em 02/09/2026: **50 de 52 repositórios sem nenhuma Release
publicada**, 47 sem nenhuma tag, e ~2.764 versões distintas espalhadas pelos
históricos. O GitHub nunca deduz versão de mensagem de commit — sem tag, o
`2.110.161` é string no `git log`, o `git diff 2.110.160..2.110.161` falha e um
deploy ruim não tem para onde voltar.

O ciclo já é o último a tocar o repo antes de o trabalho virar público. Se a tag
não sai daqui, ela depende de alguém lembrar.

### Decisão

Depois de um **push bem-sucedido** (§1.11), o ciclo cria a tag — nome = a versão
**pura**, sem `v` — e publica a Release. Chave `release: true` no marcador
(`false` desliga).

**Isso não fere o [ADR-002](#adr-002)** (*"o COMMITTER nunca bumpa versão"*): a
tag **copia** um número que o agente já escreveu no `version.md`. Decidir a
versão continua fora do escopo; carimbar a que já existe, não.

Roda depois do push, e não depois do commit, porque uma Release aponta para um
commit que precisa existir **no remoto**.

### Consequências

Falha aqui **não é fatal** e não desfaz nada: o `.github/workflows/release.yml`
do próprio repo é a segunda rede. Os dois donos guardam pela mesma pergunta —
*"a tag já existe?"* — então quem chegar primeiro ganha e o outro vira no-op.
Dois donos de uma regra costumam ser defeito; aqui a corrida é inofensiva **por
construção**, e o segundo dono existe porque o marcador está `enabled: false` na
maioria dos repos hoje — sem o workflow, quase ninguém teria Release.

O caminho preferido é o `tools/release.sh` do repo alvo, não uma segunda
implementação aqui: duas cópias de uma regra é como uma regra passa a ter duas
versões, uma errada.

### Verificação por mutação

- Neutralizar a chamada de `release()` no push → **3 testes vermelhos**.
- Suíte: **67 testes, 0 falhas**.
