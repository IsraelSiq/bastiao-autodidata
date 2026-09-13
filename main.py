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

from src.agent import BastiaoAgent

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
    print("BASTIAO AUTODIDATA - Autonomous Self-Developing Agent")
    print("="*60)
    print(f"\nRepository: {owner}/{repo}")
    print("\nStarting autonomous development loop...\n")

    agent = BastiaoAgent(owner, repo, token)
    agent.run_loop(max_cycles=10)

    print("\n" + "="*60)
    print("Development complete!")
    print("="*60)


if __name__ == "__main__":
    main()
