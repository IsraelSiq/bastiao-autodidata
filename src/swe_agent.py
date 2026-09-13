"""Bastiao - SWE-agent Implementation

Agente baseado no SWE-agent (Princeton NLP).

Referencia: https://github.com/swe-agent/swe-agent
"""

import logging
from typing import Optional

from .model import OmniRouteModel
from .env import SandboxEnv, EnvState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("bastiao.swe_agent")


class SWEAgent:
    """SWE-agent simplificado."""

    SYSTEM_PROMPT = """You are a software engineering agent that fixes issues in GitHub repositories.

You have access to these tools:
- read <path>: Read a file
- write <path> <content>: Write to a file
- run <command>: Run a shell command
- search <pattern>: Search code
- list [path]: List files

Rules:
1. Always read files before editing
2. Test your changes with 'run'
3. Use search to find relevant code
4. Make small, incremental changes
5. Always verify your changes work

Respond with actions in this format:
```
read src/main.py
```

Or chain multiple actions:
```
read src/main.py
write src/main.py print("Hello")
run python src/main.py
```
"""

    def __init__(
        self,
        model: Optional[OmniRouteModel] = None,
        env: Optional[SandboxEnv] = None,
        max_iterations: int = 20,
    ):
        """Inicializa o agente.

        Args:
            model: Modelo (OmniRoute)
            env: Ambiente (sandbox)
            max_iterations: Maximo de iteracoes
        """
        self.model = model or OmniRouteModel()
        self.env = env or SandboxEnv()
        self.max_iterations = max_iterations
        self.history = []

        logger.info("SWEAgent initialized")

    def solve(self, issue_title: str, issue_body: str = "") -> bool:
        """Tenta resolver uma issue.

        Args:
            issue_title: Titulo da issue
            issue_body: Descricao da issue

        Returns:
            True se resolveu
        """
        logger.info(f"Solving issue: {issue_title}")

        self.env.reset()
        self.history = []

        # Prompt inicial
        user_prompt = f"""Issue: {issue_title}

Description: {issue_body or 'No description'}

Your task: Fix this issue by reading, editing, and testing code.
Start by exploring the repository structure.

Current state:
{self._format_state()}

What's your first action?"""

        # Loop principal
        for i in range(self.max_iterations):
            logger.info(f"Iteration {i+1}/{self.max_iterations}")

            # 1. Query o modelo
            try:
                response = self.model.query(
                    system_prompt=self.SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )
            except Exception as e:
                logger.error(f"Model error: {e}")
                return False

            self.history.append({"model_response": response})

            # 2. Extrai acoes
            actions = self._parse_actions(response)
            if not actions:
                logger.warning("No actions found in response")
                break

            # 3. Executa acoes
            outputs = []
            for action in actions:
                output = self.env.execute_action(action)
                outputs.append(f"{action}\n{output}")

            # 4. Prepara proximo prompt
            user_prompt = f"""Previous actions:
{chr(10).join(outputs)}

Current state:
{self._format_state()}

What's your next action? (or say 'DONE' if finished)"""

            # 5. Checa se terminou
            if "DONE" in response.upper() or "FINISHED" in response.upper():
                logger.info("Agent finished")
                return True

        logger.warning("Max iterations reached")
        return False

    def _parse_actions(self, response: str) -> list[str]:
        """Extrai acoes da resposta.

        Args:
            response: Resposta do modelo

        Returns:
            Lista de acoes
        """
        # Tenta extrair de code blocks
        import re

        # Pattern 1: Code blocks
        matches = re.findall(r"```(?:\w+)?\s*([\s\S]*?)\s*```", response)
        if matches:
            actions = []
            for match in matches:
                actions.extend([line.strip() for line in match.splitlines() if line.strip()])
            return actions

        # Pattern 2: Linhas individuais
        actions = []
        for line in response.splitlines():
            line = line.strip()
            if line and any(line.startswith(cmd) for cmd in ["read", "write", "run", "search", "list"]):
                actions.append(line)

        return actions

    def _format_state(self) -> str:
        """Formata estado atual.

        Returns:
            Estado formatado
        """
        state = self.env.get_state()
        return f"""Last command: {state.last_command or 'None'}
Last output: {(state.last_output or 'None')[:500]}"""


def main():
    """Teste do agente."""
    agent = SWEAgent()

    # Testa com issue simples
    success = agent.solve(
        issue_title="Create hello.py that prints 'Hello World'",
        issue_body="Create a file src/hello.py that prints 'Hello World' when run.",
    )

    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")


if __name__ == "__main__":
    main()
