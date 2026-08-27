#!/usr/bin/env python3
"""Testes do ciclo do COMMITTER — regra de aceite herdada do AUDITOR: cada controle
e testado nos DOIS sentidos (o que bloqueia e o que deixa passar), e a suite foi
verificada por mutacao (neutralizar o scan de segredo derruba os testes de T-01).

Roda o script como subprocesso real contra repos git de verdade em tmpdir, com
XDG_STATE_HOME isolado por teste — o contrato testado e o de linha de comando, o
mesmo que o cron usa.

⚠️ Nenhum valor com formato de credencial real aparece literalmente aqui: as
amostras sao montadas por concatenacao (push protection + regra da casa).

    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skill" / "committer" / "committer_cycle.py"


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)


class CycleCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state_home = self.root / "xdg-state"
        self.repo = self.root / "alvo"
        self.repo.mkdir()
        sh(self.repo, "git", "init", "-q", "-b", "master")
        sh(self.repo, "git", "config", "user.name", "Teste")
        sh(self.repo, "git", "config", "user.email", "teste@example.invalid")
        (self.repo / "README.md").write_text("# alvo\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-q", "-m", "0.0.1 - Nasce o fixture")

    # ── helpers ──────────────────────────────────────────────────────────

    def marker(self, extra: str = "") -> None:
        (self.repo / ".committer.yml").write_text("enabled: true\npush: false\n" + extra)
        sh(self.repo, "git", "add", ".committer.yml")
        sh(self.repo, "git", "commit", "-q", "-m", "0.0.1 - Entra no committer")

    def age(self, *names: str, minutes: int = 30) -> None:
        """Empurra o mtime para tras — sai da janela quieta."""
        past = time.time() - minutes * 60
        for name in names:
            os.utime(self.repo / name, (past, past))

    def write_entrega(self, version: str = "1.2.0",
                      title: str = "Fecha o parser do intervalo") -> None:
        (self.repo / "app.py").write_text("intervalo = '30m'\n")
        (self.repo / "version.md").write_text(
            f"# Versão\n\n**Versão atual:** `{version}`\n\n## Changelog\n\n"
            f"### `{version}` — 2026-07-29 — {title}\n\n- detalhe\n"
        )
        self.age("app.py", "version.md")

    def run_cycle(self, *flags: str, repo: Path | None = None) -> subprocess.CompletedProcess:
        # COMMITTER_FALLBACK_CMD=false: guarda-corpo — NENHUM teste desta suite
        # pode invocar modelo real (custo, rede, flakiness). O fallback "quebra
        # rapido" e o ciclo reporta indisponibilidade. Integracao do fallback com
        # fakes: tests/test_fallback.py.
        env = dict(os.environ, XDG_STATE_HOME=str(self.state_home),
                   COMMITTER_FALLBACK_CMD="false")
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(repo or self.repo), *flags],
            capture_output=True, text=True, env=env,
        )

    def head_subject(self) -> str:
        return sh(self.repo, "git", "log", "-1", "--format=%s").stdout.strip()

    def commit_count(self) -> int:
        return int(sh(self.repo, "git", "rev-list", "--count", "HEAD").stdout)

    # ── ADR-004: opt-in por marcador ─────────────────────────────────────

    def test_repo_sem_marcador_e_invisivel(self) -> None:
        (self.repo / "solto.txt").write_text("x")
        self.age("solto.txt")
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertEqual(got.returncode, 0)
        self.assertEqual(self.commit_count(), before, "commitou sem opt-in")
        self.assertNotIn("solto", got.stdout)

    def test_enabled_false_e_killswitch(self) -> None:
        self.marker("")
        (self.repo / ".committer.yml").write_text("enabled: false\n")
        self.write_entrega()
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("kill-switch", got.stdout)
        self.assertEqual(self.commit_count(), before)

    def test_chave_desconhecida_no_marcador_falha_fechado(self) -> None:
        self.marker("")
        (self.repo / ".committer.yml").write_text("enabled: true\nenbled: true\n")
        self.write_entrega()
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("marcador invalido", got.stdout)
        self.assertEqual(self.commit_count(), before)

    # ── SPEC 1.2/1.3/1.4: sanidade, no-op, janela ────────────────────────

    def test_arvore_limpa_e_noop_silencioso(self) -> None:
        self.marker()
        got = self.run_cycle("--quiet-min", "0")
        self.assertEqual(got.stdout.strip(), "", f"no-op deveria ser mudo: {got.stdout!r}")

    def test_janela_quieta_adia(self) -> None:
        self.marker()
        (self.repo / "quente.txt").write_text("agora")  # mtime = agora
        before = self.commit_count()
        got = self.run_cycle()  # janela default de 5 min ativa
        self.assertIn("janela quieta", got.stdout)
        self.assertEqual(self.commit_count(), before)

    def test_merge_em_andamento_aborta(self) -> None:
        self.marker()
        self.write_entrega()
        (self.repo / ".git" / "MERGE_HEAD").write_text("deadbeef\n")
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("merge em andamento", got.stdout)

    def test_detached_head_aborta(self) -> None:
        self.marker()
        sha = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()
        sh(self.repo, "git", "checkout", "-q", sha)
        self.write_entrega()
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("detached", got.stdout)

    def test_branch_only_pula_outra_branch(self) -> None:
        self.marker("branch_only: master\n")
        sh(self.repo, "git", "checkout", "-q", "-b", "experimento")
        self.write_entrega()
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("branch_only", got.stdout)
        self.assertEqual(self.commit_count(), before)

    # ── ADR-002: mensagem changelog-first, nunca inventa ─────────────────

    def test_entrega_com_changelog_vira_commit_deterministico(self) -> None:
        self.marker()
        self.write_entrega("1.2.0", "Fecha o parser do intervalo")
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("commit", got.stdout)
        self.assertEqual(self.head_subject(), "1.2.0 - Fecha o parser do intervalo")
        body = sh(self.repo, "git", "log", "-1", "--format=%b").stdout
        self.assertIn("Committed-By: committer/", body, "trailer de auditoria ausente")
        status = sh(self.repo, "git", "status", "--porcelain").stdout
        self.assertEqual(status.strip(), "", "arvore deveria terminar limpa")

    def test_duas_entradas_novas_usa_a_do_topo(self) -> None:
        self.marker()
        (self.repo / "app.py").write_text("x = 1\n")
        (self.repo / "version.md").write_text(
            "**Versão atual:** `1.3.0`\n\n"
            "### `1.3.0` — 2026-07-29 — Entrega de cima\n\n"
            "### `1.2.9` — 2026-07-29 — Entrega de baixo\n"
        )
        self.age("app.py", "version.md")
        self.run_cycle("--quiet-min", "0")
        self.assertEqual(self.head_subject(), "1.3.0 - Entrega de cima")

    # ── SPEC §1.75: trava de versao reutilizada ──────────────────────────

    def test_versao_reutilizada_e_recusada(self) -> None:
        """Caso real de 01/08 (dois 0.5.4 no SHVIA-MOBILE): entrega nova com
        entrada de changelog nova mas SEM bump — a versao do assunto ja existe
        no historico → recusa, stage desfeito, arvore segue suja."""
        self.marker()
        self.write_entrega("1.2.0", "Primeira entrega")
        self.run_cycle("--quiet-min", "0")
        self.assertEqual(self.head_subject(), "1.2.0 - Primeira entrega")
        before = self.commit_count()

        (self.repo / "app.py").write_text("intervalo = '45m'\n")
        (self.repo / "version.md").write_text(
            "**Versão atual:** `1.2.0`\n\n"
            "### `1.2.0` — 2026-08-01 — Segunda entrega sem bump\n"
        )
        self.age("app.py", "version.md")
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("REUTILIZADA", got.stdout)
        self.assertEqual(self.commit_count(), before, "nao deveria commitar")
        staged = sh(self.repo, "git", "diff", "--cached", "--name-only").stdout
        self.assertEqual(staged.strip(), "", "stage deveria ter sido desfeito")
        status = sh(self.repo, "git", "status", "--porcelain").stdout
        self.assertNotEqual(status.strip(), "", "arvore deveria seguir suja")

    def test_bump_depois_da_recusa_passa(self) -> None:
        """O outro sentido: mesma entrega, versao INEDITA → commit normal."""
        self.marker()
        self.write_entrega("1.2.0", "Primeira entrega")
        self.run_cycle("--quiet-min", "0")
        (self.repo / "app.py").write_text("intervalo = '45m'\n")
        (self.repo / "version.md").write_text(
            "**Versão atual:** `1.2.1`\n\n"
            "### `1.2.1` — 2026-08-01 — Segunda entrega com bump\n"
        )
        self.age("app.py", "version.md")
        got = self.run_cycle("--quiet-min", "0")
        self.assertNotIn("REUTILIZADA", got.stdout)
        self.assertEqual(self.head_subject(), "1.2.1 - Segunda entrega com bump")

    def test_bump_sem_titulo_com_fallback_off_nao_commita(self) -> None:
        """Formato SHVIA-WEB: version.md so com numero → caso do fallback. Com
        fallback: off (modo vigia), NADA e commitado e o stage e desfeito."""
        self.marker("fallback: off\n")
        (self.repo / "version.md").write_text("2.88.6\n")
        (self.repo / "app.py").write_text("y = 2\n")
        self.age("version.md", "app.py")
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("fallback: off", got.stdout)
        self.assertIn("2.88.6", got.stdout, "deveria reportar a versao detectada")
        self.assertEqual(self.commit_count(), before)
        staged = sh(self.repo, "git", "diff", "--cached", "--name-only").stdout
        self.assertEqual(staged.strip(), "", "stage deveria ter sido desfeito")

    def test_fallback_indisponivel_nao_commita(self) -> None:
        """Fallback ligado mas quebrado (CMD falha): indisponibilidade NUNCA vira
        commit — o repo espera o proximo ciclo."""
        self.marker()
        (self.repo / "version.md").write_text("0.0.1\n")
        sh(self.repo, "git", "add", "version.md")
        sh(self.repo, "git", "commit", "-q", "-m", "0.0.1 - version.md do fixture")
        (self.repo / "app.py").write_text("z = 3\n")
        self.age("app.py")
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("fallback nao produziu mensagem", got.stdout)
        self.assertEqual(self.commit_count(), before)

    def test_repo_sem_version_md_nao_commita(self) -> None:
        """Sem version.md nao ha formato da casa — nem o fallback e invocado."""
        self.marker()
        (self.repo / "app.py").write_text("w = 4\n")
        self.age("app.py")
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("nao tem version.md", got.stdout)
        self.assertEqual(self.commit_count(), before)

    # ── ADR-012 / T-01: segredo → ABORTA a arvore inteira ────────────────

    def test_segredo_plantado_ABORTA_a_entrega_inteira(self) -> None:
        """ADR-012. O teste anterior exigia o oposto — que o resto entrasse — e era
        exatamente o defeito: meia entrega publicada sem nada acusar."""
        self.marker()
        self.write_entrega("1.4.0", "Entrega limpa")
        vazado = "AKIA" + "Q" * 16  # montado por concatenacao de proposito
        (self.repo / "config_novo.py").write_text(f'aws = "{vazado}"\n')
        (self.repo / "companheiro.py").write_text("x = 1\n")
        self.age("config_novo.py")
        self.age("companheiro.py")
        before = self.commit_count()

        got = self.run_cycle("--quiet-min", "0")

        # Nomeia ARQUIVO e REGRA: "abortei" sem isso devolve o problema sem a
        # informacao para resolve-lo.
        self.assertIn("SEGREDO SUSPEITO", got.stdout)
        self.assertIn("config_novo.py", got.stdout)
        self.assertIn("aws-access-key", got.stdout)
        self.assertIn("ABORTADO", got.stdout)

        # NADA commitado — nem o companheiro inocente, nem a entrega.
        self.assertEqual(self.commit_count(), before, "commitou apesar do segredo")
        status = sh(self.repo, "git", "status", "--porcelain").stdout
        self.assertIn("config_novo.py", status, "a arvore deveria seguir intocada")
        self.assertIn("companheiro.py", status, "o companheiro nao pode ter sido levado")

    def test_caminho_sensivel_aborta_mesmo_sem_conteudo_suspeito(self) -> None:
        self.marker()
        self.write_entrega("1.5.0", "Outra entrega")
        (self.repo / "deploy_key.pem").write_text("nem parece chave\n")
        self.age("deploy_key.pem")
        before = self.commit_count()

        got = self.run_cycle("--quiet-min", "0")

        self.assertIn("caminho sensivel", got.stdout)
        self.assertIn("ABORTADO", got.stdout)
        self.assertEqual(self.commit_count(), before)

    def test_env_example_NAO_e_caminho_sensivel(self) -> None:
        """ADR-012, a metade que impede a paralisia.

        `\\.env\\..*$` casa `.env.example`, que e versionado por convencao em
        metade da casa. Com o abort, deixa-lo na regra de caminho travaria todo
        commit de quem encostasse no template. A regra de CONTEUDO segue valendo —
        e o proximo teste prova."""
        self.marker()
        self.write_entrega("1.6.0", "Mexe no template de env")
        (self.repo / ".env.example").write_text("APP_NAME=\nDB_HOST=\n")
        self.age(".env.example")

        got = self.run_cycle("--quiet-min", "0")

        self.assertNotIn("SEGREDO SUSPEITO", got.stdout)
        self.assertNotIn("ABORTADO", got.stdout)
        self.assertEqual(self.head_subject(), "1.6.0 - Mexe no template de env")
        committed = sh(self.repo, "git", "show", "--name-only", "--format=", "HEAD").stdout
        self.assertIn(".env.example", committed)

    def test_env_example_COM_segredo_de_verdade_ainda_aborta(self) -> None:
        """A regra de conteudo e a que importa num template: o dia em que alguem
        colar a chave real ali, o caminho ter saido da lista nao pode salvar."""
        self.marker()
        self.write_entrega("1.7.0", "Template com chave colada por engano")
        vazado = "AKIA" + "Z" * 16
        # Chave e atribuicao montadas por CONCATENACAO, como o resto deste arquivo:
        # escrita literal, a linha faria o scan acusar o proprio arquivo de teste — e
        # com o ADR-012 isso nao amputaria o teste, travaria a entrega inteira.
        linha = "AWS_ACCESS" + "_KEY_ID" + "=" + vazado
        (self.repo / ".env.example").write_text(f"APP_NAME=\n{linha}\n")
        self.age(".env.example")
        before = self.commit_count()

        got = self.run_cycle("--quiet-min", "0")

        self.assertIn("SEGREDO SUSPEITO", got.stdout)
        self.assertIn(".env.example", got.stdout)
        self.assertIn("ABORTADO", got.stdout)
        self.assertEqual(self.commit_count(), before)

    def test_codigo_de_parser_nao_e_falso_positivo(self) -> None:
        """Regressao do dogfood de 29/07: `tokens = out.split(...)` marcava o
        proprio committer_cycle.py como segredo e o excluiria para sempre."""
        self.marker()
        self.write_entrega("1.4.5", "Entrega com parser junto")
        (self.repo / "parser.py").write_text(
            'tokens = out.split("\\0")\ntoken = parse_line(raw)\n'
        )
        self.age("parser.py")
        got = self.run_cycle("--quiet-min", "0")
        self.assertNotIn("SEGREDO SUSPEITO", got.stdout)
        committed = sh(self.repo, "git", "show", "--name-only", "--format=", "HEAD").stdout
        self.assertIn("parser.py", committed, "parser.py deveria ter entrado no commit")

    def test_so_segredo_nada_a_commitar(self) -> None:
        self.marker()
        vazado = "ghp_" + "A1b2C3d4E5f6G7h8" + "A1b2C3d4"
        (self.repo / "token.txt").write_text(vazado + "\n")
        self.age("token.txt")
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("ABORTADO", got.stdout)
        self.assertEqual(self.commit_count(), before)

    # ── ADR-006: push nao-fatal ──────────────────────────────────────────

    def test_push_falho_mantem_commit_e_conta_strike(self) -> None:
        self.marker("")  # push default true…
        (self.repo / ".committer.yml").write_text("enabled: true\npush: true\n")
        sh(self.repo, "git", "remote", "add", "origin",
           str(self.root / "nao-existe.git"))
        self.write_entrega("1.6.0", "Entrega com push quebrado")
        got = self.run_cycle("--quiet-min", "0")
        self.assertEqual(self.head_subject(), "1.6.0 - Entrega com push quebrado")
        self.assertIn("push FALHOU (1/3)", got.stdout)

    def test_push_off_fica_local(self) -> None:
        self.marker()  # push: false
        self.write_entrega("1.7.0", "Entrega local")
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("push: off", got.stdout)

    # ── ADR-003: lock ────────────────────────────────────────────────────

    def test_lock_concorrente_desiste_em_silencio(self) -> None:
        self.marker()
        self.write_entrega("1.8.0", "Nunca deve entrar")
        # forja o lock fresco que outro disparo teria criado
        import hashlib
        slug = f"{self.repo.name}-{hashlib.sha1(str(self.repo.resolve()).encode()).hexdigest()[:8]}"
        lock = self.state_home / "committer" / "locks" / f"{slug}.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("99999 0\n")
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertEqual(self.commit_count(), before)
        self.assertNotIn("commit", got.stdout)

    # ── dry-run ──────────────────────────────────────────────────────────

    def test_dry_run_preve_e_nao_toca(self) -> None:
        self.marker()
        self.write_entrega("1.9.0", "Previsao apenas")
        before = self.commit_count()
        got = self.run_cycle("--dry-run", "--quiet-min", "0")
        self.assertIn("dry-run: commitaria", got.stdout)
        self.assertIn("1.9.0 - Previsao apenas", got.stdout)
        self.assertEqual(self.commit_count(), before)
        staged = sh(self.repo, "git", "diff", "--cached", "--name-only").stdout
        self.assertEqual(staged.strip(), "")

    # ── ADR-011: skip_paths, estado de outra skill ───────────────────────

    def sujeira_de_skill(self) -> None:
        """Reproduz o que o hook do DASHPROJECT escreve DEPOIS de cada commit — a
        sujeira que reaparece sozinha e realimentava o ciclo."""
        (self.repo / ".dashproject").mkdir(exist_ok=True)
        (self.repo / ".dashproject" / "pending").write_text("pending abc123 entrega\n")
        (self.repo / ".dashproject" / "last-commit-ts").write_text("1787404703\n")

    def test_skip_paths_fica_fora_do_commit(self) -> None:
        self.marker("skip_paths: .dashproject/\n")
        self.write_entrega()
        self.sujeira_de_skill()
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("1.2.0 - Fecha o parser do intervalo", got.stdout)
        tocados = sh(self.repo, "git", "show", "--name-only", "--format=", "HEAD").stdout
        self.assertIn("app.py", tocados)
        self.assertNotIn(".dashproject", tocados, "estado de outra skill entrou no commit")
        # E continua sujo: o ciclo nao commitou NEM descartou — so nao e dele.
        # (porcelain colapsa diretorio inteiro nao rastreado em `?? .dashproject/`)
        self.assertIn(".dashproject",
                      sh(self.repo, "git", "status", "--porcelain").stdout)

    def test_sem_skip_paths_o_mesmo_caminho_entra(self) -> None:
        """Sentido contrario do anterior: sem a chave, o `add -A` leva tudo — é o
        comportamento que produzia o loop, e ele tem de continuar mensuravel."""
        self.marker()
        self.write_entrega()
        self.sujeira_de_skill()
        self.run_cycle("--quiet-min", "0")
        tocados = sh(self.repo, "git", "show", "--name-only", "--format=", "HEAD").stdout
        self.assertIn(".dashproject/pending", tocados)

    def test_sujeira_so_em_skip_paths_e_noop_silencioso(self) -> None:
        """O nucleo do loop: hook escreve `pending` depois do commit, ciclo acorda,
        acha arvore suja e commita — o que dispara o hook de novo. Aqui ele nao
        acorda, e nao imprime nada (uma linha por ciclo de cron, para sempre)."""
        self.marker("skip_paths: .dashproject/\n")
        self.sujeira_de_skill()
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertEqual(got.stdout.strip(), "", f"no-op deveria ser mudo: {got.stdout!r}")
        self.assertEqual(self.commit_count(), before)

    def test_skip_paths_nao_segura_a_janela_quieta(self) -> None:
        """`pending` tem mtime de agora a cada commit. Se ele contasse na janela
        quieta, um repo com o hook instalado ficaria adiando para sempre."""
        self.marker("skip_paths: .dashproject/\n")
        self.write_entrega()
        self.sujeira_de_skill()          # mtime = agora
        got = self.run_cycle()           # janela default de 5 min ativa
        self.assertNotIn("janela quieta", got.stdout)
        self.assertIn("1.2.0 - Fecha o parser do intervalo", got.stdout)

    def test_skip_paths_ja_staged_e_des_stageado(self) -> None:
        """A skill dona fez `git add` e morreu antes do commit: o pathspec sozinho
        nao alcanca o indice, e o caminho entraria de carona."""
        self.marker("skip_paths: .dashproject/\n")
        self.write_entrega()
        self.sujeira_de_skill()
        sh(self.repo, "git", "add", ".dashproject")
        self.run_cycle("--quiet-min", "0")
        tocados = sh(self.repo, "git", "show", "--name-only", "--format=", "HEAD").stdout
        self.assertNotIn(".dashproject", tocados)

    def test_skip_paths_com_rename_nao_vaza_a_delecao(self) -> None:
        """Rename dentro do caminho ignorado (`history/daily`, `.loop/entries`): o
        indice guarda a delecao da origem E a adicao do destino, mas
        `staged_files()` so devolve o destino. Des-stagear o que ele lista deixaria
        a DELECAO staged — o commit apagaria arquivo de outra skill. Quem fecha
        isso e o pathspec no `add`, nao a limpeza do indice."""
        self.marker("skip_paths: .dashproject/\n")
        (self.repo / ".dashproject").mkdir()
        (self.repo / ".dashproject" / "antigo.md").write_text("relatorio do dia\n")
        sh(self.repo, "git", "add", ".dashproject")
        sh(self.repo, "git", "commit", "-q", "-m", "0.0.1 - Estado da outra skill")
        (self.repo / ".dashproject" / "antigo.md").rename(
            self.repo / ".dashproject" / "novo.md")
        self.write_entrega()
        self.run_cycle("--quiet-min", "0")
        tocados = sh(self.repo, "git", "show", "--name-only", "--format=", "HEAD").stdout
        self.assertNotIn(".dashproject", tocados)
        self.assertTrue((self.repo / ".dashproject" / "novo.md").exists())

    def test_skip_paths_casa_por_segmento(self) -> None:
        """`.loop` nao pode pular `.loopback/` — prefixo cru pularia."""
        self.marker("skip_paths: .loop\n")
        self.write_entrega()
        (self.repo / ".loopback").mkdir()
        (self.repo / ".loopback" / "x.txt").write_text("vizinho de nome parecido\n")
        self.run_cycle("--quiet-min", "0")
        tocados = sh(self.repo, "git", "show", "--name-only", "--format=", "HEAD").stdout
        self.assertIn(".loopback/x.txt", tocados)

    def test_skip_paths_para_fora_do_repo_falha_fechado(self) -> None:
        """Pathspec para fora do repo derrubaria o `git add` inteiro — o ciclo
        pararia de commitar aquele repo em silencio."""
        self.marker("skip_paths: ../outro\n")
        self.write_entrega()
        before = self.commit_count()
        got = self.run_cycle("--quiet-min", "0")
        self.assertIn("marcador invalido", got.stdout)
        self.assertEqual(self.commit_count(), before)

    def test_diretorio_sem_git_e_reportado_sem_crash(self) -> None:
        naked = self.root / "pelado"
        naked.mkdir()
        got = self.run_cycle(repo=naked)
        self.assertEqual(got.returncode, 0)
        self.assertIn("nao e um repositorio git", got.stdout)


if __name__ == "__main__":
    unittest.main()
