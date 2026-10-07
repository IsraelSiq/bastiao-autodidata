"""Bastiao - Tools (ACI - Agent Computer Interface)

Ferramentas que o agente pode usar.
"""

import hashlib
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .action_approval import (
    ActionApprovalStore,
    ActionClass,
    _docker_block_reason,
    _is_npm_validation_command,
    _is_sensitive_path,
    classify_action,
)
from .process import run_bounded, sanitized_env


class ToolHandler:
    """Gerencia ferramentas do agente."""

    def __init__(
        self,
        repo_path: str = ".",
        allowed_paths: Optional[list[str]] = None,
        strict_scope: bool = False,
        command_timeout_seconds: int = 60,
        max_output_chars: int = 10000,
        max_commands: int = 100,
        max_write_bytes: int = 1_000_000,
        memory_limit_mb: int = 0,
        cpu_limit_seconds: int = 0,
        issue_number: Optional[int] = None,
        approval_store: Optional[ActionApprovalStore] = None,
        require_action_approval: bool = True,
        expected_branch: Optional[str] = None,
    ):
        """Inicializa o handler.

        Args:
            repo_path: Caminho do repositorio
        """
        self.repo_path = Path(repo_path).resolve()
        self.strict_scope = strict_scope
        self.command_timeout_seconds = command_timeout_seconds
        self.max_output_chars = max_output_chars
        self.max_commands = max_commands
        self.max_write_bytes = max_write_bytes
        self.memory_limit_mb = memory_limit_mb
        self.cpu_limit_seconds = cpu_limit_seconds
        self.issue_number = issue_number
        self.approval_store = approval_store
        self.require_action_approval = require_action_approval
        self.expected_branch = expected_branch
        self._temp_dir: Optional[str] = None
        self.last_approval_request: Optional[dict] = None
        self._approved_action_fingerprint: Optional[str] = None
        self.command_count = 0
        self.allowed_paths = {
            normalized[2:] if normalized.startswith("./") else normalized
            for path in (allowed_paths or [])
            for normalized in [path.replace("\\", "/")]
        }

    def _temp_env(self) -> dict:
        """Point temporary files at a per-task directory removed by cleanup()."""
        if self._temp_dir is None:
            self._temp_dir = tempfile.mkdtemp(prefix="bastiao-")
        return {"TMPDIR": self._temp_dir, "TEMP": self._temp_dir, "TMP": self._temp_dir}

    def cleanup(self) -> None:
        """Remove the per-task temporary directory; safe to call repeatedly."""
        if self._temp_dir is not None:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None

    def _safe_path(self, path: str) -> Path:
        """Resolve a repository-relative path without allowing traversal."""
        candidate = Path(path)
        if candidate.is_absolute():
            raise ValueError("absolute paths are not allowed")
        resolved = (self.repo_path / candidate).resolve()
        if resolved != self.repo_path and self.repo_path not in resolved.parents:
            raise ValueError("path escapes repository root")
        return resolved

    def execute(self, action: str) -> str:
        """Executa uma acao.

        Args:
            action: Acao no formato "command args"

        Returns:
            Resultado da execucao
        """
        parts = action.strip().split(maxsplit=1)
        if not parts:
            return "ERROR: Empty action"

        command = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        action_class, target, fingerprint = classify_action(action, self.repo_path)
        if action_class is ActionClass.BLOCKED:
            return f"ERROR: Action blocked: {target}"
        requires_specific_approval = (
            action_class is ActionClass.APPROVAL
            and (
                self.require_action_approval
                or target.startswith(
                    ("dependency installation:", "JavaScript execution:", "Docker inspection:")
                )
            )
        )
        if requires_specific_approval:
            if self.approval_store is None or self.issue_number is None:
                return "ERROR: Sensitive action requires an approval store and issue number"
            approved, request = self.approval_store.authorize(
                self.issue_number,
                action_class.value + ":" + target.split(" ", 1)[0],
                target,
                fingerprint,
            )
            self.last_approval_request = request
            if not approved:
                return (
                    f"ERROR: Sensitive action requires human approval "
                    f"(request {request['request_id']}, status {request['status']}). "
                    "Review with `python -m src.action_approval list`; approve with "
                    "`python -m src.action_approval approve <request_id> --approver <name>`."
                )
            self._approved_action_fingerprint = fingerprint

        if command == "read":
            return self.read_file(args)
        elif command == "write":
            return self.write_file(args)
        elif command == "run":
            return self.run_command(args)
        elif command == "search":
            return self.search_code(args)
        elif command == "list":
            return self.list_files(args)
        elif command == "complete" and not args:
            return "OK: Completion requested"
        else:
            return f"ERROR: Unknown command '{command}'"

    def read_file(self, path: str) -> str:
        """Le arquivo.

        Args:
            path: Caminho do arquivo

        Returns:
            Conteudo do arquivo
        """
        try:
            filepath = self._safe_path(path)
        except ValueError as error:
            return f"ERROR: {error}"
        action_class, target, _ = classify_action(f"read {path}", self.repo_path)
        if action_class is ActionClass.BLOCKED:
            return f"ERROR: Action blocked: {target}"
        if not filepath.exists():
            return f"ERROR: File not found: {path}"
        if not filepath.is_file():
            return f"ERROR: Not a file: {path}"

        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, args: str) -> str:
        """Escreve arquivo.

        Formato: "path content"

        Args:
            args: Path e content

        Returns:
            Resultado
        """
        # Divide path e content
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            return "ERROR: Usage: write <path> <content>"

        path = parts[0]
        content = parts[1]
        action_fingerprint = hashlib.sha256(
            f"write {args}".encode("utf-8")
        ).hexdigest()
        action_class, action_target, _ = classify_action(f"write {args}", self.repo_path)
        if (
            action_class is ActionClass.APPROVAL
            and self.require_action_approval
            and self._approved_action_fingerprint != action_fingerprint
        ):
            return "ERROR: Configuration writes require approval through the action gate"
        if len(content.encode("utf-8")) > self.max_write_bytes:
            return f"ERROR: File content exceeds limit ({self.max_write_bytes} bytes)"

        try:
            filepath = self._safe_path(path)
        except ValueError as error:
            return f"ERROR: {error}"
        if action_class is ActionClass.BLOCKED:
            return f"ERROR: Action blocked: {action_target}"
        normalized = filepath.relative_to(self.repo_path).as_posix()
        if self.strict_scope and not self.allowed_paths:
            return "ERROR: Planner scope is empty; writes are disabled"
        if self.allowed_paths and normalized not in self.allowed_paths:
            return f"ERROR: Path is outside the planner scope: {path}"
        if self._approved_action_fingerprint == action_fingerprint:
            self._approved_action_fingerprint = None
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return f"OK: Wrote {path}"

    def run_command(self, command: str) -> str:
        """Roda comando shell.

        Args:
            command: Comando

        Returns:
            Output
        """
        allowed = {
            "pytest",
            "python",
            "python3",
            "git",
            "npm",
            "node",
            "pip",
            "pip3",
            "docker",
        }
        try:
            argv = shlex.split(command)
        except ValueError as error:
            return f"ERROR: Invalid command: {error}"
        if not argv or argv[0] not in allowed:
            return f"ERROR: Command not allowed: {argv[0] if argv else '(empty)'}"
        if argv[0] == "docker" and _docker_block_reason(argv):
            return f"ERROR: {_docker_block_reason(argv)}"
        sensitive_command = argv[0] in {"pip", "pip3", "npm", "node", "docker"} or (
            argv[0] in {"python", "python3"}
            and len(argv) > 2
            and argv[1:3] == ["-m", "pip"]
        )
        install_command = (
            argv[0] in {"pip", "pip3"}
            or (argv[0] == "npm" and len(argv) > 1 and argv[1] in {"install", "ci", "update"})
            or (
                argv[0] in {"python", "python3"}
                and len(argv) > 3
                and argv[1:4] == ["-m", "pip", "install"]
            )
        )
        specific_approval_required = install_command or argv[0] in {"node", "docker"} or (
            argv[0] == "npm" and not _is_npm_validation_command(argv)
        )
        if (
            sensitive_command
            and (self.require_action_approval or specific_approval_required)
            and self._approved_action_fingerprint
            != hashlib.sha256(f"run {command}".encode("utf-8")).hexdigest()
        ):
            if install_command:
                return "ERROR: Package installation is not allowed without action approval"
            return "ERROR: Sensitive command is not allowed without action approval"
        if argv[0] == "git":
            allowed_git_actions = {"status", "diff", "log", "show", "ls-files", "add", "commit"}
            if len(argv) < 2 or argv[1] not in allowed_git_actions:
                return f"ERROR: Git action not allowed: {argv[1] if len(argv) > 1 else '(empty)'}"
            if argv[1] in {"add", "commit"}:
                git_error = self._validate_git_write(argv)
                if git_error:
                    return f"ERROR: {git_error}"
        if argv[0] in {"pip", "pip3"} and (len(argv) < 2 or argv[1] != "install"):
            return "ERROR: Package installation is not allowed except via pip install"
        if self.command_count >= self.max_commands:
            return f"ERROR: Task command limit reached ({self.max_commands})"
        if sensitive_command and self._approved_action_fingerprint is not None:
            self._approved_action_fingerprint = None
        self.command_count += 1
        run_argv = argv
        if argv[0] == "git" and argv[1] in {"add", "commit"}:
            run_argv = self._git_write_argv(argv)
        result = run_bounded(
            run_argv,
            cwd=str(self.repo_path),
            timeout=self.command_timeout_seconds,
            env=sanitized_env(self._temp_env()),
            memory_mb=self.memory_limit_mb,
            cpu_seconds=self.cpu_limit_seconds,
            max_output_bytes=max(1, self.max_output_chars * 4),
        )
        if result.timed_out:
            return f"ERROR: Timeout ({self.command_timeout_seconds}s)"
        if result.limit_exceeded == "cpu":
            return f"ERROR: CPU time limit reached ({self.cpu_limit_seconds}s)"
        if result.limit_exceeded == "memory":
            return f"ERROR: Memory limit reached ({self.memory_limit_mb} MB)"
        output = result.stdout
        if result.stderr:
            output += "\nSTDERR: " + result.stderr
        output = output or f"Command exited with code {result.returncode}"
        if argv[0] == "git" and len(argv) > 1 and argv[1] in {"add", "commit"}:
            if self._approved_action_fingerprint == hashlib.sha256(
                f"run {command}".encode("utf-8")
            ).hexdigest():
                self._approved_action_fingerprint = None
        if result.output_truncated:
            output += (
                f"\n[output truncated at "
                f"{max(1, self.max_output_chars * 4)} bytes per stream]"
            )
        if len(output) > self.max_output_chars:
            output = (
                output[: self.max_output_chars]
                + f"\n[output truncated at {self.max_output_chars} characters]"
            )
        return output

    def _git_write_argv(self, argv: list[str]) -> list[str]:
        """Disable repository hooks for the narrowly-scoped local Git writes."""
        hooks_dir = Path(self._temp_env()["TMPDIR"]) / "empty-git-hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        return ["git", "-c", f"core.hooksPath={hooks_dir}", *argv[1:]]

    def _git_output(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
            env=sanitized_env(self._temp_env()),
        )
        return result.stdout.strip()

    def _validate_git_write(self, argv: list[str]) -> Optional[str]:
        """Constrain staging and commits to this issue's isolated planner scope."""
        if (
            not self.expected_branch
            or not self.issue_number
            or self.expected_branch != f"bastiao/issue-{self.issue_number}"
        ):
            return "Git writes require the expected issue branch"
        try:
            current_branch = self._git_output("branch", "--show-current")
        except (OSError, subprocess.SubprocessError) as error:
            return f"Unable to verify the current Git branch: {error}"
        if current_branch != self.expected_branch:
            return f"Git writes are restricted to {self.expected_branch}"

        if argv[1] == "add":
            paths = argv[2:]
            if paths[:1] == ["--"]:
                paths = paths[1:]
            if not paths or any(path.startswith("-") for path in paths):
                return "git add requires explicit repository-relative file paths"
            for path in paths:
                if any(character in path for character in (":", "*", "?", "[")):
                    return "Git pathspec syntax is not allowed"
                try:
                    resolved = self._safe_path(path)
                except ValueError:
                    return "Git staging path escapes the workspace"
                normalized = resolved.relative_to(self.repo_path).as_posix()
                if _is_sensitive_path(Path(normalized)):
                    return "Git staging of credential or Git metadata files is blocked"
                if self.strict_scope and normalized not in self.allowed_paths:
                    return f"Git staging path is outside the planner scope: {normalized}"
                if normalized not in self.allowed_paths:
                    return f"Git staging path is outside the planner scope: {normalized}"
                if resolved.exists() and not resolved.is_file():
                    return "Git staging is limited to individual files"
                if not resolved.exists():
                    try:
                        self._git_output("ls-files", "--error-unmatch", "--", normalized)
                    except (OSError, subprocess.SubprocessError):
                        return f"Git staging path does not exist: {normalized}"
            return None

        if len(argv) != 4 or argv[2] != "-m" or not argv[3].strip():
            return "git commit only allows `git commit -m <message>`"
        try:
            staged_paths = self._git_output("diff", "--cached", "--name-only").splitlines()
        except (OSError, subprocess.SubprocessError) as error:
            return f"Unable to verify staged Git files: {error}"
        if not staged_paths:
            return "Git commit requires staged files"
        for path in staged_paths:
            normalized = Path(path).as_posix()
            if _is_sensitive_path(Path(normalized)) or normalized not in self.allowed_paths:
                return f"Git commit contains a file outside the planner scope: {normalized}"
        return None

    def search_code(self, pattern: str) -> str:
        """Busca no codigo.

        Args:
            pattern: Pattern de busca

        Returns:
            Resultados
        """
        try:
            result = run_bounded(
                ["grep", "-r", "--include=*.py", pattern, "."],
                cwd=str(self.repo_path),
                timeout=self.command_timeout_seconds,
                env=sanitized_env(self._temp_env()),
                memory_mb=self.memory_limit_mb,
                cpu_seconds=self.cpu_limit_seconds,
                max_output_bytes=max(1, self.max_output_chars * 4),
            )
            if result.timed_out:
                return f"ERROR: Timeout ({self.command_timeout_seconds}s)"
            output = result.stdout or "No matches found"
            if result.stderr:
                output += "\nSTDERR: " + result.stderr
            if result.output_truncated:
                output += (
                    f"\n[output truncated at "
                    f"{max(1, self.max_output_chars * 4)} bytes per stream]"
                )
            if len(output) > self.max_output_chars:
                return (
                    output[: self.max_output_chars]
                    + f"\n[output truncated at {self.max_output_chars} characters]"
                )
            return output

        except OSError as error:
            return f"ERROR: {error}"

    def list_files(self, path: str = "") -> str:
        """Lista arquivos.

        Args:
            path: Caminho (vazio = raiz)

        Returns:
            Lista de arquivos
        """
        try:
            dirpath = self._safe_path(path) if path else self.repo_path
        except ValueError as error:
            return f"ERROR: {error}"

        if not dirpath.exists():
            return f"ERROR: Directory not found: {path}"

        files = []
        for item in dirpath.iterdir():
            prefix = "📁 " if item.is_dir() else "📄 "
            files.append(f"{prefix}{item.name}")

        return "\n".join(files) if files else "Empty directory"


if __name__ == "__main__":
    # Teste
    handler = ToolHandler()

    print("Test 1: List files")
    print(handler.list_files())

    print("\nTest 2: Read file")
    print(handler.read_file("README.md")[:200])

    print("\nTest 3: Write file")
    print(handler.write_file("test.txt hello world"))

    print("\nTest 4: Run command")
    print(handler.run_command("ls -la"))
