"""Comprehensive tests for compgraph.preflight module."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from compgraph.preflight import (
    CheckResult,
    CheckStatus,
    PreflightReport,
    Severity,
    apply_fixes,
    build_parser,
    check_api_keys,
    check_git_state,
    check_process_lock,
    check_python_version,
    check_required_tools,
    check_venv_and_deps,
    format_human,
    is_op_reference,
    is_placeholder,
    main,
    parse_env_file,
    write_diagnostics,
)

# ---------------------------------------------------------------------------
# TestCheckResult
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_defaults(self):
        r = CheckResult(name="test", status=CheckStatus.PASS, severity=Severity.INFO, message="ok")
        assert r.details == {}
        assert r.fix_available is False
        assert r.fix_command is None

    def test_to_dict(self):
        r = CheckResult(
            name="test",
            status=CheckStatus.FAIL,
            severity=Severity.CRITICAL,
            message="broken",
            fix_available=True,
            fix_command="fix it",
        )
        d = r.to_dict()
        assert d["status"] == "fail"
        assert d["severity"] == "critical"
        assert d["fix_available"] is True
        assert d["fix_command"] == "fix it"

    def test_details_included_in_dict(self):
        r = CheckResult(
            name="test",
            status=CheckStatus.PASS,
            severity=Severity.INFO,
            message="ok",
            details={"key": "value"},
        )
        assert r.to_dict()["details"] == {"key": "value"}


# ---------------------------------------------------------------------------
# TestPreflightReport
# ---------------------------------------------------------------------------


class TestPreflightReport:
    def test_passed_with_no_checks(self):
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root="/tmp"
        )
        assert report.passed is True

    def test_passed_with_passing_checks(self):
        report = PreflightReport(
            timestamp="now",
            platform="test",
            python_version="3.14.0",
            project_root="/tmp",
            checks=[
                CheckResult("a", CheckStatus.PASS, Severity.CRITICAL, "ok"),
                CheckResult("b", CheckStatus.WARN, Severity.WARNING, "meh"),
            ],
        )
        assert report.passed is True

    def test_failed_with_critical_failure(self):
        report = PreflightReport(
            timestamp="now",
            platform="test",
            python_version="3.14.0",
            project_root="/tmp",
            checks=[
                CheckResult("a", CheckStatus.FAIL, Severity.CRITICAL, "bad"),
            ],
        )
        assert report.passed is False
        assert report.critical_count == 1

    def test_warning_count(self):
        report = PreflightReport(
            timestamp="now",
            platform="test",
            python_version="3.14.0",
            project_root="/tmp",
            checks=[
                CheckResult("a", CheckStatus.WARN, Severity.WARNING, "meh"),
                CheckResult("b", CheckStatus.FAIL, Severity.WARNING, "also meh"),
            ],
        )
        assert report.warning_count == 2

    def test_to_json(self):
        report = PreflightReport(
            timestamp="now",
            platform="test",
            python_version="3.14.0",
            project_root="/tmp",
            checks=[CheckResult("a", CheckStatus.PASS, Severity.INFO, "ok")],
        )
        data = json.loads(report.to_json())
        assert data["passed"] is True
        assert len(data["checks"]) == 1
        assert data["checks"][0]["name"] == "a"


# ---------------------------------------------------------------------------
# TestPythonVersion
# ---------------------------------------------------------------------------


class TestPythonVersion:
    def test_pass_satisfies(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.12"\n')
        with patch("compgraph.preflight.sys") as mock_sys:
            mock_sys.version_info = SimpleNamespace(major=3, minor=14, micro=3)
            result = check_python_version(tmp_path)
        assert result.status == CheckStatus.PASS

    def test_fail_too_old(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.12"\n')
        with patch("compgraph.preflight.sys") as mock_sys:
            mock_sys.version_info = SimpleNamespace(major=3, minor=10, micro=0)
            result = check_python_version(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert result.severity == Severity.CRITICAL

    def test_missing_pyproject(self, tmp_path: Path):
        result = check_python_version(tmp_path)
        assert result.status == CheckStatus.WARN

    def test_no_requires_python(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        result = check_python_version(tmp_path)
        assert result.status == CheckStatus.SKIP

    def test_compound_specifier(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.12,<4.0"\n')
        with patch("compgraph.preflight.sys") as mock_sys:
            mock_sys.version_info = SimpleNamespace(major=3, minor=14, micro=0)
            result = check_python_version(tmp_path)
        assert result.status == CheckStatus.PASS

    def test_compound_specifier_fail_upper(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.12,<3.14"\n')
        with patch("compgraph.preflight.sys") as mock_sys:
            mock_sys.version_info = SimpleNamespace(major=3, minor=14, micro=0)
            result = check_python_version(tmp_path)
        assert result.status == CheckStatus.FAIL

    def test_compatible_release(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = "~=3.12"\n')
        with patch("compgraph.preflight.sys") as mock_sys:
            mock_sys.version_info = SimpleNamespace(major=3, minor=14, micro=0)
            result = check_python_version(tmp_path)
        assert result.status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# TestVenvAndDeps
# ---------------------------------------------------------------------------


class TestVenvAndDeps:
    def test_missing_venv(self, tmp_path: Path):
        (tmp_path / "uv.lock").write_text("")
        result = check_venv_and_deps(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "not found" in result.message

    def test_missing_lockfile(self, tmp_path: Path):
        (tmp_path / ".venv").mkdir()
        result = check_venv_and_deps(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "uv.lock" in result.message

    @patch("compgraph.preflight._run_cmd")
    def test_deps_in_sync(self, mock_run, tmp_path: Path):
        (tmp_path / ".venv").mkdir()
        (tmp_path / "uv.lock").write_text("")
        mock_run.return_value = SimpleNamespace(
            returncode=0, stdout="Resolved 10 packages\n", stderr=""
        )
        result = check_venv_and_deps(tmp_path)
        assert result.status == CheckStatus.PASS

    @patch("compgraph.preflight._run_cmd")
    def test_deps_out_of_sync(self, mock_run, tmp_path: Path):
        (tmp_path / ".venv").mkdir()
        (tmp_path / "uv.lock").write_text("")
        mock_run.return_value = SimpleNamespace(
            returncode=0, stdout="Would install httpx 0.28.0\n", stderr=""
        )
        result = check_venv_and_deps(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert result.fix_available is True

    @patch("compgraph.preflight._run_cmd")
    def test_fix_uv_sync(self, mock_run, tmp_path: Path):
        (tmp_path / ".venv").mkdir()
        (tmp_path / "uv.lock").write_text("")
        # First call: dry-run shows out of sync
        # Second call: uv sync succeeds
        mock_run.side_effect = [
            SimpleNamespace(returncode=0, stdout="Would install httpx 0.28.0\n", stderr=""),
            SimpleNamespace(returncode=0, stdout="Installed 1 package\n", stderr=""),
        ]
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(check_venv_and_deps(tmp_path))
        actions = apply_fixes(report, tmp_path)
        assert any("uv sync" in a for a in actions)

    @patch("compgraph.preflight._run_cmd", side_effect=FileNotFoundError)
    def test_uv_not_found(self, mock_run, tmp_path: Path):
        (tmp_path / ".venv").mkdir()
        (tmp_path / "uv.lock").write_text("")
        result = check_venv_and_deps(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "uv not found" in result.message


# ---------------------------------------------------------------------------
# TestApiKeys
# ---------------------------------------------------------------------------


class TestApiKeys:
    def test_missing_env_file(self, tmp_path: Path):
        results = check_api_keys(tmp_path)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN
        assert ".env" in results[0].message

    def test_placeholder_database_url(self, tmp_path: Path):
        (tmp_path / ".env").write_text(
            "DATABASE_URL=postgresql+asyncpg://postgres:your-password@db.test.supabase.co:5432/postgres\n"
        )
        with patch("compgraph.preflight._check_gh_auth") as mock_gh:
            mock_gh.return_value = CheckResult(
                "api_keys_gh", CheckStatus.SKIP, Severity.INFO, "skip"
            )
            results = check_api_keys(tmp_path)
        db_results = [r for r in results if r.name == "api_keys_database"]
        assert len(db_results) == 1
        assert db_results[0].status == CheckStatus.FAIL

    def test_valid_database_url(self, tmp_path: Path):
        (tmp_path / ".env").write_text(
            "DATABASE_URL=postgresql+asyncpg://user:realpass@db.real.supabase.co:5432/postgres\n"
        )
        with patch("compgraph.preflight._check_gh_auth") as mock_gh:
            mock_gh.return_value = CheckResult(
                "api_keys_gh", CheckStatus.SKIP, Severity.INFO, "skip"
            )
            results = check_api_keys(tmp_path)
        db_results = [r for r in results if r.name == "api_keys_database"]
        assert len(db_results) == 1
        assert db_results[0].status == CheckStatus.PASS

    @patch("compgraph.preflight._validate_anthropic_key")
    def test_valid_anthropic_key_format(self, mock_validate, tmp_path: Path):
        mock_validate.return_value = CheckResult(
            "api_keys_anthropic", CheckStatus.PASS, Severity.WARNING, "valid"
        )
        (tmp_path / ".env").write_text(
            "DATABASE_URL=postgresql+asyncpg://user:realpass@db.real.supabase.co:5432/postgres\n"
            "ANTHROPIC_API_KEY=sk-ant-api03-real-key-here\n"
        )
        with patch("compgraph.preflight._check_gh_auth") as mock_gh:
            mock_gh.return_value = CheckResult(
                "api_keys_gh", CheckStatus.SKIP, Severity.INFO, "skip"
            )
            results = check_api_keys(tmp_path)
        anthropic_results = [r for r in results if r.name == "api_keys_anthropic"]
        assert len(anthropic_results) == 1
        assert anthropic_results[0].status == CheckStatus.PASS

    def test_invalid_anthropic_key_prefix(self, tmp_path: Path):
        (tmp_path / ".env").write_text(
            "DATABASE_URL=postgresql+asyncpg://user:realpass@db.real.supabase.co:5432/postgres\n"
            "ANTHROPIC_API_KEY=wrong-prefix-key\n"
        )
        with patch("compgraph.preflight._check_gh_auth") as mock_gh:
            mock_gh.return_value = CheckResult(
                "api_keys_gh", CheckStatus.SKIP, Severity.INFO, "skip"
            )
            results = check_api_keys(tmp_path)
        anthropic_results = [r for r in results if r.name == "api_keys_anthropic"]
        assert len(anthropic_results) == 1
        assert anthropic_results[0].status == CheckStatus.WARN
        assert "prefix" in anthropic_results[0].message

    @patch("compgraph.preflight._validate_anthropic_key")
    def test_anthropic_key_401(self, mock_validate, tmp_path: Path):
        mock_validate.return_value = CheckResult(
            "api_keys_anthropic", CheckStatus.FAIL, Severity.WARNING, "returned 401"
        )
        (tmp_path / ".env").write_text(
            "DATABASE_URL=postgresql+asyncpg://user:realpass@db.real.supabase.co:5432/postgres\n"
            "ANTHROPIC_API_KEY=sk-ant-api03-invalid\n"
        )
        with patch("compgraph.preflight._check_gh_auth") as mock_gh:
            mock_gh.return_value = CheckResult(
                "api_keys_gh", CheckStatus.SKIP, Severity.INFO, "skip"
            )
            results = check_api_keys(tmp_path)
        anthropic_results = [r for r in results if r.name == "api_keys_anthropic"]
        assert anthropic_results[0].status == CheckStatus.FAIL

    def test_op_reference_detection(self):
        assert is_op_reference("op://vault/item/field") is True
        assert is_op_reference("op://my-vault/my-item/password") is True
        assert is_op_reference("not-an-op-ref") is False
        assert is_op_reference("op://missing-parts") is False

    @patch("compgraph.preflight._run_cmd")
    @patch("compgraph.preflight.resolve_op_reference")
    @patch("shutil.which", return_value="/usr/local/bin/op")
    def test_op_reference_resolved(self, mock_which, mock_resolve, mock_run, tmp_path: Path):
        (tmp_path / ".env").write_text("DATABASE_URL=op://vault/item/db-url\n")
        # op account list succeeds
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="account", stderr="")
        mock_resolve.return_value = (
            "postgresql+asyncpg://user:realpass@db.real.supabase.co:5432/postgres",
            None,
        )
        with patch("compgraph.preflight._check_gh_auth") as mock_gh:
            mock_gh.return_value = CheckResult(
                "api_keys_gh", CheckStatus.SKIP, Severity.INFO, "skip"
            )
            results = check_api_keys(tmp_path)
        db_results = [r for r in results if r.name == "api_keys_database"]
        assert db_results[0].status == CheckStatus.PASS

    @patch("shutil.which", return_value=None)
    def test_op_required_but_missing(self, mock_which, tmp_path: Path):
        (tmp_path / ".env").write_text("DATABASE_URL=op://vault/item/field\n")
        results = check_api_keys(tmp_path)
        assert len(results) == 1
        assert results[0].status == CheckStatus.FAIL
        assert "op" in results[0].message.lower()

    def test_no_httpx_skips_validation(self, tmp_path: Path):
        """When httpx import fails, API key validation is skipped."""
        (tmp_path / ".env").write_text(
            "DATABASE_URL=postgresql+asyncpg://user:realpass@db.real.supabase.co:5432/postgres\n"
            "ANTHROPIC_API_KEY=sk-ant-api03-real-key\n"
        )
        with (
            patch("compgraph.preflight._check_gh_auth") as mock_gh,
            patch("compgraph.preflight._validate_anthropic_key") as mock_validate,
        ):
            mock_gh.return_value = CheckResult(
                "api_keys_gh", CheckStatus.SKIP, Severity.INFO, "skip"
            )
            mock_validate.return_value = CheckResult(
                "api_keys_anthropic", CheckStatus.SKIP, Severity.WARNING, "httpx not installed"
            )
            results = check_api_keys(tmp_path)
        anthropic_results = [r for r in results if r.name == "api_keys_anthropic"]
        assert anthropic_results[0].status == CheckStatus.SKIP


# ---------------------------------------------------------------------------
# TestGitState
# ---------------------------------------------------------------------------


class TestGitState:
    @patch("compgraph.preflight._run_cmd")
    def test_not_a_repo(self, mock_run, tmp_path: Path):
        mock_run.return_value = SimpleNamespace(returncode=128, stdout="", stderr="not a repo")
        result = check_git_state(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert result.severity == Severity.CRITICAL

    @patch("compgraph.preflight._run_cmd")
    def test_clean_worktree(self, mock_run, tmp_path: Path):
        mock_run.side_effect = [
            SimpleNamespace(returncode=0, stdout="true", stderr=""),  # is-inside-work-tree
            SimpleNamespace(returncode=0, stdout="main\n", stderr=""),  # branch
            SimpleNamespace(returncode=0, stdout="", stderr=""),  # status --porcelain
        ]
        result = check_git_state(tmp_path)
        assert result.status == CheckStatus.PASS
        assert "main" in result.message

    @patch("compgraph.preflight._run_cmd")
    def test_dirty_worktree(self, mock_run, tmp_path: Path):
        mock_run.side_effect = [
            SimpleNamespace(returncode=0, stdout="true", stderr=""),
            SimpleNamespace(returncode=0, stdout="main\n", stderr=""),
            SimpleNamespace(returncode=0, stdout=" M file.py\n?? new.py\n", stderr=""),
        ]
        result = check_git_state(tmp_path)
        assert result.status == CheckStatus.WARN
        assert "2" in result.message

    @patch("compgraph.preflight._run_cmd")
    def test_wrong_branch(self, mock_run, tmp_path: Path):
        mock_run.side_effect = [
            SimpleNamespace(returncode=0, stdout="true", stderr=""),
            SimpleNamespace(returncode=0, stdout="feature\n", stderr=""),
        ]
        result = check_git_state(tmp_path, expected_branch="main")
        assert result.status == CheckStatus.WARN
        assert "expected" in result.message

    @patch("compgraph.preflight._run_cmd")
    def test_expected_branch_match(self, mock_run, tmp_path: Path):
        mock_run.side_effect = [
            SimpleNamespace(returncode=0, stdout="true", stderr=""),
            SimpleNamespace(returncode=0, stdout="main\n", stderr=""),
            SimpleNamespace(returncode=0, stdout="", stderr=""),
        ]
        result = check_git_state(tmp_path, expected_branch="main")
        assert result.status == CheckStatus.PASS

    @patch("compgraph.preflight._run_cmd", side_effect=FileNotFoundError)
    def test_git_not_found(self, mock_run, tmp_path: Path):
        result = check_git_state(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "not found" in result.message


# ---------------------------------------------------------------------------
# TestProcessLock
# ---------------------------------------------------------------------------


class TestProcessLock:
    def test_no_task_skip(self, tmp_path: Path):
        result = check_process_lock(tmp_path, task_name=None)
        assert result.status == CheckStatus.SKIP

    def test_acquire_lock(self, tmp_path: Path):
        result = check_process_lock(tmp_path, task_name="test-task")
        assert result.status == CheckStatus.PASS
        lock_file = tmp_path / ".locks" / "test-task.pid"
        assert lock_file.exists()
        assert lock_file.read_text().strip() == str(os.getpid())

    def test_stale_pid(self, tmp_path: Path):
        locks_dir = tmp_path / ".locks"
        locks_dir.mkdir()
        lock_file = locks_dir / "stale-task.pid"
        lock_file.write_text("99999999")  # Very unlikely to be a real PID

        with patch("os.kill", side_effect=ProcessLookupError):
            result = check_process_lock(tmp_path, task_name="stale-task")
        assert result.status == CheckStatus.FAIL
        assert "Stale" in result.message
        assert result.fix_available is True

    def test_active_pid(self, tmp_path: Path):
        locks_dir = tmp_path / ".locks"
        locks_dir.mkdir()
        lock_file = locks_dir / "active-task.pid"
        lock_file.write_text(str(os.getpid()))  # Our own PID — definitely alive

        with patch("os.kill", return_value=None):  # No exception = process alive
            result = check_process_lock(tmp_path, task_name="active-task")
        assert result.status == CheckStatus.FAIL
        assert "already running" in result.message

    def test_corrupt_file(self, tmp_path: Path):
        locks_dir = tmp_path / ".locks"
        locks_dir.mkdir()
        lock_file = locks_dir / "corrupt-task.pid"
        lock_file.write_text("not-a-number")

        result = check_process_lock(tmp_path, task_name="corrupt-task")
        assert result.status == CheckStatus.FAIL
        assert "Corrupt" in result.message
        assert result.fix_available is True

    def test_fix_stale_lock(self, tmp_path: Path):
        locks_dir = tmp_path / ".locks"
        locks_dir.mkdir()
        lock_file = locks_dir / "stale-task.pid"
        lock_file.write_text("99999999")

        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(
            CheckResult(
                name="process_lock",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message="Stale lock for 'stale-task' (PID 99999999 is dead)",
                details={"pid": "99999999", "lock_file": str(lock_file)},
                fix_available=True,
                fix_command=f"rm {lock_file}",
            )
        )
        actions = apply_fixes(report, tmp_path)
        assert any("stale lock" in a.lower() for a in actions)
        assert not lock_file.exists()


# ---------------------------------------------------------------------------
# TestRequiredTools
# ---------------------------------------------------------------------------


class TestRequiredTools:
    @patch("shutil.which")
    def test_all_found(self, mock_which, tmp_path: Path):
        mock_which.return_value = "/usr/bin/tool"
        results = check_required_tools(tmp_path)
        assert all(r.status == CheckStatus.PASS for r in results)

    @patch("shutil.which")
    def test_missing_tool_warning(self, mock_which, tmp_path: Path):
        def which_side_effect(name):
            if name in ("git", "uv", "op"):
                return f"/usr/bin/{name}"
            return None

        mock_which.side_effect = which_side_effect
        with patch("compgraph.preflight.sys") as mock_sys:
            mock_sys.platform = "linux"
            results = check_required_tools(tmp_path)
        timeout_results = [r for r in results if "timeout" in r.name]
        assert len(timeout_results) == 1
        assert timeout_results[0].status == CheckStatus.WARN

    @patch("shutil.which")
    def test_macos_fallback_gtimeout(self, mock_which, tmp_path: Path):
        def which_side_effect(name):
            if name == "timeout":
                return None
            if name == "gtimeout":
                return "/opt/homebrew/bin/gtimeout"
            if name == "realpath":
                return None
            if name == "grealpath":
                return "/opt/homebrew/bin/grealpath"
            return f"/usr/bin/{name}"

        mock_which.side_effect = which_side_effect
        with patch("compgraph.preflight.sys") as mock_sys:
            mock_sys.platform = "darwin"
            results = check_required_tools(tmp_path)
        timeout_results = [r for r in results if "timeout" in r.name]
        assert timeout_results[0].status == CheckStatus.PASS
        assert "gtimeout" in timeout_results[0].message

    @patch("shutil.which")
    def test_missing_critical_tool(self, mock_which, tmp_path: Path):
        def which_side_effect(name):
            if name == "git":
                return None
            return f"/usr/bin/{name}"

        mock_which.side_effect = which_side_effect
        results = check_required_tools(tmp_path)
        git_results = [r for r in results if "git" in r.name]
        assert git_results[0].status == CheckStatus.FAIL
        assert git_results[0].severity == Severity.CRITICAL

    @patch("shutil.which")
    def test_op_critical_when_env_has_refs(self, mock_which, tmp_path: Path):
        (tmp_path / ".env").write_text("DATABASE_URL=op://vault/item/field\n")

        def which_side_effect(name):
            if name == "op":
                return None
            return f"/usr/bin/{name}"

        mock_which.side_effect = which_side_effect
        results = check_required_tools(tmp_path)
        op_results = [r for r in results if "op" in r.name]
        assert op_results[0].severity == Severity.CRITICAL


# ---------------------------------------------------------------------------
# TestFixMode
# ---------------------------------------------------------------------------


class TestFixMode:
    @patch("compgraph.preflight._run_cmd")
    def test_fix_uv_sync_success(self, mock_run, tmp_path: Path):
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(
            CheckResult(
                name="venv_and_deps",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message="out of sync",
                fix_available=True,
                fix_command="uv sync",
            )
        )
        actions = apply_fixes(report, tmp_path)
        assert any("successfully" in a for a in actions)
        assert report.checks[0].status == CheckStatus.PASS

    @patch("compgraph.preflight._run_cmd")
    def test_fix_uv_sync_failure(self, mock_run, tmp_path: Path):
        mock_run.return_value = SimpleNamespace(returncode=1, stdout="", stderr="error")
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(
            CheckResult(
                name="venv_and_deps",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message="out of sync",
                fix_available=True,
                fix_command="uv sync",
            )
        )
        actions = apply_fixes(report, tmp_path)
        assert any("failed" in a.lower() for a in actions)

    def test_fix_corrupt_lock_removal(self, tmp_path: Path):
        locks_dir = tmp_path / ".locks"
        locks_dir.mkdir()
        lock_file = locks_dir / "corrupt-task.pid"
        lock_file.write_text("garbage")
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(
            CheckResult(
                name="process_lock",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message="Corrupt lock file: " + str(lock_file),
                details={"lock_file": str(lock_file)},
                fix_available=True,
                fix_command=f"rm {lock_file}",
            )
        )
        actions = apply_fixes(report, tmp_path)
        assert not lock_file.exists()
        assert any("corrupt lock" in a.lower() for a in actions)


# ---------------------------------------------------------------------------
# TestCLI
# ---------------------------------------------------------------------------


class TestCLI:
    @patch("compgraph.preflight.PreflightRunner")
    def test_exit_code_0_all_pass(self, MockRunner, tmp_path: Path):
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(CheckResult("a", CheckStatus.PASS, Severity.CRITICAL, "ok"))
        MockRunner.return_value.run_all.return_value = report
        MockRunner.return_value.project_root = tmp_path
        code = main(["--project-dir", str(tmp_path)])
        assert code == 0

    @patch("compgraph.preflight.PreflightRunner")
    def test_exit_code_1_critical(self, MockRunner, tmp_path: Path):
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(CheckResult("a", CheckStatus.FAIL, Severity.CRITICAL, "broken"))
        MockRunner.return_value.run_all.return_value = report
        MockRunner.return_value.project_root = tmp_path
        code = main(["--project-dir", str(tmp_path)])
        assert code == 1

    @patch("compgraph.preflight.PreflightRunner")
    def test_exit_code_2_warnings(self, MockRunner, tmp_path: Path):
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(CheckResult("a", CheckStatus.WARN, Severity.WARNING, "meh"))
        MockRunner.return_value.run_all.return_value = report
        MockRunner.return_value.project_root = tmp_path
        code = main(["--project-dir", str(tmp_path)])
        assert code == 2

    @patch("compgraph.preflight.PreflightRunner")
    def test_json_output(self, MockRunner, tmp_path: Path, capsys):
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(CheckResult("a", CheckStatus.PASS, Severity.INFO, "ok"))
        MockRunner.return_value.run_all.return_value = report
        MockRunner.return_value.project_root = tmp_path
        main(["--project-dir", str(tmp_path), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["passed"] is True

    @patch("compgraph.preflight.PreflightRunner")
    def test_selective_checks(self, MockRunner, tmp_path: Path):
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        MockRunner.return_value.run_all.return_value = report
        MockRunner.return_value.project_root = tmp_path
        main(["--project-dir", str(tmp_path), "--checks", "python,tools"])
        call_kwargs = MockRunner.call_args[1]
        assert call_kwargs["checks"] == ["python", "tools"]

    @patch("compgraph.preflight.PreflightRunner")
    def test_fix_flag(self, MockRunner, tmp_path: Path):
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        MockRunner.return_value.run_all.return_value = report
        MockRunner.return_value.project_root = tmp_path
        main(["--project-dir", str(tmp_path), "--fix"])
        call_kwargs = MockRunner.call_args[1]
        assert call_kwargs["fix"] is True

    def test_parser_defaults(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.fix is False
        assert args.json_output is False
        assert args.checks is None
        assert args.task is None
        assert args.branch is None
        assert args.project_dir is None


# ---------------------------------------------------------------------------
# TestUtilities
# ---------------------------------------------------------------------------


class TestUtilities:
    def test_parse_env_file(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            '# comment\nKEY1=value1\nKEY2="quoted value"\n'
            "KEY3='single quoted'\n\nKEY4=no_quotes\n"
        )
        env = parse_env_file(env_file)
        assert env["KEY1"] == "value1"
        assert env["KEY2"] == "quoted value"
        assert env["KEY3"] == "single quoted"
        assert env["KEY4"] == "no_quotes"

    def test_parse_env_file_missing(self, tmp_path: Path):
        env = parse_env_file(tmp_path / ".env")
        assert env == {}

    def test_is_placeholder(self):
        assert is_placeholder("your-password") is True
        assert is_placeholder("sk-ant-...") is True
        assert is_placeholder("changeme") is True
        assert is_placeholder("real-secret-value-abc123") is False

    def test_format_human_output(self):
        report = PreflightReport(
            timestamp="2026-02-12T18:30:00",
            platform="darwin",
            python_version="3.14.3",
            project_root="/tmp/test",
            checks=[
                CheckResult("test", CheckStatus.PASS, Severity.INFO, "all good"),
            ],
        )
        output = format_human(report, use_color=False)
        assert "CompGraph Preflight Check" in output
        assert "[PASS]" in output
        assert "all good" in output

    def test_write_diagnostics_on_failure(self, tmp_path: Path):
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(CheckResult("a", CheckStatus.FAIL, Severity.CRITICAL, "broken"))
        diag_file = write_diagnostics(report, tmp_path)
        assert diag_file is not None
        assert diag_file.exists()
        data = json.loads(diag_file.read_text())
        assert data["passed"] is False

    def test_write_diagnostics_skip_on_pass(self, tmp_path: Path):
        report = PreflightReport(
            timestamp="now", platform="test", python_version="3.14.0", project_root=str(tmp_path)
        )
        report.checks.append(CheckResult("a", CheckStatus.PASS, Severity.INFO, "ok"))
        diag_file = write_diagnostics(report, tmp_path)
        assert diag_file is None

    def test_find_project_root(self, tmp_path: Path):
        from compgraph.preflight import find_project_root

        (tmp_path / "pyproject.toml").write_text("[project]\n")
        sub = tmp_path / "src" / "pkg"
        sub.mkdir(parents=True)
        root = find_project_root(sub)
        assert root == tmp_path
