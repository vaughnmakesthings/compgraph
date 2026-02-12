"""Preflight validation for CompGraph environment.

Validates Python version, venv/dependencies, API keys, git state,
process locks, and required tools before any work begins.

stdlib-only imports at module level — httpx is lazy-imported for API validation.
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import platform
import re
import signal
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class CheckStatus(StrEnum):
    PASS = "pass"  # noqa: S105
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    severity: Severity
    message: str
    details: dict[str, str] = field(default_factory=dict)
    fix_available: bool = False
    fix_command: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["severity"] = self.severity.value
        return d


@dataclass
class PreflightReport:
    timestamp: str
    platform: str
    python_version: str
    project_root: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(
            c.status == CheckStatus.FAIL and c.severity == Severity.CRITICAL for c in self.checks
        )

    @property
    def critical_count(self) -> int:
        return sum(
            1
            for c in self.checks
            if c.status == CheckStatus.FAIL and c.severity == Severity.CRITICAL
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1
            for c in self.checks
            if c.status in (CheckStatus.FAIL, CheckStatus.WARN) and c.severity == Severity.WARNING
        )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "platform": self.platform,
            "python_version": self.python_version,
            "project_root": self.project_root,
            "passed": self.passed,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "checks": [c.to_dict() for c in self.checks],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

_PLACEHOLDER_PATTERNS = [
    "your-password",
    "your-project",
    "sk-ant-...",
    "your-api-key",
    "changeme",
    "placeholder",
    "xxx",
]

_OP_REF_RE = re.compile(r"^op://[^/]+/[^/]+/[^/]+$")


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start to find directory containing pyproject.toml."""
    current = start or Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return current


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Minimal .env parser — handles KEY=VALUE, quotes, comments."""
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        env[key] = value
    return env


def is_placeholder(value: str) -> bool:
    """Check if a value looks like a placeholder from .env.example."""
    lower = value.lower()
    return any(p in lower for p in _PLACEHOLDER_PATTERNS)


def is_op_reference(value: str) -> bool:
    """Check if a value is a 1Password secret reference."""
    return bool(_OP_REF_RE.match(value))


def resolve_op_reference(ref: str, timeout: float = 5.0) -> tuple[str | None, str | None]:
    """Resolve a 1Password op:// reference. Returns (value, error)."""
    try:
        result = subprocess.run(
            ["op", "read", ref],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip(), None
        return None, result.stderr.strip() or "op read failed"
    except FileNotFoundError:
        return None, "1Password CLI (op) not found"
    except subprocess.TimeoutExpired:
        return None, f"op read timed out after {timeout}s"


def _run_cmd(
    args: list[str], timeout: float = 10.0, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with timeout, capturing output."""
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )


# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

_COLORS = {
    CheckStatus.PASS: "\033[32m",  # green
    CheckStatus.FAIL: "\033[31m",  # red
    CheckStatus.WARN: "\033[33m",  # yellow
    CheckStatus.SKIP: "\033[90m",  # gray
}
_RESET = "\033[0m"
_BOLD = "\033[1m"


def _color(status: CheckStatus, text: str, use_color: bool) -> str:
    if not use_color:
        return text
    return f"{_COLORS.get(status, '')}{text}{_RESET}"


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_python_version(project_root: Path) -> CheckResult:
    """Check that the running Python satisfies requires-python from pyproject.toml."""
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return CheckResult(
            name="python_version",
            status=CheckStatus.WARN,
            severity=Severity.WARNING,
            message="pyproject.toml not found, cannot check Python version",
        )

    try:
        data = tomllib.loads(pyproject.read_text())
    except Exception as e:
        return CheckResult(
            name="python_version",
            status=CheckStatus.WARN,
            severity=Severity.WARNING,
            message=f"Failed to parse pyproject.toml: {e}",
        )

    requires = data.get("project", {}).get("requires-python", "")
    if not requires:
        return CheckResult(
            name="python_version",
            status=CheckStatus.SKIP,
            severity=Severity.INFO,
            message="No requires-python specified",
        )

    current = sys.version_info
    current_str = f"{current.major}.{current.minor}.{current.micro}"

    # Parse version specifiers (handle >=3.12, >=3.12,<4.0, ~=3.12)
    if not _check_version_specifier(requires, current):
        return CheckResult(
            name="python_version",
            status=CheckStatus.FAIL,
            severity=Severity.CRITICAL,
            message=f"Python {current_str} does not satisfy {requires}",
            details={"current": current_str, "requires": requires},
        )

    return CheckResult(
        name="python_version",
        status=CheckStatus.PASS,
        severity=Severity.CRITICAL,
        message=f"Python {current_str} satisfies {requires}",
        details={"current": current_str, "requires": requires},
    )


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a version string like '3.12' or '3.12.1' into a tuple."""
    parts = version_str.strip().split(".")
    return tuple(int(p) for p in parts if p.isdigit())


def _check_version_specifier(specifier: str, version_info: object) -> bool:
    """Check if version_info satisfies a PEP 440-ish specifier string."""
    vi = version_info
    current = (vi.major, vi.minor, vi.micro)  # type: ignore[union-attr]

    for spec in specifier.split(","):
        spec = spec.strip()
        if not spec:
            continue

        if spec.startswith("~="):
            # Compatible release: ~=3.12 means >=3.12, <4.0
            ver = _parse_version(spec[2:])
            if len(ver) >= 2:
                if current[:2] < ver[:2]:
                    return False
                if current[0] > ver[0]:
                    return False
        elif spec.startswith(">="):
            ver = _parse_version(spec[2:])
            if current[: len(ver)] < ver:
                return False
        elif spec.startswith("<="):
            ver = _parse_version(spec[2:])
            if current[: len(ver)] > ver:
                return False
        elif spec.startswith("!="):
            ver = _parse_version(spec[2:])
            if current[: len(ver)] == ver:
                return False
        elif spec.startswith(">"):
            ver = _parse_version(spec[1:])
            if current[: len(ver)] <= ver:
                return False
        elif spec.startswith("<"):
            ver = _parse_version(spec[1:])
            if current[: len(ver)] >= ver:
                return False
        elif spec.startswith("=="):
            ver = _parse_version(spec[2:])
            if current[: len(ver)] != ver:
                return False

    return True


def check_venv_and_deps(project_root: Path) -> CheckResult:
    """Check that .venv exists, uv.lock exists, and dependencies are synced."""
    venv_dir = project_root / ".venv"
    if not venv_dir.is_dir():
        return CheckResult(
            name="venv_and_deps",
            status=CheckStatus.FAIL,
            severity=Severity.CRITICAL,
            message="Virtual environment (.venv/) not found",
            fix_available=True,
            fix_command="uv sync",
        )

    lockfile = project_root / "uv.lock"
    if not lockfile.exists():
        return CheckResult(
            name="venv_and_deps",
            status=CheckStatus.FAIL,
            severity=Severity.CRITICAL,
            message="uv.lock not found — run uv lock",
            fix_available=True,
            fix_command="uv sync",
        )

    # Check if deps are in sync
    try:
        result = _run_cmd(["uv", "sync", "--dry-run"], timeout=30.0, cwd=project_root)
        output = result.stdout + result.stderr
        # If uv sync --dry-run mentions installing/uninstalling, we're out of sync
        if re.search(r"(?i)(would install|would uninstall|would upgrade|would downgrade)", output):
            return CheckResult(
                name="venv_and_deps",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message="Dependencies out of sync",
                details={"dry_run_output": output.strip()[:500]},
                fix_available=True,
                fix_command="uv sync",
            )
    except FileNotFoundError:
        return CheckResult(
            name="venv_and_deps",
            status=CheckStatus.FAIL,
            severity=Severity.CRITICAL,
            message="uv not found in PATH",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="venv_and_deps",
            status=CheckStatus.WARN,
            severity=Severity.WARNING,
            message="uv sync --dry-run timed out",
        )

    return CheckResult(
        name="venv_and_deps",
        status=CheckStatus.PASS,
        severity=Severity.CRITICAL,
        message="All dependencies synced",
    )


def check_api_keys(project_root: Path) -> list[CheckResult]:
    """Check API keys and secrets from .env file. Returns multiple results."""
    results: list[CheckResult] = []
    env_path = project_root / ".env"
    example_path = project_root / ".env.example"

    if not env_path.exists():
        results.append(
            CheckResult(
                name="api_keys",
                status=CheckStatus.WARN,
                severity=Severity.WARNING,
                message=".env file not found",
                details={"hint": "Copy .env.example to .env and fill in values"},
            )
        )
        return results

    env = parse_env_file(env_path)
    _ = parse_env_file(example_path) if example_path.exists() else {}

    # Resolve any 1Password references
    resolved_env = {}
    has_op_refs = any(is_op_reference(v) for v in env.values())

    if has_op_refs:
        import shutil

        if not shutil.which("op"):
            results.append(
                CheckResult(
                    name="api_keys_op",
                    status=CheckStatus.FAIL,
                    severity=Severity.CRITICAL,
                    message="1Password CLI (op) required but not found — .env has op:// references",
                    details={"hint": "brew install 1password-cli"},
                )
            )
            return results

        # Check op session
        try:
            session_result = _run_cmd(["op", "account", "list"], timeout=5.0)
            if session_result.returncode != 0:
                results.append(
                    CheckResult(
                        name="api_keys_op",
                        status=CheckStatus.FAIL,
                        severity=Severity.CRITICAL,
                        message="1Password session expired — run: eval $(op signin)",
                    )
                )
                return results
        except (FileNotFoundError, subprocess.TimeoutExpired):
            results.append(
                CheckResult(
                    name="api_keys_op",
                    status=CheckStatus.FAIL,
                    severity=Severity.CRITICAL,
                    message="Failed to check 1Password session",
                )
            )
            return results

    # Resolve values
    for key, value in env.items():
        if is_op_reference(value):
            resolved, err = resolve_op_reference(value)
            if err:
                results.append(
                    CheckResult(
                        name=f"api_keys_{key.lower()}",
                        status=CheckStatus.FAIL,
                        severity=Severity.CRITICAL,
                        message=f"Failed to resolve {key} from 1Password: {err}",
                    )
                )
                resolved_env[key] = value  # Keep original on failure
            else:
                resolved_env[key] = resolved  # type: ignore[assignment]
        else:
            resolved_env[key] = value

    # Check DATABASE_URL
    db_url = resolved_env.get("DATABASE_URL", "")
    if not db_url or is_placeholder(db_url):
        results.append(
            CheckResult(
                name="api_keys_database",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message="DATABASE_URL is missing or placeholder",
            )
        )
    else:
        results.append(
            CheckResult(
                name="api_keys_database",
                status=CheckStatus.PASS,
                severity=Severity.CRITICAL,
                message="DATABASE_URL is set",
            )
        )

    # Check ANTHROPIC_API_KEY
    api_key = resolved_env.get("ANTHROPIC_API_KEY", "")
    if not api_key or is_placeholder(api_key):
        results.append(
            CheckResult(
                name="api_keys_anthropic",
                status=CheckStatus.WARN,
                severity=Severity.WARNING,
                message="ANTHROPIC_API_KEY is missing or placeholder",
            )
        )
    elif not api_key.startswith("sk-ant-"):
        results.append(
            CheckResult(
                name="api_keys_anthropic",
                status=CheckStatus.WARN,
                severity=Severity.WARNING,
                message="ANTHROPIC_API_KEY doesn't have expected sk-ant- prefix",
            )
        )
    else:
        # Validate key with a lightweight API call
        key_result = _validate_anthropic_key(api_key)
        results.append(key_result)

    # Check gh auth
    gh_result = _check_gh_auth()
    results.append(gh_result)

    return results


def _validate_anthropic_key(api_key: str) -> CheckResult:
    """Validate Anthropic API key with a lightweight test call."""
    try:
        import httpx
    except ImportError:
        return CheckResult(
            name="api_keys_anthropic",
            status=CheckStatus.SKIP,
            severity=Severity.WARNING,
            message="httpx not installed — skipping API key validation",
        )

    try:
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1, "messages": []},
            timeout=5.0,
        )
        if response.status_code == 401:
            return CheckResult(
                name="api_keys_anthropic",
                status=CheckStatus.FAIL,
                severity=Severity.WARNING,
                message="ANTHROPIC_API_KEY returned 401 (invalid key)",
            )
        # 400 = valid key, bad request body (expected)
        return CheckResult(
            name="api_keys_anthropic",
            status=CheckStatus.PASS,
            severity=Severity.WARNING,
            message="ANTHROPIC_API_KEY is valid",
        )
    except httpx.TimeoutException:
        return CheckResult(
            name="api_keys_anthropic",
            status=CheckStatus.WARN,
            severity=Severity.WARNING,
            message="ANTHROPIC_API_KEY validation timed out",
        )
    except Exception as e:
        return CheckResult(
            name="api_keys_anthropic",
            status=CheckStatus.WARN,
            severity=Severity.WARNING,
            message=f"ANTHROPIC_API_KEY validation error: {e}",
        )


def _check_gh_auth() -> CheckResult:
    """Check GitHub CLI authentication status."""
    try:
        result = _run_cmd(["gh", "auth", "status"], timeout=10.0)
        if result.returncode == 0:
            return CheckResult(
                name="api_keys_gh",
                status=CheckStatus.PASS,
                severity=Severity.INFO,
                message="GitHub CLI authenticated",
            )
        return CheckResult(
            name="api_keys_gh",
            status=CheckStatus.WARN,
            severity=Severity.INFO,
            message="GitHub CLI not authenticated",
            details={"stderr": result.stderr.strip()[:200]},
        )
    except FileNotFoundError:
        return CheckResult(
            name="api_keys_gh",
            status=CheckStatus.SKIP,
            severity=Severity.INFO,
            message="GitHub CLI (gh) not installed",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="api_keys_gh",
            status=CheckStatus.WARN,
            severity=Severity.INFO,
            message="gh auth status timed out",
        )


def check_git_state(project_root: Path, expected_branch: str | None = None) -> CheckResult:
    """Check git repository state."""
    # Is this a git repo?
    try:
        result = _run_cmd(["git", "rev-parse", "--is-inside-work-tree"], cwd=project_root)
        if result.returncode != 0:
            return CheckResult(
                name="git_state",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message="Not inside a git repository",
            )
    except FileNotFoundError:
        return CheckResult(
            name="git_state",
            status=CheckStatus.FAIL,
            severity=Severity.CRITICAL,
            message="git not found in PATH",
        )

    # Current branch
    branch_result = _run_cmd(["git", "branch", "--show-current"], cwd=project_root)
    current_branch = branch_result.stdout.strip()

    # Check expected branch
    if expected_branch and current_branch != expected_branch:
        return CheckResult(
            name="git_state",
            status=CheckStatus.WARN,
            severity=Severity.WARNING,
            message=f"On branch '{current_branch}', expected '{expected_branch}'",
            details={"current_branch": current_branch, "expected_branch": expected_branch},
        )

    # Dirty state
    status_result = _run_cmd(["git", "status", "--porcelain"], cwd=project_root)
    dirty_files = [line for line in status_result.stdout.splitlines() if line.strip()]

    if dirty_files:
        return CheckResult(
            name="git_state",
            status=CheckStatus.WARN,
            severity=Severity.WARNING,
            message=(
                f"Working tree has {len(dirty_files)} uncommitted change(s) on '{current_branch}'"
            ),
            details={
                "branch": current_branch,
                "dirty_count": str(len(dirty_files)),
            },
        )

    return CheckResult(
        name="git_state",
        status=CheckStatus.PASS,
        severity=Severity.WARNING,
        message=f"Clean worktree on branch '{current_branch}'",
        details={"branch": current_branch},
    )


def check_process_lock(project_root: Path, task_name: str | None = None) -> CheckResult:
    """Check and acquire a process lock for a named task."""
    if not task_name:
        return CheckResult(
            name="process_lock",
            status=CheckStatus.SKIP,
            severity=Severity.INFO,
            message="No --task specified",
        )

    locks_dir = project_root / ".locks"
    locks_dir.mkdir(exist_ok=True)
    lock_file = locks_dir / f"{task_name}.pid"

    if lock_file.exists():
        try:
            pid_str = lock_file.read_text().strip()
            pid = int(pid_str)
        except (ValueError, OSError):
            return CheckResult(
                name="process_lock",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message=f"Corrupt lock file: {lock_file}",
                fix_available=True,
                fix_command=f"rm {lock_file}",
            )

        # Check if PID is still alive
        try:
            os.kill(pid, 0)
            # Process is alive
            return CheckResult(
                name="process_lock",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message=f"Task '{task_name}' already running (PID {pid})",
                details={"pid": str(pid), "lock_file": str(lock_file)},
            )
        except ProcessLookupError:
            # Process is dead — stale lock
            return CheckResult(
                name="process_lock",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message=f"Stale lock for '{task_name}' (PID {pid} is dead)",
                details={"pid": str(pid), "lock_file": str(lock_file)},
                fix_available=True,
                fix_command=f"rm {lock_file}",
            )
        except PermissionError:
            # Process exists but we can't signal it — treat as alive
            return CheckResult(
                name="process_lock",
                status=CheckStatus.FAIL,
                severity=Severity.CRITICAL,
                message=f"Task '{task_name}' locked by PID {pid} (permission denied on signal)",
                details={"pid": str(pid), "lock_file": str(lock_file)},
            )

    # No existing lock — acquire it
    my_pid = os.getpid()
    lock_file.write_text(str(my_pid))

    def _cleanup_lock(*_args: object) -> None:
        try:
            if lock_file.exists() and lock_file.read_text().strip() == str(my_pid):
                lock_file.unlink()
        except OSError:
            pass

    atexit.register(_cleanup_lock)
    signal.signal(signal.SIGTERM, lambda *a: (_cleanup_lock(), sys.exit(143)))
    signal.signal(signal.SIGINT, lambda *a: (_cleanup_lock(), sys.exit(130)))

    return CheckResult(
        name="process_lock",
        status=CheckStatus.PASS,
        severity=Severity.CRITICAL,
        message=f"Lock acquired for '{task_name}' (PID {my_pid})",
        details={"pid": str(my_pid), "lock_file": str(lock_file)},
    )


def check_required_tools(project_root: Path) -> list[CheckResult]:
    """Check that required external tools are available."""
    import shutil

    results: list[CheckResult] = []
    is_macos = sys.platform == "darwin"

    # Tool registry: (name, alternatives, severity, install_hint)
    tools: list[tuple[str, list[str], Severity, str]] = [
        ("git", [], Severity.CRITICAL, "Install git"),
        ("uv", [], Severity.CRITICAL, "curl -LsSf https://astral.sh/uv/install.sh | sh"),
        (
            "timeout",
            ["gtimeout"] if is_macos else [],
            Severity.WARNING,
            "brew install coreutils" if is_macos else "Install coreutils",
        ),
        (
            "realpath",
            ["grealpath"] if is_macos else [],
            Severity.WARNING,
            "brew install coreutils" if is_macos else "Install coreutils",
        ),
    ]

    # Check if .env has op:// references — if so, op is CRITICAL
    env_path = project_root / ".env"
    env_has_op_refs = False
    if env_path.exists():
        env = parse_env_file(env_path)
        env_has_op_refs = any(is_op_reference(v) for v in env.values())

    op_severity = Severity.CRITICAL if env_has_op_refs else Severity.INFO
    tools.append(
        (
            "op",
            [],
            op_severity,
            "brew install 1password-cli" if is_macos else "Install 1Password CLI",
        )
    )

    for tool_name, alternatives, severity, install_hint in tools:
        found = shutil.which(tool_name)
        if found:
            results.append(
                CheckResult(
                    name=f"tool_{tool_name}",
                    status=CheckStatus.PASS,
                    severity=severity,
                    message=f"{tool_name} found at {found}",
                )
            )
            continue

        # Try alternatives
        alt_found = None
        for alt in alternatives:
            alt_path = shutil.which(alt)
            if alt_path:
                alt_found = alt
                break

        if alt_found:
            results.append(
                CheckResult(
                    name=f"tool_{tool_name}",
                    status=CheckStatus.PASS,
                    severity=severity,
                    message=f"{tool_name} not found, using {alt_found}",
                    details={"alternative": alt_found},
                )
            )
        else:
            results.append(
                CheckResult(
                    name=f"tool_{tool_name}",
                    status=CheckStatus.WARN if severity == Severity.WARNING else CheckStatus.FAIL,
                    severity=severity,
                    message=f"Missing: {tool_name} (try: {install_hint})",
                    details={"install": install_hint},
                )
            )

    return results


# ---------------------------------------------------------------------------
# Fix logic
# ---------------------------------------------------------------------------


def apply_fixes(report: PreflightReport, project_root: Path) -> list[str]:
    """Apply automated fixes for issues that support them. Returns log of actions taken."""
    actions: list[str] = []

    for check in report.checks:
        if not check.fix_available or check.status != CheckStatus.FAIL:
            continue

        if check.name == "venv_and_deps":
            try:
                result = _run_cmd(["uv", "sync"], timeout=120.0, cwd=project_root)
                if result.returncode == 0:
                    actions.append("Fixed: ran uv sync successfully")
                    check.status = CheckStatus.PASS
                    check.message = "Dependencies synced (fixed)"
                else:
                    actions.append(f"Fix failed: uv sync returned {result.returncode}")
            except Exception as e:
                actions.append(f"Fix failed: uv sync error: {e}")

        elif check.name == "process_lock" and "Stale" in check.message:
            lock_file = check.details.get("lock_file", "")
            if lock_file:
                try:
                    Path(lock_file).unlink()
                    actions.append(f"Fixed: removed stale lock {lock_file}")
                    check.status = CheckStatus.PASS
                    check.message = "Stale lock removed (fixed)"
                except OSError as e:
                    actions.append(f"Fix failed: could not remove {lock_file}: {e}")

        elif check.name == "process_lock" and "Corrupt" in check.message:
            lock_file = check.details.get("lock_file", "")
            if lock_file:
                try:
                    Path(lock_file).unlink()
                    actions.append(f"Fixed: removed corrupt lock {lock_file}")
                    check.status = CheckStatus.PASS
                    check.message = "Corrupt lock removed (fixed)"
                except OSError as e:
                    actions.append(f"Fix failed: could not remove {lock_file}: {e}")

    return actions


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_CHECKS = ["python", "venv", "api_keys", "git", "process_lock", "tools"]


class PreflightRunner:
    def __init__(
        self,
        project_root: Path | None = None,
        checks: list[str] | None = None,
        task_name: str | None = None,
        expected_branch: str | None = None,
        fix: bool = False,
    ):
        self.project_root = project_root or find_project_root()
        self.checks = checks or ALL_CHECKS
        self.task_name = task_name
        self.expected_branch = expected_branch
        self.fix = fix

    def run_all(self) -> PreflightReport:
        report = PreflightReport(
            timestamp=datetime.now(UTC).isoformat(),
            platform=platform.system().lower(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            project_root=str(self.project_root),
        )

        if "python" in self.checks:
            report.checks.append(check_python_version(self.project_root))

        if "venv" in self.checks:
            report.checks.append(check_venv_and_deps(self.project_root))

        if "api_keys" in self.checks:
            report.checks.extend(check_api_keys(self.project_root))

        if "git" in self.checks:
            report.checks.append(check_git_state(self.project_root, self.expected_branch))

        if "process_lock" in self.checks:
            report.checks.append(check_process_lock(self.project_root, self.task_name))

        if "tools" in self.checks:
            report.checks.extend(check_required_tools(self.project_root))

        if self.fix:
            apply_fixes(report, self.project_root)

        return report


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_human(report: PreflightReport, use_color: bool = True) -> str:
    """Format report for human-readable terminal output."""
    lines: list[str] = []
    header = "CompGraph Preflight Check"
    lines.append(f"{_BOLD}{header}{_RESET}" if use_color else header)
    lines.append("=" * len(header))
    lines.append(
        f"Platform: {report.platform} | Python: {report.python_version} | {report.timestamp[:19]}"
    )
    lines.append("")

    for check in report.checks:
        tag = f"[{check.status.value.upper():4s}]"
        tag = _color(check.status, tag, use_color)
        lines.append(f"  {tag} {check.name:20s} {check.message}")

    lines.append("")
    if report.passed:
        result_msg = "PASSED"
        if report.warning_count:
            result_msg += f" ({report.warning_count} warning(s))"
        lines.append(_color(CheckStatus.PASS, f"Result: {result_msg}", use_color))
    else:
        result_msg = f"FAILED ({report.critical_count} critical"
        if report.warning_count:
            result_msg += f", {report.warning_count} warning(s)"
        result_msg += ")"
        lines.append(_color(CheckStatus.FAIL, f"Result: {result_msg}", use_color))

    return "\n".join(lines)


def write_diagnostics(report: PreflightReport, project_root: Path) -> Path | None:
    """Write diagnostic JSON file on critical failure."""
    if report.passed:
        return None

    diag_dir = project_root / ".diagnostics"
    diag_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    diag_file = diag_dir / f"preflight_{ts}.json"
    diag_file.write_text(report.to_json())
    return diag_file


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="preflight",
        description="CompGraph environment preflight validation",
    )
    parser.add_argument("--fix", action="store_true", help="Auto-remediate fixable issues")
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output JSON report"
    )
    parser.add_argument(
        "--checks",
        type=str,
        default=None,
        help=f"Comma-separated checks to run (default: all). Options: {','.join(ALL_CHECKS)}",
    )
    parser.add_argument("--task", type=str, default=None, help="Task name for process lock check")
    parser.add_argument("--branch", type=str, default=None, help="Expected git branch name")
    parser.add_argument(
        "--project-dir",
        type=str,
        default=None,
        help="Override project root detection",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    project_root = Path(args.project_dir) if args.project_dir else None
    checks = args.checks.split(",") if args.checks else None

    runner = PreflightRunner(
        project_root=project_root,
        checks=checks,
        task_name=args.task,
        expected_branch=args.branch,
        fix=args.fix,
    )

    report = runner.run_all()

    if args.json_output:
        print(report.to_json())
    else:
        use_color = sys.stdout.isatty()
        print(format_human(report, use_color=use_color))

        # Write diagnostics on failure
        diag_file = write_diagnostics(report, runner.project_root)
        if diag_file:
            print(f"Diagnostics: {diag_file}")

    if not report.passed:
        return 1
    if report.warning_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
