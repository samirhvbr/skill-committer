# Versão — skill-COMMITTER

**Versão atual:** `0.1.0`

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
