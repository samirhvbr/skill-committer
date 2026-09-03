#!/usr/bin/env python3
"""committer_cycle — um ciclo do COMMITTER sobre cada repositorio candidato.

Pipeline normativo no SPEC.md §1 (a ordem dos estagios aqui segue a de la).
Decisoes em docs/decisoes.md (ADR-001 a ADR-008). Resumo do contrato:

- So repos com o marcador `.committer.yml` participam (ADR-004).
- Mensagem vem do changelog do `version.md` staged (deterministico, zero tokens);
  sem entrada com titulo → o caso e do fallback Sonnet (F3, ainda nao implementado):
  este script REPORTA e desfaz o stage, nunca inventa mensagem (ADR-002).
- Segredo no staged → ABORTA a arvore inteira, nomeando arquivo e regra (ADR-012,
  supera o ADR-005). `.env.example` e afins nao contam como caminho sensivel — senao
  o abort viraria paralisia; eles seguem sujeitos a regra de CONTEUDO.
- `skip_paths` no marcador → o caminho nem e staged: estado de outra skill tem dono,
  e nao e este ciclo (ADR-011).
- Push da branch atual, nunca force; falha nao e fatal, 3 seguidas param (ADR-006).
- Nunca bumpa versao, nunca edita conteudo, nunca resolve conflito.

Uso:
    committer_cycle.py REPO [REPO...] [--dry-run] [--quiet-min N]

Exit code sempre 0 (e um ciclo de cron; erro de um repo nao derruba os outros) —
exceto uso invalido da linha de comando.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secret_scan import is_sensitive_path, scan_text  # noqa: E402
import fallback as fb  # noqa: E402

MARKER = ".committer.yml"
LOCK_STALE_S = 30 * 60
FF_FAILS_LIMIT = 3

# Arquivos onde a entrada de changelog e procurada, em ordem, quando o marcador nao
# aponta um. Existe porque a maioria dos repos da casa le o `version.md` em RUNTIME
# (PHP/Rust/Python/shell) e varios com `trim(file_get_contents())`, que pega o
# arquivo inteiro — transformar aquele arquivo em markdown quebraria a versao
# exibida em producao. Um `CHANGELOG.md` novo nao tem esse acoplamento: o repo vira
# deterministico sem tocar em codigo (ADR-009).
CHANGELOG_CANDIDATES = ("CHANGELOG.md", "docs/VERSION.md", "version.md")

# Chaves aceitas no marcador e seus defaults (SPEC §2). Chave desconhecida e ERRO
# (fail-closed): typo em "enabled" nao pode virar silencio.
MARKER_DEFAULTS: dict[str, object] = {
    "enabled": True,
    "push": True,
    "quiet_window_min": 5,
    "branch_only": None,
    "credential_bridge": "auto",   # auto = bridge gh so quando o remote e http(s)
    "lfs_bypass": False,
    "fallback": "sonnet",
    "changelog_file": None,        # None = tenta CHANGELOG_CANDIDATES em ordem
    "skip_paths": None,            # CSV de caminhos que o ciclo nao stagea (ADR-011)
    "release": True,               # false = nao cria tag/Release apos o push (ADR-013)
}

# -c aplicados quando lfs_bypass=true: neutralizam os filtros LFS em maquinas sem
# git-lfs (caso matomo). Sem efeito em repo sem .gitattributes de LFS.
LFS_BYPASS_CFG = [
    "-c", "filter.lfs.clean=cat",
    "-c", "filter.lfs.smudge=cat",
    "-c", "filter.lfs.process=",
    "-c", "filter.lfs.required=false",
]

GH_BRIDGE_CFG = ["-c", "credential.helper=!gh auth git-credential"]

# Entrada de changelog com titulo, no formato da casa:
#   ### `0.2.0` — 2026-07-29 — Titulo da entrega
# Aceita 1-4 #, hifen/en/em-dash, data opcional, crase opcional.
CHANGELOG_ENTRY = re.compile(
    r"^\+\s*#{1,4}\s*`?(\d+\.\d+\.\d+)`?\s*[—–-]+\s*(?:\d{4}-\d{2}-\d{2}\s*[—–-]+\s*)?(\S.*?)\s*$"
)
# Bump sem titulo: "**Versão atual:** `X.Y.Z`" ou linha so com o numero (SHVIA-WEB).
VERSION_ONLY = re.compile(r"^\+\s*(?:\*{0,2}Vers[aã]o atual:?\*{0,2}\s*)?`?(\d+\.\d+\.\d+)`?\s*$")


def repo_current_version(repo: Path) -> str:
    """Primeiro semver do version.md do repo (working tree — que ja reflete o que
    esta staged). E a versao que o fallback DEVE usar; ele nunca inventa."""
    try:
        text = (repo / "version.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r"\d+\.\d+\.\d+", text)
    return m.group(0) if m else ""


def state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "committer"


def skill_version() -> str:
    try:
        text = (Path(__file__).resolve().parents[2] / "version.md").read_text(encoding="utf-8")
        m = re.search(r"\d+\.\d+\.\d+", text)
        return m.group(0) if m else "0.0.0"
    except OSError:
        return "0.0.0"


def slug(repo: Path) -> str:
    real = str(repo.resolve())
    return f"{repo.name}-{hashlib.sha1(real.encode()).hexdigest()[:8]}"


def git(repo: Path, *args: str, cfg: list[str] | None = None,
        check: bool = False) -> subprocess.CompletedProcess:
    cmd = ["git", *(cfg or []), "-C", str(repo), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


class Report:
    """Acumula as linhas do relatorio — uma por evento, prefixadas pelo repo."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.lines: list[str] = []

    def add(self, msg: str) -> None:
        self.lines.append(f"[{self.name}] {msg}")


def parse_skip_paths(raw: str) -> list[str]:
    """`skip_paths: .dashproject/, .loop/` → `['.dashproject', '.loop']` (ADR-011).

    CSV numa linha porque o marcador e um subset YAML plano — lista com `- ` exigiria
    outro parser, e o arquivo continua YAML valido do jeito que esta.

    Fail-closed em caminho absoluto ou com `..`: pathspec para fora do repo faz o
    `git add` inteiro falhar, e o ciclo pararia de commitar aquele repo **em
    silencio** — o modo de falha que o marcador nao pode ter."""
    out: list[str] = []
    for item in raw.split(","):
        entry = item.strip()
        if not entry:
            continue
        if entry.startswith("/") or ".." in Path(entry).parts:
            raise ValueError(f"{MARKER}: skip_paths nao aceita {entry!r} "
                             "(so caminho relativo dentro do repo)")
        trimmed = entry.strip("/")
        if trimmed:
            out.append(trimmed)
    return out


def is_skipped(path: str, skips: list[str]) -> bool:
    """True se `path` esta sob algum caminho ignorado. Compara por segmento: `.loop`
    nao casa `.loopback/x` — prefixo cru casaria."""
    return any(path == s or path.startswith(s + "/") for s in skips)


def parse_marker(path: Path) -> dict:
    """Parser do subset YAML do marcador: linhas `chave: valor` planas, comentarios
    com # e vazias. Fail-closed: chave desconhecida ou valor de tipo errado e erro
    (SPEC §2 — o marcador so restringe; um typo nao pode afrouxar nada)."""
    cfg = dict(MARKER_DEFAULTS)
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"{MARKER}:{n}: linha sem 'chave: valor': {raw!r}")
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip().strip("\"'")
        if key not in MARKER_DEFAULTS:
            raise ValueError(f"{MARKER}:{n}: chave desconhecida {key!r}")
        default = MARKER_DEFAULTS[key]
        if isinstance(default, bool):
            if value.lower() not in ("true", "false"):
                raise ValueError(f"{MARKER}:{n}: {key} espera true/false, veio {value!r}")
            cfg[key] = value.lower() == "true"
        elif isinstance(default, int):
            if not value.isdigit():
                raise ValueError(f"{MARKER}:{n}: {key} espera inteiro, veio {value!r}")
            cfg[key] = int(value)
        else:  # str | None
            cfg[key] = None if value.lower() in ("null", "~", "none", "") else value
    cfg["skip_paths"] = parse_skip_paths(str(cfg["skip_paths"] or ""))
    return cfg


def dirty_paths(repo: Path) -> list[str]:
    """Caminhos sujos via `status --porcelain=v1 -z` (NUL-separado, aguenta espaco
    e rename — rename consome dois campos)."""
    out = git(repo, "status", "--porcelain=v1", "-z").stdout
    paths: list[str] = []
    tokens = out.split("\0")
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if not tok:
            i += 1
            continue
        status, path = tok[:2], tok[3:]
        paths.append(path)
        if status[0] in ("R", "C"):
            i += 1  # campo extra: caminho de origem do rename/copy
            if i < len(tokens) and tokens[i]:
                paths.append(tokens[i])
        i += 1
    return paths


def quiet_violated(repo: Path, paths: list[str], window_min: int) -> bool:
    """True se algum arquivo sujo foi modificado dentro da janela quieta — alguem
    esta trabalhando AGORA. Arquivo deletado nao tem mtime e nao conta."""
    if window_min <= 0:
        return False
    threshold = time.time() - window_min * 60
    for p in paths:
        try:
            if (repo / p).stat().st_mtime > threshold:
                return True
        except OSError:
            continue
    return False


def sanity_block(repo: Path, cfg: dict, rep: Report) -> str | None:
    """Estagio 1.2 do SPEC: retorna o motivo do bloqueio, ou None para seguir."""
    if not cfg["enabled"]:
        return "enabled: false no marcador (kill-switch local)"
    gitdir = repo / ".git"
    for marker, label in [
        ("MERGE_HEAD", "merge em andamento"),
        ("rebase-merge", "rebase em andamento"),
        ("rebase-apply", "rebase/am em andamento"),
        ("CHERRY_PICK_HEAD", "cherry-pick em andamento"),
        ("BISECT_LOG", "bisect em andamento"),
    ]:
        if (gitdir / marker).exists():
            return label
    branch = git(repo, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip()
    if not branch:
        return "detached HEAD"
    if cfg["branch_only"] and branch != cfg["branch_only"]:
        return f"branch atual ({branch}) fora de branch_only ({cfg['branch_only']})"
    if git(repo, "diff", "--name-only", "--diff-filter=U").stdout.strip():
        return "conflito nao resolvido no indice"
    return None


def staged_files(repo: Path, cfg_extra: list[str]) -> list[tuple[str, str]]:
    """[(status, path)] do indice, NUL-separado."""
    out = git(repo, "diff", "--cached", "--name-status", "-z", cfg=cfg_extra).stdout
    tokens = [t for t in out.split("\0")]
    files: list[tuple[str, str]] = []
    i = 0
    while i < len(tokens):
        status = tokens[i]
        if not status:
            i += 1
            continue
        if status[0] in ("R", "C"):
            # origem em i+1, destino em i+2 — o destino e o que esta staged
            if i + 2 < len(tokens):
                files.append((status[0], tokens[i + 2]))
            i += 3
        else:
            if i + 1 < len(tokens):
                files.append((status[0], tokens[i + 1]))
            i += 2
    return files


def added_lines(repo: Path, path: str, cfg_extra: list[str]) -> str:
    """Linhas adicionadas (staged) de um arquivo — so o que ESTE commit publicaria.
    Segredo antigo ja commitado nao bloqueia arquivo para sempre."""
    out = git(repo, "diff", "--cached", "-U0", "--", path, cfg=cfg_extra).stdout
    return "\n".join(l[1:] for l in out.splitlines()
                     if l.startswith("+") and not l.startswith("+++"))


def is_binary_staged(repo: Path, path: str, cfg_extra: list[str]) -> bool:
    out = git(repo, "diff", "--cached", "--numstat", "--", path, cfg=cfg_extra).stdout
    return out.startswith("-\t-\t")


def secret_sweep(repo: Path, cfg_extra: list[str], rep: Report) -> list[str]:
    """Estagio 1.6: retorna os arquivos suspeitos de segredo.

    ADR-012 (supera o ADR-005): achou um, a arvore INTEIRA fica para tras. Antes o
    arquivo era des-stageado e o resto commitava — e isso publicava **meia entrega**
    sem nada acusar. Medido no SHVIA-WEB 2.92.0: dos 49 arquivos, 7 ficaram fora, e
    entre eles a migration cujos consumidores entraram. HEAD nao-deployavel.

    O relatorio nomeia ARQUIVO e REGRA porque "abortei" sem isso devolve o problema
    ao humano sem a informacao para resolve-lo.
    """
    offenders: list[str] = []
    for status, path in staged_files(repo, cfg_extra):
        if status == "D":
            continue  # delecao nao publica conteudo novo
        reasons: list[str] = []
        if is_sensitive_path(path):
            reasons.append("caminho sensivel")
        elif not is_binary_staged(repo, path, cfg_extra):
            reasons.extend(scan_text(added_lines(repo, path, cfg_extra)))
        if reasons:
            offenders.append(path)
            rep.add(f"SEGREDO SUSPEITO em {path} ({', '.join(reasons)})")
    return offenders


def changelog_paths(repo: Path, cfg: dict) -> list[str]:
    """Arquivos onde procurar a entrada de changelog, na ordem de preferencia."""
    named = cfg.get("changelog_file")
    if named:
        return [str(named)]
    return [c for c in CHANGELOG_CANDIDATES if (repo / c).is_file()]


def extract_message(repo: Path, cfg_extra: list[str],
                    cfg: dict) -> tuple[str | None, str | None]:
    """Estagio 1.7 caminho deterministico. Retorna (mensagem, versao_detectada).

    mensagem != None  → entrada de changelog com titulo no diff staged de um dos
                        arquivos de changelog: e a mensagem do commit.
    mensagem == None  → sem entrada com titulo. versao_detectada indica se ao menos
                        houve bump de numero no version.md (caso SHVIA-WEB) — de
                        todo jeito o caso e do fallback (F3).

    A entrada NAO precisa estar no `version.md`: procuramos tambem em `CHANGELOG.md`
    e `docs/VERSION.md`. Isso deixa um repo cujo `version.md` e lido em runtime
    (`trim(file_get_contents())`) virar deterministico so criando um arquivo novo,
    sem tocar no parser de producao."""
    names = {p for _, p in staged_files(repo, cfg_extra)}
    version_only: str | None = None

    for candidate in changelog_paths(repo, cfg):
        if candidate not in names:
            continue
        diff = git(repo, "diff", "--cached", "-U0", "--", candidate,
                   cfg=cfg_extra).stdout
        for line in diff.splitlines():
            m = CHANGELOG_ENTRY.match(line)
            if m:
                return f"{m.group(1)} - {m.group(2)}", m.group(1)
            if candidate == "version.md" and version_only is None:
                v = VERSION_ONLY.match(line)
                if v:
                    version_only = v.group(1)
    return None, version_only


def version_reused(repo: Path, message: str) -> str | None:
    """Estagio 1.75 — trava de versao REUTILIZADA.

    Caso real (01/08/2026): sessoes paralelas + fallback produziram dois
    `0.5.4` no SHVIA-MOBILE e dois `1.1.11` no SHVIA-DESKTOP — o version.md
    nao tinha sido bumpado desde o commit anterior e a mensagem saiu com a
    mesma versao. Historico com versao repetida quebra `git log --grep` como
    indice e mente sobre o que cada versao contem.

    Se o assunto comeca com `X.Y.Z - ` e o historico da branch ja tem commit
    com o MESMO prefixo de versao, recusamos: postura identica ao fallback sem
    changelog — aborta e espera um humano/agente bumpar. Retorna o sha
    conflitante, ou None se a versao e inedita."""
    m = re.match(r"^(\d+\.\d+\.\d+) - ", message)
    if not m:
        return None
    version = m.group(1)
    pattern = "^" + version.replace(".", r"\.") + " - "
    r = git(repo, "log", "--grep", pattern, "--format=%h %s", "-n", "5")
    for line in r.stdout.splitlines():
        sha, _, subject = line.partition(" ")
        if subject.startswith(f"{version} - "):
            return sha
    return None


def release(repo: Path, cfg: dict, rep: Report, dry: bool) -> None:
    """Estagio 1.11. Roda SO depois de um push que deu certo.

    Motivo de rodar aqui e nao apos o commit: uma Release aponta para um commit
    que precisa existir NO REMOTO. Tag criada sobre commit local que nunca subiu
    e uma promessa que o GitHub nao consegue cumprir.

    A skill NAO decide versao — ela copia o numero que o agente ja escreveu no
    `version.md` (o ADR-002 continua inteiro). Falha aqui NUNCA e fatal: o
    workflow `release.yml` do proprio repo e a segunda rede, e os dois guardam
    pela mesma pergunta ("a tag ja existe?"), entao quem chegar primeiro ganha.
    """
    if not cfg["release"]:
        rep.add("release: off no marcador")
        return
    version = repo_current_version(repo)
    if not version:
        rep.add("release: sem semver no version.md — nada a publicar")
        return
    if dry:
        rep.add(f"dry-run: publicaria a Release {version}")
        return

    script = repo / "tools" / "release.sh"
    if script.is_file() and os.access(script, os.X_OK):
        # Caminho preferido: a implementacao unica da casa, que tira as notas da
        # secao do CHANGELOG. Duas copias de uma regra e como uma regra passa a
        # ter duas versoes, uma errada.
        r = subprocess.run([str(script), "--current", "-q"], cwd=str(repo),
                           capture_output=True, text=True)
    else:
        # Sem o script no repo: o minimo que ainda entrega a Release.
        if git(repo, "rev-parse", "--verify", "--quiet",
               f"refs/tags/{version}").returncode == 0:
            rep.add(f"release {version}: tag ja existe")
            return
        r = subprocess.run(
            ["gh", "release", "create", version, "--title", version,
             "--target", git(repo, "rev-parse", "HEAD").stdout.strip(),
             "--generate-notes", "--latest"],
            cwd=str(repo), capture_output=True, text=True)

    if r.returncode == 0:
        rep.add(f"release {version} OK")
    else:
        err = (r.stderr or r.stdout or "").strip().splitlines()
        rep.add(f"release {version} FALHOU (nao fatal — o workflow pega): "
                f"{err[-1] if err else 'sem detalhe'}")


def push(repo: Path, branch: str, cfg: dict, cfg_extra: list[str],
         st: dict, rep: Report, dry: bool) -> None:
    """Estagio 1.9. Falha nao e fatal; 3 seguidas param de tentar (ADR-006)."""
    if not cfg["push"]:
        rep.add("push: off no marcador — commit fica local")
        return
    if int(st.get("push_fails", 0)) >= FF_FAILS_LIMIT:
        rep.add(f"push SUSPENSO apos {FF_FAILS_LIMIT} falhas seguidas — requer humano "
                "(resolva e zere apagando o estado ou pushe manualmente)")
        return
    url = git(repo, "remote", "get-url", "origin").stdout.strip()
    if not url:
        rep.add("sem remote origin — commit fica local")
        return
    extra = list(cfg_extra)
    if cfg["credential_bridge"] == "gh" or (
            cfg["credential_bridge"] == "auto" and url.startswith("http")):
        extra = GH_BRIDGE_CFG + extra
    if dry:
        rep.add(f"dry-run: pusharia {branch} para {url}")
        release(repo, cfg, rep, dry)
        return
    r = git(repo, "push", "origin", branch, cfg=extra)
    if r.returncode == 0:
        st["push_fails"] = 0
        rep.add(f"push OK ({branch})")
        release(repo, cfg, rep, dry)
    else:
        st["push_fails"] = int(st.get("push_fails", 0)) + 1
        err = (r.stderr or "").strip().splitlines()
        rep.add(f"push FALHOU ({st['push_fails']}/{FF_FAILS_LIMIT}) — commit local "
                f"mantido; retenta no proximo ciclo. {err[-1] if err else ''}")


def acquire_lock(name: str) -> Path | None:
    locks = state_dir() / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    lock = locks / f"{name}.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            if time.time() - lock.stat().st_mtime > LOCK_STALE_S:
                lock.unlink(missing_ok=True)  # stale de processo morto
                return acquire_lock(name)
        except OSError:
            pass
        return None
    with os.fdopen(fd, "w") as f:
        f.write(f"{os.getpid()} {int(time.time())}\n")
    return lock


def cycle(repo: Path, args: argparse.Namespace, state: dict) -> Report:
    rep = Report(repo.name)
    st = state.setdefault(slug(repo), {})

    marker = repo / MARKER
    if not marker.is_file():
        return rep  # invisivel por construcao (ADR-004): nem linha de log

    try:
        cfg = parse_marker(marker)
    except (ValueError, OSError) as exc:
        rep.add(f"marcador invalido — nada feito (fail-closed): {exc}")
        return rep

    if args.quiet_min is not None:
        cfg["quiet_window_min"] = args.quiet_min

    blocked = sanity_block(repo, cfg, rep)
    if blocked:
        rep.add(f"no-op: {blocked}")
        return rep

    skips = list(cfg["skip_paths"])
    paths = [p for p in dirty_paths(repo) if not is_skipped(p, skips)]
    st["last_checked"] = int(time.time())
    if not paths:
        # Arvore limpa — ou suja **so** onde o marcador diz que o dono e outro
        # (ADR-011): no-op silencioso dos dois jeitos. Silencioso e o ponto: um
        # `.dashproject/pending` reescrito pelo hook a cada commit renderia uma
        # linha de log a cada ciclo de cron, para sempre.
        return rep

    if quiet_violated(repo, paths, int(cfg["quiet_window_min"])):
        rep.add(f"adiado: modificacao ha menos de {cfg['quiet_window_min']} min "
                "(janela quieta — alguem trabalhando agora)")
        return rep

    lock = acquire_lock(slug(repo))
    if lock is None:
        return rep  # disparo concorrente desiste em silencio (ADR-003)

    cfg_extra = LFS_BYPASS_CFG if cfg["lfs_bypass"] else []
    try:
        branch = git(repo, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip()
        exclude = [f":(exclude){p}" for p in skips]
        git(repo, "add", "-A", *(["--", *exclude] if exclude else []), cfg=cfg_extra)
        if skips:
            # O pathspec impede a ENTRADA; isto trata o que ja estava no indice antes
            # do ciclo — tipicamente a skill dona tendo feito `git add` e morrido
            # antes do commit. Des-stagea so o que existe, para o pathspec sempre
            # casar algo.
            stray = [p for _, p in staged_files(repo, cfg_extra) if is_skipped(p, skips)]
            if stray:
                git(repo, "restore", "--staged", "--", *stray, cfg=cfg_extra)

        # ADR-012: suspeita de segredo ABORTA a arvore inteira. Nunca "commita o
        # resto" — commit parcial por decisao de scanner publica meia entrega, e
        # migration separada do consumidor deixa HEAD nao-deployavel.
        blocked_files = secret_sweep(repo, cfg_extra, rep)
        if blocked_files:
            rep.add(f"ABORTADO: {len(blocked_files)} arquivo(s) com suspeita de segredo. "
                    "NADA foi commitado — a arvore fica intocada, do jeito que estava. "
                    "Trate o(s) arquivo(s) acima (ou, se for falso positivo, commite a "
                    "mao) e o ciclo seguinte leva a entrega inteira.")
            git(repo, "reset", "-q")
            return rep

        if not staged_files(repo, cfg_extra):
            rep.add("nada a commitar")
            git(repo, "reset", "-q")
            return rep

        message, version_seen = extract_message(repo, cfg_extra, cfg)
        used_fallback = False
        if message is None:
            # ADR-002: sem entrada de changelog com titulo, o caso e do fallback
            # (F3). Que NUNCA inventa: versao vem do version.md do repo, e sem
            # version.md nao ha formato da casa — o repo espera um humano.
            detail = (f"version.md bumpado para {version_seen} mas sem entrada de "
                      "changelog com titulo" if version_seen
                      else "version.md sem mudanca")
            if cfg["fallback"] in (None, "off"):
                rep.add(f"fallback necessario ({detail}) mas fallback: off no "
                        "marcador — stage desfeito, arvore intocada")
                git(repo, "reset", "-q")
                return rep
            version = version_seen or repo_current_version(repo)
            if not version:
                rep.add(f"fallback necessario ({detail}) mas o repo nao tem "
                        "version.md legivel — sem formato da casa, sem commit")
                git(repo, "reset", "-q")
                return rep
            stat = git(repo, "diff", "--cached", "--stat", cfg=cfg_extra).stdout
            diff = git(repo, "diff", "--cached", cfg=cfg_extra).stdout

            # BACKOFF POR ARVORE INALTERADA. Sem isto, um repo cujo fallback falha
            # (ABORT, saida rejeitada, modelo fora do ar) e reinvocado a CADA ciclo
            # sobre o MESMO diff: ~26 tentativas por dia, que esgotam o teto e
            # deixam todos os outros repos sem fallback. Se a arvore nao mudou desde
            # a ultima falha, nem tentamos — o resultado seria o mesmo.
            tree_id = hashlib.sha1(diff.encode("utf-8", "replace")).hexdigest()[:16]
            if st.get("fallback_failed_tree") == tree_id:
                rep.add(f"fallback ja falhou nesta arvore ({st.get('fallback_failed_why', '?')}) "
                        "— nao reinvoca ate a arvore mudar (backoff). "
                        "Resolva no repo ou escreva a entrada de changelog")
                git(repo, "reset", "-q")
                return rep

            if args.dry_run:
                rep.add(f"dry-run: invocaria o fallback ({detail}; "
                        f"versao {version}, modelo {cfg['fallback']})")
                git(repo, "reset", "-q")
                return rep
            message, why, falha_do_diff = fb.generate_message(
                version, stat, diff, str(cfg["fallback"]), state,
                state_dir() / "sandbox", repo_state=st)
            if message is None:
                # So memoriza quando o modelo VIU o diff e falhou nele. Teto, rede,
                # CLI ausente e auth sao transitorios — memorizar viraria bloqueio
                # permanente por problema passageiro.
                if falha_do_diff:
                    st["fallback_failed_tree"] = tree_id
                    st["fallback_failed_why"] = why
                rep.add(f"fallback nao produziu mensagem ({why}) — {detail}; "
                        "stage desfeito, arvore intocada")
                git(repo, "reset", "-q")
                return rep
            st.pop("fallback_failed_tree", None)
            st.pop("fallback_failed_why", None)
            used_fallback = True
            rep.add(f"mensagem via fallback {cfg['fallback']}: {message}")

        dup = version_reused(repo, message)
        if dup:
            rep.add(f"versao REUTILIZADA: {dup} ja usa a versao do assunto "
                    f"({message.split(' - ', 1)[0]}) — commit recusado; bumpe o "
                    "version.md (com a entrada de changelog) para versao inedita. "
                    "Stage desfeito, arvore intocada")
            git(repo, "reset", "-q")
            return rep

        n_files = len(staged_files(repo, cfg_extra))
        if args.dry_run:
            rep.add(f"dry-run: commitaria {n_files} arquivo(s) com: {message!r}")
            git(repo, "reset", "-q")
            return rep

        trailer = f"Committed-By: committer/{skill_version()}"
        if used_fallback:
            trailer += (" (fallback " + str(cfg["fallback"]) + ")\n"
                        "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>")
        r = git(repo, "commit", "-m", message, "-m", trailer, cfg=cfg_extra)
        if r.returncode != 0:
            rep.add(f"commit FALHOU: {(r.stderr or r.stdout).strip().splitlines()[-1]}")
            git(repo, "reset", "-q")
            return rep
        sha = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
        st.update(last_commit=sha, last_message=message)
        rep.add(f"commit {sha} ({n_files} arquivo(s)): {message}")

        push(repo, branch, cfg, cfg_extra, st, rep, args.dry_run)
    finally:
        lock.unlink(missing_ok=True)
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description="Um ciclo do COMMITTER (SPEC.md §1).")
    ap.add_argument("repos", nargs="+", type=Path,
                    help="repositorios candidatos (so os com .committer.yml participam)")
    ap.add_argument("--dry-run", action="store_true",
                    help="tudo menos commit/push; imprime o que faria e desfaz o stage")
    ap.add_argument("--quiet-min", type=int, default=None, metavar="N",
                    help="override da janela quieta (uso manual/teste; 0 desliga)")
    args = ap.parse_args()

    sdir = state_dir()
    sdir.mkdir(parents=True, exist_ok=True)
    state_file = sdir / "state.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    for repo in args.repos:
        if not (repo / ".git").exists():
            print(f"[{repo.name}] ignorado: nao e um repositorio git")
            continue
        try:
            rep = cycle(repo.resolve(), args, state)
        except Exception as exc:  # noqa: BLE001 — um repo nunca derruba os outros
            print(f"[{repo.name}] ERRO inesperado: {type(exc).__name__}: {exc}")
            continue
        for line in rep.lines:
            print(f"{stamp} {line}")

    try:
        state_file.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n",
                              encoding="utf-8")
    except OSError as exc:
        print(f"[state] aviso: nao consegui gravar {state_file}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
