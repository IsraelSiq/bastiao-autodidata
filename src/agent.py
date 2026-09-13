"""Bastiao - Autonomous Agent

Agente autonomo que se auto-desenvolve.
"""

import logging
from typing import Optional

from .github_client import GitHubClient, GitHubIssue
from .planner import Planner, Task
from .coder import Coder, CodeFile
from .tester import Tester, TestResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("bastiao.agent")


class BastiaoAgent:
    """Agente autonomo do Bastiao."""

    def __init__(
        self,
        owner: str,
        repo: str,
        github_token: Optional[str] = None,
    ):
        """Inicializa o agente.

        Args:
            owner: Owner do repo
            repo: Nome do repo
            github_token: Token do GitHub
        """
        self.client = GitHubClient(owner, repo, github_token)
        self.planner = Planner()
        self.coder = Coder()
        self.tester = Tester()
        self.owner = owner
        self.repo = repo

        logger.info(f"BastiaoAgent initialized: {owner}/{repo}")

    def run_cycle(self) -> dict:
        """Roda um ciclo de desenvolvimento.

        Returns:
            Dict com estatisticas
        """
        logger.info("Starting development cycle...")

        stats = {
            "issues_processed": 0,
            "tasks_created": 0,
            "files_created": 0,
            "tests_passed": 0,
            "commits_made": 0,
        }

        # 1. Le issues
        issues = self.client.list_issues(state="open")
        logger.info(f"Found {len(issues)} open issues")

        # 2. Processa cada issue
        for issue in issues[:5]:  # Limita a 5 issues por ciclo
            logger.info(f"Processing issue #{issue.number}: {issue.title}")

            # 3. Planeja
            tasks = self.planner.plan_issue(issue)
            stats["tasks_created"] += len(tasks)

            # 4. Gera codigo
            all_files = []
            for task in tasks:
                files = self.coder.generate_code(task)
                all_files.extend(files)

            stats["files_created"] += len(all_files)

            # 5. Testa
            if all_files:
                test_results = self.tester.run_tests(all_files)
                stats["tests_passed"] += sum(1 for r in test_results if r.success)

                # 6. Comita se testes passaram
                if all(r.success for r in test_results):
                    files_data = [{"path": f.path, "content": f.content} for f in all_files]
                    if files_data:
                        self.client.commit_files(
                            files=files_data,
                            message=f"feat: implement {issue.title} (via Bastiao)",
                        )
                        stats["commits_made"] += 1

                        # Comenta na issue
                        self.client.add_comment(
                            issue.number,
                            f"✅ Implemented by Bastiao! Commit: {len(files_data)} files created.",
                        )

                        # Fecha issue
                        self.client.close_issue(issue.number)
                        logger.info(f"Issue #{issue.number} closed")

            stats["issues_processed"] += 1

        logger.info(f"Cycle complete: {stats}")

        return stats

    def run_loop(self, max_cycles: int = 10):
        """Roda loop autonomo.

        Args:
            max_cycles: Maximo de ciclos
        """
        logger.info(f"Starting autonomous loop (max {max_cycles} cycles)...")

        for i in range(max_cycles):
            logger.info(f"\n{'='*60}")
            logger.info(f"Cycle {i+1}/{max_cycles}")
            logger.info(f"{'='*60}\n")

            stats = self.run_cycle()

            # Se nao processou nada, para
            if stats["issues_processed"] == 0:
                logger.info("No more issues to process. Stopping.")
                break

        logger.info("\nAutonomous loop complete!")


def main():
    """Main function."""
    import os

    owner = "IsraelSiq"
    repo = "bastiao-autodidata"
    token = os.getenv("GITHUB_TOKEN")

    agent = BastiaoAgent(owner, repo, token)
    agent.run_loop(max_cycles=3)


if __name__ == "__main__":
    main()
