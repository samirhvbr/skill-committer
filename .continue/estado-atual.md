# Estado atual — skill-COMMITTER

- **2026-07-29 — nasce o repositório com a proposta fechada (`0.1.0` / F0).**
  Conversa com o Samir fechou o desenho inteiro em uma sessão; decisões dele,
  registradas nos ADRs:
  - Repo próprio `skill-COMMITTER` (2 T confirmado), não uma segunda skill dentro do
    AUDITOR (ADR-001).
  - Mensagem changelog-first; **nunca bumpa versão** — "não há problema ter commits
    com a mesma versão, desde que seja outro conteúdo" (ADR-002).
  - Cron 30 min + hook `Stop` + janela quieta 5 min (ADR-003).
  - Opt-in por marcador `.committer.yml` no repo (ADR-004, escolhido entre 3 opções).
  - Segredo no staged → exclui o arquivo, commita o resto (ADR-005, escolhido entre
    2 opções).
  - Agrupamento por assunto aprovado como **v2** (ADR-007).
  - O PS para os `CLAUDE.md` da casa está pronto no `README.md` §Mudança de hábito —
    o Samir confirmou o texto; sweep só depois do piloto (F4).

---

## Onde o projeto está

**F0 concluída: documentação completa, zero implementação.** Pipeline normativo no
`SPEC.md`, 7 ADRs, modelo de ameaça T-01–T-07, prompt do fallback escrito.

## Próximo passo

**F1 — núcleo determinístico** (`.continue/escopo-projeto.md`): o script do ciclo
sem modelo nenhum, com o scan de segredo vendorizado do AUDITOR e testes nos dois
sentidos. Depende de fechar **P-01** (caminho do estado local) e **P-02** (esquema do
`.committer.yml`) — ambas decisões técnicas, não precisam do Samir.

## Decisões que precisam do Samir

- **P-05** — quais 2 repos entram no piloto (sugestão: este + um de movimento real
  tipo SHVIA-WEB) e os critérios de aprovação antes do sweep.
- **P-03** parcialmente — se o cron vai de rotina agendada da plataforma ou crontab
  do sistema (toca a máquina dele).

## Contexto de ambiente (herdado da casa)

- `~/x` tem auto-pusher ("Version X (clean)" + `pull --rebase`): nunca reescrever
  histórico no working copy; conferir `git log` antes de assumir entrega registrada.
- Push HTTPS usa a ponte `gh`; este repo nasce com remoto SSH.
- O irmão AUDITOR (`~/x/AUDITOR`) tem os padrões de segredo (`redact.py`) a
  vendorizar na F1 e a política de scheduler (ADR-008 de lá) que este projeto herda.
