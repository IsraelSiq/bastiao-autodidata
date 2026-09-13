"""Bastiao - Planner

Planeja implementacao baseado em issues.
"""

from dataclasses import dataclass
from typing import Optional

from .github_client import GitHubIssue


@dataclass
class Task:
    """Task de implementacao."""
    title: str
    description: str
    files_to_create: list[str]
    files_to_modify: list[str]
    tests_needed: list[str]
    priority: int = 1


class Planner:
    """Planeja tasks baseado em issues."""

    def __init__(self):
        """Inicializa o planner."""
        pass

    def plan_issue(self, issue: GitHubIssue) -> list[Task]:
        """Cria plano de implementacao para uma issue.

        Args:
            issue: Issue

        Returns:
            Lista de tasks
        """
        # Analisa a issue e cria tasks
        # Isso aqui vai usar LLM pra gerar o plano

        title = issue.title.lower()

        # Heuristica simples por enquanto
        if "criar" in title or "create" in title:
            return self._plan_create_task(issue)
        elif "atualizar" in title or "update" in title:
            return self._plan_update_task(issue)
        elif "teste" in title or "test" in title:
            return self._plan_test_task(issue)
        else:
            return self._plan_generic_task(issue)

    def _plan_create_task(self, issue: GitHubIssue) -> list[Task]:
        """Planeja task de criacao."""
        task = Task(
            title=f"Implementar: {issue.title}",
            description=issue.body or "",
            files_to_create=[],
            files_to_modify=[],
            tests_needed=[],
            priority=1,
        )

        # Tenta extrair nome do arquivo do titulo
        if ".py" in issue.title:
            filename = issue.title.split(".py")[0] + ".py"
            if "src/" not in filename:
                filename = f"src/{filename}"
            task.files_to_create.append(filename)

        return [task]

    def _plan_update_task(self, issue: GitHubIssue) -> list[Task]:
        """Planeja task de atualizacao."""
        task = Task(
            title=f"Atualizar: {issue.title}",
            description=issue.body or "",
            files_to_create=[],
            files_to_modify=[],
            tests_needed=[],
            priority=2,
        )

        return [task]

    def _plan_test_task(self, issue: GitHubIssue) -> list[Task]:
        """Planeja task de teste."""
        task = Task(
            title=f"Testar: {issue.title}",
            description=issue.body or "",
            files_to_create=[],
            files_to_modify=[],
            tests_needed=["tests/"],
            priority=3,
        )

        return [task]

    def _plan_generic_task(self, issue: GitHubIssue) -> list[Task]:
        """Planeja task generica."""
        task = Task(
            title=f"Implementar: {issue.title}",
            description=issue.body or "",
            files_to_create=[],
            files_to_modify=[],
            tests_needed=[],
            priority=1,
        )

        return [task]


if __name__ == "__main__":
    # Teste
    from .github_client import GitHubIssue

    issue = GitHubIssue(
        number=1,
        title="Criar modulo orchestrator",
        body="Criar orchestrator.py",
        labels=["enhancement"],
        state="open",
    )

    planner = Planner()
    tasks = planner.plan_issue(issue)

    print(f"Tasks: {len(tasks)}")
    for task in tasks:
        print(f"  - {task.title}")
        print(f"    Files to create: {task.files_to_create}")
