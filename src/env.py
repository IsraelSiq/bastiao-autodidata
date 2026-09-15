"""Bastiao - Environment

Ambiente de execucao do agente.
"""

from dataclasses import dataclass
from typing import Optional

from .tools import ToolHandler


@dataclass
class EnvState:
    """Estado do ambiente."""
    current_file: Optional[str] = None
    last_command: Optional[str] = None
    last_output: Optional[str] = None
    error: Optional[str] = None


class SandboxEnv:
    """Ambiente sandbox do agente."""

    def __init__(
        self,
        repo_path: str = ".",
        allowed_paths: Optional[list[str]] = None,
        strict_scope: bool = False,
    ):
        """Inicializa o ambiente.

        Args:
            repo_path: Caminho do repositorio
        """
        self.repo_path = repo_path
        self.tools = ToolHandler(
            repo_path,
            allowed_paths=allowed_paths,
            strict_scope=strict_scope,
        )
        self.state = EnvState()

    def execute_action(self, action: str) -> str:
        """Executa acao.

        Args:
            action: Acao

        Returns:
            Resultado
        """
        self.state.last_command = action

        try:
            result = self.tools.execute(action)
            self.state.last_output = result
            self.state.error = None
            return result

        except Exception as e:
            self.state.error = str(e)
            return f"ERROR: {e}"

    def get_state(self) -> EnvState:
        """Pega estado atual.

        Returns:
            Estado
        """
        return self.state

    def reset(self):
        """Reseta o ambiente."""
        self.state = EnvState()


if __name__ == "__main__":
    # Teste
    env = SandboxEnv()

    print("Test 1: List files")
    result = env.execute_action("list .")
    print(result)

    print("\nTest 2: Read file")
    result = env.execute_action("read README.md")
    print(result[:200])

    print("\nState:", env.get_state())
