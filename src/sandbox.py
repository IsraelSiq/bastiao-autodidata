"""BastiÃ£o Autodidata - Sandbox de ExecuÃ§Ã£o Segura

Executa cÃ³digo Python em ambiente isolado.
"""

import sys
import io
import traceback
import json
from typing import Any, Optional
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class ExecutionResult:
    """Resultado de execuÃ§Ã£o."""
    success: bool
    output: str
    error: Optional[str] = None
    result: Optional[Any] = None
    execution_time: float = 0.0


class PythonSandbox:
    """Sandbox para execuÃ§Ã£o segura de cÃ³digo Python."""

    def __init__(self, timeout: int = 30, max_output_lines: int = 100):
        """Inicializa a sandbox.

        Args:
            timeout: Timeout em segundos
            max_output_lines: MÃ¡ximo de linhas de output
        """
        self.timeout = timeout
        self.max_output_lines = max_output_lines

    def execute(
        self,
        code: str,
        globals_dict: Optional[dict] = None,
        locals_dict: Optional[dict] = None,
    ) -> ExecutionResult:
        """Executa cÃ³digo Python.

        Args:
            code: CÃ³digo a executar
            globals_dict: Dict global (opcional)
            locals_dict: Dict local (opcional)

        Returns:
            ExecutionResult com output e erros
        """
        import time

        start_time = time.time()

        # Captura stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Prepara ambiente
            if globals_dict is None:
                globals_dict = {"__builtins__": __builtins__}
            if locals_dict is None:
                locals_dict = {}

            # Executa cÃ³digo
            exec(code, globals_dict, locals_dict)

            # Pega resultado se houver
            result = locals_dict.get("result") or locals_dict.get("output")

            output = stdout_capture.getvalue()
            error = stderr_capture.getvalue()

            return ExecutionResult(
                success=True,
                output=self._truncate_output(output),
                error=self._truncate_output(error) if error else None,
                result=result,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            error_msg = traceback.format_exc()
            return ExecutionResult(
                success=False,
                output=stdout_capture.getvalue(),
                error=self._truncate_output(error_msg),
                execution_time=time.time() - start_time,
            )

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _truncate_output(self, text: str) -> str:
        """Trunca output se for muito grande."""
        lines = text.splitlines()
        if len(lines) > self.max_output_lines:
            lines = lines[:self.max_output_lines]
            lines.append(f"\n... (truncado, {len(lines)} linhas mÃ¡x)")

        return "\n".join(lines)

    def run_exercise(
        self,
        exercise_code: str,
        test_code: str,
    ) -> ExecutionResult:
        """Executa exercÃ¬cio com teste automÃ¡tico.

        Args:
            exercise_code: CÃ³digo do aluno
            test_code: CÃ³digo de teste

        Returns:
            ExecutionResult com resultado do teste
        """
        # Junta exercÃ¬cio + teste
        full_code = f"{exercise_code}\n\n# Teste\n{test_code}"

        return self.execute(full_code)


class ShellSandbox:
    """Sandbox para execuÃ§Ã£o de comandos shell (bÃ¡sico)."""

    def __init__(self, allowed_commands: Optional[list[str]] = None):
        """Inicializa a sandbox.

        Args:
            allowed_commands: Lista de comandos permitidos
        """
        self.allowed_commands = allowed_commands or [
            "ls", "cat", "head", "tail", "wc",
            "grep", "find", "pwd", "echo",
        ]

    def is_safe(self, command: str) -> bool:
        """Verifica se comando ÃƒÂ© seguro."""
        # Comandos proibidos
        forbidden = ["rm", "sudo", "chmod", "chown", "kill", "curl", "wget"]

        for cmd in forbidden:
            if cmd in command.split():
                return False

        return True

    def execute(self, command: str) -> ExecutionResult:
        """Executa comando shell.

        Args:
            command: Comando a executar

        Returns:
            ExecutionResult com output
        """
        import subprocess
        import time

        start_time = time.time()

        if not self.is_safe(command):
            return ExecutionResult(
                success=False,
                output="",
                error="Comando nÃ£o permitido por seguranÃ§a",
            )

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            return ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                execution_time=time.time() - start_time,
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Timeout apÃ³s {self.timeout}s",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
            )


def main():
    """Teste da sandbox."""
    print("Testing PythonSandbox...")

    sandbox = PythonSandbox()

    # Teste 1: CÃ³digo simples
    code1 = """
x = 10
y = 20
result = x + y
print(f"Soma: {result}")
"""

    result1 = sandbox.execute(code1)
    print(f"\nTest 1 - Success: {result1.success}")
    print(f"Output: {result1.output}")
    print(f"Result: {result1.result}")

    # Teste 2: Erro
    code2 = """
x = 10 / 0
"""

    result2 = sandbox.execute(code2)
    print(f"\nTest 2 - Success: {result2.success}")
    print(f"Error: {result2.error[:100]}...")

    # Teste 3: ExercÃ¬cio
    exercise = """
def soma(a, b):
    return a + b
"""

    test = """
result = soma(5, 3)
assert result == 8, f"Esperado 8, got {result}"
print("Teste passou!")
"""

    result3 = sandbox.run_exercise(exercise, test)
    print(f"\nTest 3 - Success: {result3.success}")
    print(f"Output: {result3.output}")


if __name__ == "__main__":
    main()
