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

- **Data:** 2026-07-29 · **Status:** Aceito (decidido pelo Samir entre duas opções)
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
