# skill-COMMITTER

Skill que tira dos agentes principais (Opus, Fable) o compromisso de fazer commits.
Um subagente barato (Sonnet) — e, na maioria dos ciclos, **nenhum modelo** — lê o que
ficou sem commit nos repositórios participantes, monta a mensagem no padrão da casa
(`X.Y.Z - Descrição em português`) a partir do `version.md`, commita e pusha.

> **Documentação:** [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) (regras de quem
> desenvolve este repo) · [SECURITY.md](SECURITY.md) (modelo de ameaça — leitura
> obrigatória) · [SPEC.md](SPEC.md) (pipeline e configuração) ·
> [prompts/committer-fallback.md](prompts/committer-fallback.md) (prompt do fallback) ·
> [docs/README.md](docs/README.md) (índice técnico) ·
> [docs/decisoes.md](docs/decisoes.md) (ADRs) ·
> [version.md](version.md) (versão e formato de commit) ·
> [.continue/estado-atual.md](.continue/estado-atual.md) (onde o projeto está).
>
> Irmão do [AUDITOR](https://github.com/samirhvbr/AUDITOR) — mesmo padrão de
> documentação, mesma política de scheduler, e os padrões de segredo vendorizados de
> lá. Status: **proposta fechada, sem implementação** (fase F0 concluída).

## Objetivo

Hoje o fluxo da casa manda o agente que produz também commitar: validar → bump no
`version.md` → commit `X.Y.Z - descrição` → push. Isso gasta tokens de modelo caro em
tarefa mecânica e interrompe o fluxo de desenvolvimento.

Com o COMMITTER:

- o agente principal **conclui a entrega bumpando `version.md` + entrada de
  changelog** — trabalho de documentação que já era dele — e para por aí;
- o COMMITTER, em ciclo, encontra a árvore suja, monta a mensagem **a partir do
  changelog** (zero tokens no caminho feliz), commita e pusha;
- o modelo (Sonnet) só entra quando o changelog não foi atualizado — e a existência
  desse fallback é sinal de handoff malfeito, não o caminho normal.

## Pipeline (resumo — normativo em [SPEC.md](SPEC.md))

Por repositório participante, a cada disparo:

1. **Elegibilidade** — só repos com o marcador `.committer.yml` (opt-in explícito;
   fork de terceiro nunca terá o marcador).
2. **Sanidade** — merge/rebase/bisect em andamento, conflito ou detached HEAD →
   no-op com aviso. O COMMITTER nunca "ajuda" a resolver estado quebrado.
3. **Sujo?** — árvore limpa → no-op silencioso.
4. **Janela quieta** — arquivo modificado nos últimos 5 min → adia (alguém está
   trabalhando agora).
5. **Stage** — `git add -A`; o `.gitignore` de cada repo é a primeira linha de defesa.
6. **Scan de segredo** no diff staged (padrões do `redact.py` do AUDITOR). Achou →
   **exclui o arquivo, commita o resto, reporta visível** (ADR-005).
7. **Mensagem** — `version.md` staged com entrada nova → `X.Y.Z - título da entrada`
   (determinístico). Senão → fallback Sonnet: uma linha honesta; se não conseguir
   descrever, **aborta** — vago é proibido (ADR-002).
8. **Commit** — com trailer identificável da skill.
9. **Push da branch atual** — nunca force; falha de push não é fatal (retenta).
10. **Relatório** — uma linha por repo tocado; estado local mínimo.

## Gatilho

Híbrido (ADR-003): **hook `Stop`** do agente principal como disparo primário (fim de
turno = árvore em ponto de descanso) + **cron de 30 min** como rede de segurança para
sessões que morreram sem `Stop`. A janela quieta de 5 min protege contra sessões
paralelas no mesmo repo.

## O que o COMMITTER nunca faz

- Bumpar versão (ADR-002) — repetir a versão atual com conteúdo novo é sancionado
  pelo padrão da casa; decidir bump é julgamento do agente principal. Quando um bump
  parecia devido, o COMMITTER **anota**, não decide.
- `push --force`, amend, rebase, trocar de branch, resolver conflito.
- Commitar em repo sem o marcador `.committer.yml`.
- Editar arquivo de trabalho — ele commita o que está lá ou exclui do stage; nunca
  altera conteúdo.
- Mensagem vaga ("ajustes", "update", "wip").

## Mudança de hábito nos agentes principais

Bloco a incluir nos `CLAUDE.md`/`AGENTS.md` dos repos participantes (sweep após o
piloto — F4):

> **PS — Commits:** Existindo a skill **COMMITTER** neste ambiente, o agente NÃO
> commita nem pusha por padrão: conclui a entrega bumpando `version.md` + entrada de
> changelog (é dali que o committer tira a mensagem) e deixa a árvore pronta.
> Exceções: o Samir pediu commit explícito, ou a tarefa exige commit/push imediato
> (SHA para referência, deploy, PR). Forks/contribuições de terceiros ficam fora dos
> dois fluxos.

## Limitações declaradas da v1

- **Commit-checkpoint:** árvore com duas entregas misturadas vira um commit só, com a
  mensagem da entrada do topo. "Um objetivo por commit" degrada nesses casos — de
  propósito e declarado. A v2 (ADR-007) agrupa por assunto, aí sim com modelo.
- O agente principal continua livre para commits cirúrgicos quando importa.

## Interações com o resto do ambiente

- **AUDITOR** — commits regulares dão ao AUDITOR unidades limpas para auditar. Os
  dois ciclos não rodam simultâneos no mesmo repo (lock; ordem committer→auditor).
- **Auto-pusher de `~/x`** (commits "Version X (clean)") — com o COMMITTER rodando
  antes/mais frequente, ele encontra árvore limpa e seus commits-lixo desaparecem
  naturalmente. Sinergia, não conflito.
