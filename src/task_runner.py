"""BastiÃ£o Autodidata - Interface de ExecuÃ§Ã£o de Tarefas

Interface principal para execuÃ§Ã£o de tarefas de estudo.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from .executor import TaskExecutor, TaskRunner, Task, TaskResult
from .sandbox import PythonSandbox, ShellSandbox
from .orchestrator import BastiaoOrchestrator
from .planner import StudyPlan
from .logging_config import get_logger

logger = get_logger("bastiao.task_runner")


class StudyTaskRunner:
    """Gerencia execuÃ§Ã£o de tarefas de estudo."""

    def __init__(
        self,
        orchestrator: BastiaoOrchestrator,
        data_dir: str = "data",
    ):
        """Inicializa o runner.

        Args:
            orchestrator: Orchestrator
            data_dir: DiretÃ³rio de dados
        """
        self.orchestrator = orchestrator
        self.executor = TaskExecutor(
            orchestrator,
            python_sandbox=PythonSandbox(),
            shell_sandbox=ShellSandbox(),
        )
        self.runner = TaskRunner(self.executor, checkpoint_dir=f"{data_dir}/checkpoints")
        self.data_dir = Path(data_dir)
        self.logger = logger

    def create_task_from_topic(
        self,
        topic: dict,
        topic_index: int,
    ) -> list[Task]:
        """Cria tarefas a partir de tÃ³pico do plano.

        Args:
            topic: TÃ³pico do plano
            topic_index: Ãndice do tÃ³pico

        Returns:
            Lista de tarefas
        """
        tasks = []

        # Tarefa 1: Estudo teÃ³rico
        tasks.append(Task(
            id=f"topic_{topic_index}_theory",
            name=f"Estudo: {topic['name']}",
            description=topic.get("description", ""),
            type="text",
            instructions=f"Estude: {topic.get('resources', [])}",
        ))

        # Tarefa 2: ExercÃ¬cios
        exercises = topic.get("exercises", [])
        for i, exercise in enumerate(exercises[:3], 1):
            tasks.append(Task(
                id=f"topic_{topic_index}_ex_{i}",
                name=f"ExercÃ¬cio {i}: {exercise[:50]}",
                description=exercise,
                type="code",
                instructions=f"Resolva: {exercise}",
            ))

        return tasks

    def run_topic(
        self,
        topic: dict,
        topic_index: int,
    ) -> list[TaskResult]:
        """Executa todas as tarefas de um tÃ³pico.

        Args:
            topic: TÃ³pico do plano
            topic_index: Ãndice do tÃ³pico

        Returns:
            Lista de resultados
        """
        tasks = self.create_task_from_topic(topic, topic_index)
        results = self.runner.run_tasks(tasks)

        return results

    def get_topic_progress(self, topic_index: int) -> dict:
        """ObtÃ©m progresso de um tÃ³pico.

        Args:
            topic_index: Ãndice do tÃ³pico

        Returns:
            Dict com progresso
        """
        # Simula tarefas
        dummy_tasks = [
            Task(id=f"topic_{topic_index}_theory", name="Theory", description="", type="text"),
            Task(id=f"topic_{topic_index}_ex_1", name="Exercise 1", description="", type="code"),
        ]

        return self.runner.get_progress(dummy_tasks)

    def mark_topic_complete(self, topic_index: int):
        """Marca tÃ³pico como completo.

        Args:
            topic_index: Ãndice do tÃ³pico
        """
        checkpoint = {
            "topic_index": topic_index,
            "completed": True,
            "timestamp": datetime.now().isoformat(),
        }

        filepath = self.data_dir / "checkpoints" / f"topic_{topic_index}.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2)

        self.logger.info(f"Topic {topic_index} marked complete")

    def is_topic_complete(self, topic_index: int) -> bool:
        """Verifica se tÃ³pico estÃ¡ completo.

        Args:
            topic_index: Ãndice do tÃ³pico

        Returns:
            True se completo
        """
        filepath = self.data_dir / "checkpoints" / f"topic_{topic_index}.json"

        if not filepath.exists():
            return False

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("completed", False)


def main():
    """Teste do task runner."""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    orchestrator = BastiaoOrchestrator()
    runner = StudyTaskRunner(orchestrator)

    # Simula tÃ³pico
    topic = {
        "name": "VariÃ¡veis e Tipos de Dados",
        "description": "Aprender variÃ¡veis e tipos",
        "resources": ["Python.org", "Real Python"],
        "exercises": [
            "Crie variÃ¡veis de diferentes tipos",
            "FaÃ§a conversÃµes entre tipos",
        ],
    }

    print("Creating tasks from topic...\n")
    tasks = runner.create_task_from_topic(topic, 0)

    print(f"Tasks created: {len(tasks)}")
    for task in tasks:
        print(f"  - {task.id}: {task.name}")

    print("\nRunning tasks...\n")
    results = runner.run_tasks(tasks)

    print(f"\nCompleted: {sum(1 for r in results if r.success)}/{len(results)}")


if __name__ == "__main__":
    main()
