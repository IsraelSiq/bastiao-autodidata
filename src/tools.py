"""Bastiao - Tools (ACI - Agent Computer Interface)

Ferramentas que o agente pode usar.
"""

import subprocess
import os
from pathlib import Path
from typing import Optional


class ToolHandler:
    """Gerencia ferramentas do agente."""

    def __init__(self, repo_path: str = "."):
        """Inicializa o handler.

        Args:
            repo_path: Caminho do repositorio
        """
        self.repo_path = Path(repo_path)

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
        else:
            return f"ERROR: Unknown command '{command}'"

    def read_file(self, path: str) -> str:
        """Le arquivo.

        Args:
            path: Caminho do arquivo

        Returns:
            Conteudo do arquivo
        """
        filepath = self.repo_path / path
        if not filepath.exists():
            return f"ERROR: File not found: {path}"

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

        filepath = self.repo_path / path
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
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.repo_path),
            )

            output = result.stdout
            if result.stderr:
                output += "\nSTDERR: " + result.stderr

            return output or f"Command exited with code {result.returncode}"

        except subprocess.TimeoutExpired:
            return "ERROR: Timeout (60s)"
        except Exception as e:
            return f"ERROR: {e}"

    def search_code(self, pattern: str) -> str:
        """Busca no codigo.

        Args:
            pattern: Pattern de busca

        Returns:
            Resultados
        """
        try:
            result = subprocess.run(
                ["grep", "-r", "--include=*.py", pattern, str(self.repo_path)],
                capture_output=True,
                text=True,
                timeout=30,
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
        dirpath = self.repo_path / path if path else self.repo_path

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
