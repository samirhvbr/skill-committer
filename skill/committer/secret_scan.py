#!/usr/bin/env python3
"""Deteccao de segredos no conteudo staged (T-01 do SECURITY.md).

VENDORIZADO do AUDITOR (`~/x/AUDITOR/skill/auditor/lib/redact.py`) por decisao do
ADR-001: repos separados, padroes copiados. Manter os REGEXES em sincronia com o
original ao evoluir qualquer um dos dois — a fonte da verdade dos padroes e o
AUDITOR, que tem a suite de testes de redacao (la o uso e redigir texto; aqui e
DETECTAR e excluir o arquivo do stage — ADR-005 daqui).

Sem dependencias externas: precisa rodar no cron de qualquer maquina da casa.
"""

from __future__ import annotations

import re

# Mesmos padroes do redact.py do AUDITOR (versao 0.3.0 de la), sem os grupos de
# preservacao — aqui nao ha reescrita de texto, so deteccao.
_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "pem",
        re.compile(
            r"-----BEGIN[A-Z ]*PRIVATE KEY-----.*?-----END[A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    # Variante para diffs: um arquivo PEM novo aparece linha a linha; o header
    # sozinho ja e motivo suficiente para bloquear o arquivo.
    ("pem-header", re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA|AROA|AIDA)[A-Z0-9]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("google-api-key", re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b")),
    ("stripe-like", re.compile(r"\b[sprk]k_(?:live|test)_[A-Za-z0-9]{10,}\b")),
    (
        "authorization-header",
        re.compile(r"(?i)\bauthorization\s*:\s*(?:bearer|basic|token)\s+[A-Za-z0-9._~+/=-]{8,}"),
    ),
    ("url-credentials", re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s:@/]+:[^\s@/]+@")),
    (
        "assigned-secret",
        re.compile(
            r"""(?ix)
            \b(
              [A-Z0-9_]*
              (?: SECRET | PASSWD | PASSWORD | TOKEN | API[_-]?KEY | ACCESS[_-]?KEY
                | PRIVATE[_-]?KEY | CLIENT[_-]?SECRET | DSN | CREDENTIAL[S]? )
              [A-Z0-9_]*
            )
            (\s*[:=]\s*)
            (["']?)
            ([^\s"'#,;()]{6,})
            (?![^\s"'#,;])
            \3
            """
        ),
    ),
    # Valor sem parenteses + lookahead de fronteira (sincronizado com o redact.py
    # do AUDITOR em 29/07): expressao de codigo tem "()", segredo real nao — e sem
    # o lookahead o motor casaria um PREFIXO do valor (`out.spl` em
    # `tokens = out.split(...)`). Foi o proprio dogfood daqui que achou: o scan
    # marcava committer_cycle.py e bloquearia o arquivo do ciclo para sempre.
]

# Caminhos cujo CONTEUDO nunca deveria entrar num commit autonomo, mesmo que o
# .gitignore do repo nao os conheca. Identico ao is_sensitive_path do AUDITOR.
_SENSITIVE_PATHS = re.compile(
    r"""(?ix)
    (?:^|/)
    (?:
        \.env(?:\.[A-Za-z0-9_-]+)?
      | auth\.json
      | id_rsa(?:\.[A-Za-z0-9_-]+)?
      | id_ed25519(?:\.[A-Za-z0-9_-]+)?
      | .*\.(?: pem | key | p12 | p8 | pfx | jks | keystore )
    )
    $
    """
)


def is_sensitive_path(path: str) -> bool:
    """True quando o caminho, por si so, ja justifica excluir o arquivo do stage."""
    return bool(_SENSITIVE_PATHS.search((path or "").replace("\\", "/")))


def scan_text(text: str) -> list[str]:
    """Retorna os tipos de segredo encontrados em `text` (linhas adicionadas de um
    diff, tipicamente). Lista vazia = limpo. Nunca retorna o valor encontrado —
    quem chama nao precisa dele, e log nao e lugar de segredo."""
    if not text:
        return []
    found: list[str] = []
    for kind, pattern in _RULES:
        if pattern.search(text):
            found.append(kind)
    return found
