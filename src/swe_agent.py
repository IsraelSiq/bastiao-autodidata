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

    SYSTEM_PROMPT = """You are a software engineering agent. You MUST respond with actions only.

AVAILABLE ACTIONS:
- read <path>: Read a file
- write <path> <content>: Write to a file  
- run <command>: Run a shell command
- search <pattern>: Search code
- list [path]: List files

RESPONSE FORMAT:
You MUST respond with ONLY actions, one per line. NO explanations.

Example response:
list src
read src/main.py
write src/hello.py print("Hello World")
run python src/hello.py

RULES:
1. ALWAYS use actions, never explanations
2. Read files before editing
3. Test changes with 'run'
4. Say 'DONE' when finished

Current task:"""

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

    def solve(self, issue_title: str, issue_body: str = "", plan: str = "") -> bool:
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

Structured plan:
{plan or 'Follow inspect, implement, verify, and review steps.'}

Task: Fix this issue.

Start by exploring the repository.

Respond with actions ONLY:
"""

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
            logger.info(f"Model response: {response[:200]}")

            # 2. Extrai acoes
            actions = self._parse_actions(response)
            logger.info(f"Parsed actions: {actions}")
            
            if not actions:
                logger.warning("No actions found in response")
                # Tenta uma ultima vez com prompt mais direto
                if i == self.max_iterations - 1:
                    return False
                user_prompt = f"""You MUST respond with actions.

Previous response: {response}

This is NOT valid. Respond with actions like:
read src/main.py
write src/test.py print("hello")

Current state:
{self._format_state()}

Respond with actions NOW:"""
                continue

            # 3. Executa acoes
            outputs = []
            for action in actions:
                output = self.env.execute_action(action)
                outputs.append(f"{action}\n=> {output[:200]}")
                logger.info(f"Action: {action} => {output[:100]}")

            # 4. Prepara proximo prompt
            user_prompt = f"""Previous actions:
{chr(10).join(outputs)}

Current state:
{self._format_state()}

What's your next action? Respond with actions ONLY.
Say 'DONE' if finished."""

            # 5. Checa se terminou
            if "DONE" in response.upper() or "FINISHED" in response.upper():
                logger.info("Agent finished; external quality gates must still pass")
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
                for line in match.splitlines():
                    line = line.strip()
                    if line and any(line.startswith(cmd) for cmd in ["read", "write", "run", "search", "list", "DONE", "FINISHED"]):
                        actions.append(line)
            if actions:
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
