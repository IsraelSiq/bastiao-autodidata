"""Bastiao Autodidata - Main Entry Point

Agente autonomo que se auto-desenvolve.

Uso:
    python main.py

O Bastiao vai:
1. Ler issues do GitHub
2. Planejar implementacao
3. Escrever codigo
4. Testar
5. Comitar
6. Repetir
"""

import os
import logging

from src.swe_agent import SWEAgent
from src.github_client import GitHubClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main():
    """Main function."""
    owner = "IsraelSiq"
    repo = "bastiao-autodidata"
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        print("ERROR: GITHUB_TOKEN not set!")
        print("Please set GITHUB_TOKEN environment variable.")
        return

    print("="*60)
    print("BASTIAO AUTODIDATA - SWE-agent Implementation")
    print("="*60)
    print(f"\nRepository: {owner}/{repo}")
    print("\nStarting autonomous development...\n")

    # Inicializa
    client = GitHubClient(owner, repo, token)
    agent = SWEAgent()

    # Le issues abertas
    issues = client.list_issues(state="open")
    print(f"Found {len(issues)} open issues\n")

    # Processa cada issue
    for issue in issues[:5]:  # Limita a 5 issues
        print(f"\n{'='*60}")
        print(f"Processing issue #{issue.number}: {issue.title}")
        print(f"{'='*60}\n")

        # Tenta resolver
        success = agent.solve(
            issue_title=issue.title,
            issue_body=issue.body or "",
        )

        # Comenta na issue
        if success:
            client.add_comment(
                issue.number,
                f"✅ Implemented by Bastiao (SWE-agent)!",
            )
            print(f"Issue #{issue.number} solved!")
        else:
            client.add_comment(
                issue.number,
                f"❌ Failed to solve. Needs human help.",
            )
            print(f"Issue #{issue.number} failed.")

    print("\n" + "="*60)
    print("Development cycle complete!")
    print("="*60)


if __name__ == "__main__":
    main()
