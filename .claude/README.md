# Perfil de modelo Claude Code — skill-COMMITTER

`.claude/` deste projeto segue o padrão dos repos Blue3/samirhvbr: **perfil de
modelo + postura de permissões**. Núcleo previsto em Python 3 sem dependência
externa; allow-list enxuta até a F1 existir.

| Arquivo | Papel |
|---------|-------|
| `settings.json` | Perfil **ativo** (versionado). Opus-only `opus[1m]`, `effortLevel: xhigh`, `defaultMode: plan`, deny-list de segurança. |
| `README.md` | Este arquivo. |

## Regras que valem lembrar

- **Não adicionar `CLAUDE_CODE_DISABLE_1M_CONTEXT`** — é ela que derruba a janela
  para 200K.
- **Effort `max` vai por sessão** (`/effort max`); o campo do JSON aceita até
  `xhigh`.
- `crontab`/`systemctl` em **ask** de propósito: o produto instala gatilho de
  agendamento (F2) — ninguém instala persistência na máquina sem o Samir ver. Mesma
  postura do irmão AUDITOR.
- `git filter-branch`/`filter-repo` negados: o auto-pusher de `~/x` faz
  `pull --rebase` e desfaz reescrita — reescrever aqui só quebra o repo.
- **Distinção importante:** o produto (a skill) commita e pusha nos repos **alvo**
  quando estiver operando; *este* repositório segue o fluxo manual normal da casa
  até lá.

## Modelo do produto vs modelo do desenvolvimento

- Desenvolvimento deste repo: Opus (perfil acima).
- **Fallback do produto: `sonnet`** — definido em `SPEC.md` §4 e no marcador
  `.committer.yml` (`fallback: sonnet`); não é configurado por este `.claude/`.
