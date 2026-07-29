# skill-COMMITTER — Guia do Agente (AGENTS.md)

> **Leia também:** [README.md](README.md) (o produto) ·
> [SECURITY.md](SECURITY.md) (**leitura obrigatória** — modelo de ameaça) ·
> [SPEC.md](SPEC.md) (pipeline normativo e `.committer.yml`) ·
> [docs/decisoes.md](docs/decisoes.md) (ADR-001 a ADR-007 + pendências) ·
> [prompts/committer-fallback.md](prompts/committer-fallback.md) (prompt do fallback) ·
> [version.md](version.md) (versão + formato de commit).
>
> `CLAUDE.md` e `AGENTS.md` são **espelhados** abaixo do H1 — editar os dois.

---

## 🔄 Antes de começar: `git pull`

**SEMPRE** verifique atualizações remotas antes de escrever ou alterar qualquer
coisa neste repositório:

```bash
git pull          # já está pré-autorizado (allow)
```

---

## O que é este repo

Skill **committer** (comando `/committer`): subagente que tira dos agentes
principais o compromisso de commitar. Em ciclo (hook `Stop` + cron 30 min), lê a
árvore suja dos repos com marcador `.committer.yml`, monta a mensagem
`X.Y.Z - descrição` a partir do `version.md` (determinístico; Sonnet só como
fallback), commita e pusha a branch atual.

Irmão do **AUDITOR** (`~/x/skill-AUDITOR`): mesmo padrão de documentação, mesma política
de scheduler, padrões de segredo vendorizados do `redact.py` de lá.

---

## ⚠️ Estado do projeto: F1 entregue, piloto armado

O que **existe e roda**: `skill/committer/committer_cycle.py` (pipeline
determinístico completo, com `--dry-run`), `secret_scan.py` (vendorizado do
AUDITOR) e **20 testes** verificados por mutação. Piloto: este repo + SHVIA-WEB,
marcadores instalados; cron no `SPEC.md` §3.

O que **não existe**: fallback Sonnet (F3 — sem ele o SHVIA-WEB só vigia, não
commita), hook `Stop` (F2 restante), sweep do PS nos repos da casa (F4).

```bash
python3 -m unittest discover -s tests -v          # 20 testes
python3 skill/committer/committer_cycle.py <repo> --dry-run --quiet-min 0
```

Ao trabalhar aqui:

- **Não descreva como pronto** o que é spec. `SPEC.md` marca com ⛔ o que falta.
- **Não feche pendência (P-01 a P-05) dentro de um how-to** — decisão nova vira ADR
  em [docs/decisoes.md](docs/decisoes.md).
- **Não confunda "escrito" com "implementado"** — regra herdada do AUDITOR: controle
  só conta com teste que **falha quando o controle é desligado**.

---

## Padrão de Commits (obrigatório)

Formato: `X.Y.Z - Descrição curta em português`. A versão **sempre** vem de
[`version.md`](version.md), bumpada **no mesmo commit**. Critério resumido: **Z** =
entrega que muda regra/spec/prompt/segurança; **Y** = fase concluída, quebra de
contrato, ADR que muda direção; **X** = skill estável operando. **Proibido**
`feat:`/`fix:`/`chore:` e mensagens vagas.

(Sim: este repo define a skill que commita pelos outros e, enquanto ela não opera,
os commits daqui seguem o fluxo manual da casa.)

---

## Regras do produto (não relitigar sem ADR)

1. Repo próprio, v1 = **commit-checkpoint**, um commit por repo por ciclo (ADR-001).
2. Mensagem **changelog-first**; fallback Sonnet só sem entrada nova; **nunca bumpa
   versão**; vago é proibido → `ABORT` (ADR-002).
3. Gatilho híbrido: `Stop` primário + cron 30 min + janela quieta 5 min + lock
   (ADR-003).
4. Opt-in **por marcador** `.committer.yml` no repo participante; marcador só
   restringe, nunca amplia (ADR-004).
5. Segredo no staged → **exclui o arquivo, commita o resto, reporta** (ADR-005).
6. Push da **branch atual**, nunca force/amend/rebase; falha de push não é fatal e
   nunca escala (ADR-006).
7. Agrupamento por assunto = **v2**, com modelo (ADR-007).

E o que o COMMITTER **nunca** faz: bumpar versão, editar conteúdo de arquivo,
resolver conflito/merge, trocar de branch, mensagem vaga, commit em repo sem
marcador.

---

## Regras de escrita

- **Idioma do repositório: PT-BR.** Artefatos que a skill produz (mensagens de
  commit) também são em português — é o padrão da casa.
- Documentação durável → `docs/`. Notas de trabalho → `.continue/`. Contrato
  normativo → `SPEC.md`. Prompt do produto → `prompts/` (nunca na raiz com nome que
  ferramenta carrega sozinha — lição do ADR-007 do AUDITOR).
- Sem link para arquivo inexistente; futuro se descreve em texto.
- Distinguir **fato observado**, **inferência** e **recomendação**.

---

## Como o Claude Code deve operar aqui

- **Planeje antes de editar** (`defaultMode: plan`).
- Mudanças pequenas e atômicas; ao concluir entrega, **atualize `version.md`** e
  `.continue/estado-atual.md`.
- Decisão pendente bloqueia? Faça o que não depende dela e pergunte — não escolha
  por conta própria.
- Fixtures de teste **nunca** usam formato real de chave de provedor — montar por
  concatenação (push protection barra, e com razão).

---

## Referências rápidas

- Versão e commits: [version.md](version.md)
- Modelo de ameaça: [SECURITY.md](SECURITY.md)
- Pipeline e config: [SPEC.md](SPEC.md)
- Decisões: [docs/decisoes.md](docs/decisoes.md)
- Escopo e fases: [.continue/escopo-projeto.md](.continue/escopo-projeto.md)
- Estado atual: [.continue/estado-atual.md](.continue/estado-atual.md)
- Perfil do agente: [.claude/README.md](.claude/README.md)
- Irmão: `~/x/skill-AUDITOR` (padrões de segredo, política de scheduler)
- Remoto: `github.com/samirhvbr/skill-COMMITTER` (privado) · branch `master`
