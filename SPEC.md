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
1. **Determinístico (caminho feliz, zero tokens):** `version.md` está entre os
   arquivos staged **e** o diff dele adiciona entrada nova no topo do changelog →
   mensagem = `X.Y.Z - <título da entrada>`. O próprio diff denuncia que o agente
   principal preparou o handoff.
2. **Fallback (Sonnet):** senão → o subagente lê `git diff --cached` e escreve **uma
   linha** honesta em português; versão = a atual do `version.md`, repetida
   (sancionado — ADR-002). Prompt em
   [prompts/committer-fallback.md](prompts/committer-fallback.md). Se não conseguir
   descrever com especificidade, retorna `ABORT` e o repo fica para o próximo ciclo
   com aviso — **mensagem vaga é proibida**.

O COMMITTER **nunca bumpa versão**. Quando o diff claramente merecia bump (mudança de
comportamento sem entrada de changelog), anota a pendência no relatório.

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
  `last_commit` por repo e locks. ⛔ Caminho exato (`~/.local/state/committer/`?) na
  F1.

---

## 2. `.committer.yml` (o marcador de opt-in)

A **presença** do arquivo é o opt-in. Todas as chaves têm default:

```yaml
enabled: true          # false = kill-switch local sem apagar o marcador
push: true             # false = só commita, não pusha
quiet_window_min: 5    # janela quieta
branch_only: null      # ex.: master — se setado, só commita nessa branch
credential_bridge: gh  # gh | none (SSH)
lfs_bypass: false      # true em SHVIA-WEB / matomo
fallback: sonnet       # modelo do fallback; "off" = só caminho determinístico
```

Regra herdada do AUDITOR (ADR-009 de lá): o marcador só pode **restringir** o
comportamento, nunca ampliar — não existe chave que libere force, outra branch ou
bump.

⛔ Esquema JSON formal na F1, junto com o validador.

---

## 3. Gatilhos (ADR-003)

| Gatilho | Papel |
|---|---|
| Hook `Stop` do agente principal | **Primário** — fim de turno é árvore em ponto de descanso; dispara o pipeline do repo da sessão |
| Cron **30 min** | Rede de segurança — pega sessões mortas sem `Stop` e trabalho manual |
| Janela quieta 5 min | Guarda transversal dos dois |

Lock por repo (arquivo em estado local): dois disparos simultâneos (Stop + cron) →
o segundo desiste em silêncio. O mesmo lock ordena COMMITTER × AUDITOR — nunca os
dois ciclos no mesmo repo ao mesmo tempo.

---

## 4. Modelo

- Caminho determinístico: **nenhum modelo**.
- Fallback: `sonnet` (subagente/headless com `model: sonnet`), entrada = diff staged,
  saída = uma linha ou `ABORT`. Sem tools. ⛔ Teto de invocações por dia na F3.

---

## 5. Fora de escopo da v1 (não relitigar sem ADR)

- Agrupar a árvore em múltiplos commits por assunto → **v2** (ADR-007).
- Bump de versão, resolução de conflito, force push, amend — **nunca**, em versão
  nenhuma sem ADR.
- Validar build/testes antes de commitar (o commit é checkpoint; validação é do
  agente principal).
