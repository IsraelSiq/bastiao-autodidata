"""Bastiao - Tester

Roda testes do codigo gerado.
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .coder import CodeFile


@dataclass
class TestResult:
    """Resultado de teste."""
    success: bool
    output: str
    error: Optional[str] = None


class Tester:
    """Roda testes."""

    def __init__(self, test_dir: str = "tests", repo_path: str = "."):
        """Inicializa o tester.

        Args:
            test_dir: Diretorio de testes
        """
        self.test_dir = Path(test_dir)
        self.repo_path = Path(repo_path)

    def run_tests(self, files: list[CodeFile]) -> list[TestResult]:
        """Roda testes dos arquivos.

        Args:
            files: Arquivos

        Returns:
            Lista de resultados
        """
        results = []

        # Roda pytest se existir
        if self.test_dir.exists():
            result = self._run_pytest()
            results.append(result)

        # Testa sintaxe Python
        for file in files:
            if file.path.endswith(".py"):
                result = self._check_syntax(file)
                results.append(result)

        return results

    def _run_pytest(self) -> TestResult:
        """Roda pytest."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(self.test_dir), "-v"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.repo_path),
            )

            return TestResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )

        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                output="",
                error="Timeout",
            )
        except Exception as e:
            return TestResult(
                success=False,
                output="",
                error=str(e),
            )

    def _check_syntax(self, file: CodeFile) -> TestResult:
        """Checa sintaxe Python."""
        try:
            compile(file.content, file.path, "exec")
            return TestResult(
                success=True,
                output=f"Syntax OK: {file.path}",
            )
        except SyntaxError as e:
            return TestResult(
                success=False,
                output="",
                error=f"Syntax error in {file.path}: {e}",
            )


if __name__ == "__main__":
    # Teste
    from .coder import CodeFile

    files = [
        CodeFile(
            path="src/test.py",
            content='print("Hello")\n',
            description="Test",
        )
    ]

    tester = Tester()
    results = tester.run_tests(files)

    print(f"Results: {len(results)}")
    for result in results:
        print(f"  - Success: {result.success}")
        if result.error:
            print(f"    Error: {result.error[:100]}")
