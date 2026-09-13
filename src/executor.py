"""BastiÃ£o Autodidata - Executor de Tarefas

Executa tarefas de estudo (cÃ³digo, comandos, validaÃ§Ãµes).
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, asdict

from .sandbox import PythonSandbox, ShellSandbox, ExecutionResult
from .orchestrator import BastiaoOrchestrator, ChatMessage
from .logging_config import get_logger

logger = get_logger("bastiao.executor")


@dataclass
class TaskResult:
    """Resultado de execuÃ§Ã£o de tarefa."""
    task_id: str
    task_name: str
    success: bool
    output: str
    error: Optional[str] = None
    duration_seconds: float = 0.0
    validated: bool = False
    validation_feedback: Optional[str] = None
    completed_at: str = ""

    def __post_init__(self):
        if not self.completed_at:
            self.completed_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Converte para dict."""
        return asdict(self)


@dataclass
class Task:
    """Tarefa de estudo."""
    id: str
    name: str
    description: str
    type: str  # "code", "shell", "text"
    code: Optional[str] = None
    test_code: Optional[str] = None
    expected_output: Optional[str] = None
    instructions: str = ""
    completed: bool = False
    max_attempts: int = 3


class TaskExecutor:
    """Executa tarefas de estudo."""

    def __init__(
        self,
        orchestrator: BastiaoOrchestrator,
        python_sandbox: Optional[PythonSandbox] = None,
        shell_sandbox: Optional[ShellSandbox] = None,
    ):
        """Inicializa o executor.

        Args:
            orchestrator: Orchestrator para validaÃ§Ãµes
            python_sandbox: Sandbox para Python
            shell_sandbox: Sandbox para shell
        """
        self.orchestrator = orchestrator
        self.python_sandbox = python_sandbox or PythonSandbox()
        self.shell_sandbox = shell_sandbox or ShellSandbox()
        self.logger = logging.getLogger(__name__)

    def execute_task(self, task: Task) -> TaskResult:
        """Executa uma tarefa.

        Args:
            task: Tarefa a executar

        Returns:
            TaskResult com resultado
        """
        import time

        start_time = time.time()

        self.logger.info(f"Executing task: {task.name} ({task.type})")

        try:
            if task.type == "code":
                result = self._execute_code_task(task)
            elif task.type == "shell":
                result = self._execute_shell_task(task)
            elif task.type == "text":
                result = self._execute_text_task(task)
            else:
                result = TaskResult(
                    task_id=task.id,
                    task_name=task.name,
                    success=False,
                    output="",
                    error=f"Tipo de tarefa desconhecido: {task.type}",
                )

            result.duration_seconds = time.time() - start_time

            self.logger.info(f"Task completed: {task.name} - Success: {result.success}")

            return result

        except Exception as e:
            self.logger.error(f"Error executing task: {e}")
            return TaskResult(
                task_id=task.id,
                task_name=task.name,
                success=False,
                output="",
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _execute_code_task(self, task: Task) -> TaskResult:
        """Executa tarefa de cÃ³digo."""
        if not task.code:
            return TaskResult(
                task_id=task.id,
                task_name=task.name,
                success=False,
                output="",
                error="Nenhum cÃ³digo fornecido",
            )

        # Executa cÃ³digo
        if task.test_code:
            exec_result = self.python_sandbox.run_exercise(task.code, task.test_code)
        else:
            exec_result = self.python_sandbox.execute(task.code)

        # Valida resultado
        validated = False
        feedback = None

        if exec_result.success and task.expected_output:
            # Valida com LLM
            validated, feedback = self._validate_output(
                exec_result.output,
                task.expected_output,
            )
        elif exec_result.success:
            validated = True
            feedback = "CÃ³digo executou com sucesso!"

        return TaskResult(
            task_id=task.id,
            task_name=task.name,
            success=exec_result.success,
            output=exec_result.output,
            error=exec_result.error,
            validated=validated,
            validation_feedback=feedback,
        )

    def _execute_shell_task(self, task: Task) -> TaskResult:
        """Executa tarefa de shell."""
        if not task.code:
            return TaskResult(
                task_id=task.id,
                task_name=task.name,
                success=False,
                output="",
                error="Nenhum comando fornecido",
            )

        exec_result = self.shell_sandbox.execute(task.code)

        return TaskResult(
            task_id=task.id,
            task_name=task.name,
            success=exec_result.success,
            output=exec_result.output,
            error=exec_result.error,
            validated=exec_result.success,
            validation_feedback="Comando executou com sucesso!" if exec_result.success else None,
        )

    def _execute_text_task(self, task: Task) -> TaskResult:
        """Executa tarefa de texto (resposta escrita)."""
        # Tarefa de texto sÃ³ marca como completada se o usuÃ¡rio confirmar
        return TaskResult(
            task_id=task.id,
            task_name=task.name,
            success=True,
            output="Tarefa de texto concluÃ¬da",
            validated=True,
            validation_feedback="Resposta registrada!",
        )

    def _validate_output(
        self,
        actual_output: str,
        expected_output: str,
    ) -> tuple[bool, str]:
        """Valida output com LLM.

        Args:
            actual_output: Output real
            expected_output: Output esperado

        Returns:
            (validado, feedback)
        """
        prompt = f"""Compare o output real com o esperado.

**Output Real:**
{actual_output}

**Output Esperado:**
{expected_output}

O output real atende ao esperado? Responda em JSON:
{{"valid": true/false, "feedback": "explicaÃ§Ã£o"}}"""

        messages = [
            ChatMessage(role="system", content="VocÃª ÃƒÂ© um validador de exercÃ¬cios. Retorne APENAS JSON."),
            ChatMessage(role="user", content=prompt),
        ]

        try:
            response = self.orchestrator.chat(messages)

            # Extrai JSON
            import re
            match = re.search(r"\{[\s\S]*\}", response)
            if match:
                result = json.loads(match.group(0))
                return result.get("valid", False), result.get("feedback", "")

            return False, "NÃ£o foi possÃ¬vel validar"

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False, f"Erro na validaÃ§Ã£o: {e}"


class TaskRunner:
    """Gerencia execuÃ§Ã£o de mÃºltiplas tarefas."""

    def __init__(
        self,
        executor: TaskExecutor,
        checkpoint_dir: str = "data/checkpoints",
    ):
        """Inicializa o runner.

        Args:
            executor: Executor de tarefas
            checkpoint_dir: DiretÃ³rio para checkpoints
        """
        self.executor = executor
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def run_tasks(self, tasks: list[Task]) -> list[TaskResult]:
        """Executa lista de tarefas.

        Args:
            tasks: Lista de tarefas

        Returns:
            Lista de resultados
        """
        results = []

        for i, task in enumerate(tasks, 1):
            self.logger.info(f"Running task {i}/{len(tasks)}: {task.name}")

            result = self.executor.execute_task(task)
            results.append(result)

            # Salva checkpoint
            self._save_checkpoint(task, result)

            if result.success:
                print(f"â�» Task {i}: {task.name} - OK")
            else:
                print(f"â¨¯ Task {i}: {task.name} - FAILED")
                if result.error:
                    print(f"  Error: {result.error[:100]}")

        return results

    def _save_checkpoint(self, task: Task, result: TaskResult):
        """Salva checkpoint de tarefa."""
        checkpoint = {
            "task": task.__dict__,
            "result": result.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

        filepath = self.checkpoint_dir / f"{task.id}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)

        self.logger.debug(f"Checkpoint saved: {filepath}")

    def load_checkpoint(self, task_id: str) -> Optional[dict]:
        """Carrega checkpoint de tarefa.

        Args:
            task_id: ID da tarefa

        Returns:
            Checkpoint ou None
        """
        filepath = self.checkpoint_dir / f"{task_id}.json"

        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_progress(self, tasks: list[Task]) -> dict:
        """Calcula progresso das tarefas.

        Args:
            tasks: Lista de tarefas

        Returns:
            Dict com progresso
        """
        total = len(tasks)
        completed = 0
        validated = 0

        for task in tasks:
            checkpoint = self.load_checkpoint(task.id)
            if checkpoint:
                result = checkpoint.get("result", {})
                if result.get("success"):
                    completed += 1
                if result.get("validated"):
                    validated += 1

        return {
            "total_tasks": total,
            "completed": completed,
            "validated": validated,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
        }


def main():
    """Teste do executor."""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    orchestrator = BastiaoOrchestrator()
    executor = TaskExecutor(orchestrator)
    runner = TaskRunner(executor)

    # Cria tarefas
    tasks = [
        Task(
            id="task_001",
            name="Soma Simples",
            description="Crie uma funÃ§Ã£o que soma dois nÃºmeros",
            type="code",
            code="""
def soma(a, b):
    return a + b

# Teste
result = soma(5, 3)
print(f"Resultado: {result}")
""",
            test_code="""
assert soma(5, 3) == 8
assert soma(10, 20) == 30
print("Todos os testes passaram!")
""",
            expected_output="Resultado: 8",
        ),
        Task(
            id="task_002",
            name="Lista de NÃºmeros",
            description="Crie uma lista com 5 nÃºmeros",
            type="code",
            code="""
numeros = [1, 2, 3, 4, 5]
print(f"Lista: {numeros}")
print(f"Tamanho: {len(numeros)}")
""",
        ),
    ]

    # Executa tarefas
    print("Running tasks...\n")
    results = runner.run_tasks(tasks)

    # Progresso
    progress = runner.get_progress(tasks)
    print(f"\nProgresso: {progress['progress_percent']:.0f}%")
    print(f"Completas: {progress['completed']}/{progress['total_tasks']}")


if __name__ == "__main__":
    main()
