"""Bastiao - Tools (ACI - Agent Computer Interface)

Ferramentas que o agente pode usar.
"""

import subprocess
import shlex
from pathlib import Path
from typing import Optional


class ToolHandler:
    """Gerencia ferramentas do agente."""

    def __init__(self, repo_path: str = ".", allowed_paths: Optional[list[str]] = None):
        """Inicializa o handler.

        Args:
            repo_path: Caminho do repositorio
        """
        self.repo_path = Path(repo_path).resolve()
        self.allowed_paths = {
            path.replace("\\", "/").lstrip("./") for path in (allowed_paths or [])
        }

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

        try:
            filepath = self._safe_path(path)
        except ValueError as error:
            return f"ERROR: {error}"
        normalized = filepath.relative_to(self.repo_path).as_posix()
        if self.allowed_paths and normalized not in self.allowed_paths:
            return f"ERROR: Path is outside the planner scope: {path}"
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
        }
        try:
            argv = shlex.split(command)
        except ValueError as error:
            return f"ERROR: Invalid command: {error}"
        if not argv or argv[0] not in allowed:
            return f"ERROR: Command not allowed: {argv[0] if argv else '(empty)'}"
        if argv[0] == "git":
            allowed_git_actions = {"status", "diff", "log", "show", "ls-files"}
            if len(argv) < 2 or argv[1] not in allowed_git_actions:
                return f"ERROR: Git action not allowed: {argv[1] if len(argv) > 1 else '(empty)'}"
        if (
            argv[0] in {"pip", "pip3"}
            or (argv[0] in {"python", "python3"} and len(argv) > 2 and argv[1:3] == ["-m", "pip"])
            or (argv[0] == "npm" and len(argv) > 1 and argv[1] in {"install", "ci", "update"})
        ):
            return "ERROR: Package installation is not allowed during an autonomous task"
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.repo_path),
                check=False,
            )
            output = result.stdout
            if result.stderr:
                output += "\nSTDERR: " + result.stderr
            return output or f"Command exited with code {result.returncode}"
        except subprocess.TimeoutExpired:
            return "ERROR: Timeout (60s)"

    def search_code(self, pattern: str) -> str:
        """Busca no codigo.

        Args:
            pattern: Pattern de busca

        Returns:
            Resultados
        """
        try:
            result = subprocess.run(
                ["grep", "-r", "--include=*.py", pattern, "."],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.repo_path),
            )

            return result.stdout or "No matches found"

        except Exception as e:
            return f"ERROR: {e}"

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
