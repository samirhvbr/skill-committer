# Documentação técnica — skill-COMMITTER

Índice de `docs/`. Documentação **durável** mora aqui; notas de trabalho, escopo e
estado em [`.continue/`](../.continue/); contrato normativo em [`SPEC.md`](../SPEC.md);
prompt do produto em [`prompts/`](../prompts/).

> Projeto em **F0**: proposta fechada, sem implementação. O que estiver marcado com
> ⛔ no `SPEC.md` é lacuna conhecida, não esquecimento.

## Nesta pasta

| Arquivo | O que é |
|---|---|
| [decisoes.md](decisoes.md) | **ADRs.** ADR-001 a ADR-007 (todas as decisões da conversa de 29/07) + pendências P-01 a P-05. Decisão nova entra aqui. |

## Fora desta pasta

| Arquivo | O que é |
|---|---|
| [../README.md](../README.md) | O produto: objetivo, pipeline resumido, limitações declaradas, bloco PS para os repos da casa. |
| [../SPEC.md](../SPEC.md) | **Normativo.** Pipeline em 10 estágios, `.committer.yml`, gatilhos, estado. |
| [../SECURITY.md](../SECURITY.md) | Modelo de ameaça (T-01 a T-07). **Leitura obrigatória.** |
| [../prompts/committer-fallback.md](../prompts/committer-fallback.md) | Prompt do fallback Sonnet — artefato do produto. |
| [../version.md](../version.md) | Fonte de verdade da versão, gatilhos de bump, formato de commit. |
| [../CLAUDE.md](../CLAUDE.md) / [../AGENTS.md](../AGENTS.md) | Regras de quem desenvolve este repo. Espelhados — editar os dois. |
| [../.continue/escopo-projeto.md](../.continue/escopo-projeto.md) | Fases F0–F4 + v2, com critério de pronto. |
| [../.continue/estado-atual.md](../.continue/estado-atual.md) | Onde o projeto está e o que precisa do Samir. |
| [../.claude/README.md](../.claude/README.md) | Perfil de modelo e postura de permissões. |

## Por onde começar

- **Entender o produto** → `../README.md`, depois `decisoes.md`.
- **Vai implementar (F1)** → `../SPEC.md` + `../SECURITY.md`, e o `redact.py` do
  irmão AUDITOR (`~/x/SKILLS/skill-AUDITOR/skill/auditor/lib/redact.py`) para vendorizar.
- **Vai mexer no prompt do fallback** → T-04 do `../SECURITY.md` primeiro.

## Convenções

- PT-BR em tudo — inclusive nas mensagens de commit que a skill produz.
- Documento novo aqui entra **neste índice** no mesmo commit.
- Sem link para arquivo inexistente.
- Fato observado ≠ inferência ≠ recomendação.
