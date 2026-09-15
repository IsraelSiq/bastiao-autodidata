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
import time
import requests

from src.autonomous import AutonomousRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main():
    """Main function."""
    required = ["GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_REPO", "BASTIAO_WORKSPACE"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print(f"ERROR: missing environment variables: {', '.join(missing)}")
        return

    print("="*60)
    print("BASTIAO AUTODIDATA - SWE-agent Implementation")
    print("="*60)
    print(f"\nRepository: {os.environ['GITHUB_OWNER']}/{os.environ['GITHUB_REPO']}")
    print("\nStarting autonomous development...\n")

    interval = max(300, int(os.getenv("BASTIAO_INTERVAL_SECONDS", "3600")))
    runner = AutonomousRunner(os.environ["BASTIAO_WORKSPACE"])
    while True:
        try:
            result = runner.run_once()
            print(f"Cycle complete: {result}", flush=True)
        except requests.RequestException as error:
            logging.getLogger("bastiao.main").error(
                "GitHub request failed; keeping service alive: %s",
                error,
            )
        except (OSError, ValueError) as error:
            logging.getLogger("bastiao.main").error(
                "Cycle failed with recoverable configuration/runtime error: %s",
                error,
            )
        time.sleep(interval)


if __name__ == "__main__":
    main()
