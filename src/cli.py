"""BastiÃ£o Autodidata - Interface CLI

Interface de linha de comando para o BastiÃ£o.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from .orchestrator import BastiaoOrchestrator, ChatMessage
from .planner import StudyPlanner, StudyPlan
from .study_plan import StudyPlanManager
from .executor import TaskExecutor, Task
from .task_runner import StudyTaskRunner, TaskRunner
from .sandbox import PythonSandbox, ShellSandbox
from .logging_config import get_logger

logger = get_logger("bastiao.cli")


class BastiaoCLI:
    """Interface CLI do BastiÃ£o."""

    def __init__(self, data_dir: str = "data"):
        """Inicializa a CLI.

        Args:
            data_dir: DiretÃ³rio de dados
        """
        self.orchestrator = BastiaoOrchestrator()
        self.plan_manager = StudyPlanManager(self.orchestrator, data_dir=data_dir)
        self.task_runner = StudyTaskRunner(self.orchestrator, data_dir=data_dir)
        self.data_dir = Path(data_dir)
        self.logger = logger

    def cmd_plan(
        self,
        topic: str,
        level: str = "iniciante",
        objective: str = "",
        hours_per_day: int = 2,
    ):
        """Cria plano de estudo.

        Args:
            topic: TÃ³pico a estudar
            level: NÃ¬vel atual
            objective: Objetivo
            hours_per_day: Horas por dia
        """
        print(f"\nð§¡§ Criando plano de estudo: {topic}\n")

        plan = self.plan_manager.create_plan(
            topic=topic,
            level=level,
            objective=objective,
            hours_per_day=hours_per_day,
        )

        print(f"â§¡ TÃ³pico: {plan.topic}")
        print(f"â§¡ NÃ¬vel: {plan.level}")
        print(f"â§¡ Objetivo: {plan.objective}")
        print(f"â§¡ Total de horas: {plan.total_hours}")
        print(f"â§¡ TÃ³picos: {len(plan.topics)}\n")

        print("TÃ³picos:")
        for i, t in enumerate(plan.topics, 1):
            print(f"  {i}. {t.name} ({t.duration_hours}h)")

        print(f"\nâ§¡ Plano salvo em: {self.plan_manager.plans_dir}")

    def cmd_study(self, topic: Optional[str] = None):
        """Inicia sessÃ£o de estudo.

        Args:
            topic: TÃ³pico (opcional, usa Ã¸ltimo se None)
        """
        print("\nð§¡§ Iniciando sessÃ£o de estudo\n")

        # Pega Ã¸ltimo plano ou tÃ³pico
        plans = self.plan_manager.list_plans()
        if not plans and not topic:
            print("Nenhum plano encontrado. Crie um com: bastiao plan \"Python\"")
            return

        if topic:
            # Cria novo plano
            self.cmd_plan(topic)
            plans = self.plan_manager.list_plans()

        # Carrega Ã¸ltimo plano
        latest_plan = max(plans, key=lambda p: p.stat().st_mtime)
        plan = self.plan_manager.load_plan(latest_plan)

        print(f"Plano: {plan.topic}")
        print(f"TÃ³picos: {len(plan.topics)}\n")

        # Mostra tÃ³picos
        for i, t in enumerate(plan.topics, 1):
            status = "â§¡" if self.task_runner.is_topic_complete(i - 1) else "â§¡"
            print(f"{status} {i}. {t.name}")

        # Menu interativo
        while True:
            print("\nOpÃ§Ãµes:")
            print("  [1-{}] Estudar tÃ³pico".format(len(plan.topics)))
            print("  [p] Progresso")
            print("  [q] Sair")

            choice = input("\nEscolha: ").strip().lower()

            if choice == "q":
                print("\nAtÃ© logo! ðĹĹ")
                break
            elif choice == "p":
                self.cmd_progress()
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(plan.topics):
                    self._study_topic(plan, idx)
                else:
                    print("ÃĨndice invÃ¡lido!")
            else:
                print("OpÃ§Ã£o invÃ¡lida!")

    def _study_topic(self, plan: StudyPlan, topic_index: int):
        """Estuda um tÃ³pico."""
        topic = plan.topics[topic_index]

        print(f"\nð§¡§ TÃ³pico: {topic.name}\n")
        print(f"DescriÃ§Ã£o: {topic.description}")
        print(f"DuraÃ§Ã£o: {topic.duration_hours}h")

        if topic.resources:
            print("\nRecursos:")
            for r in topic.resources:
                print(f"  - {r}")

        if topic.exercises:
            print("\nExercÃ¬cios:")
            for i, e in enumerate(topic.exercises, 1):
                print(f"  {i}. {e}")

        # Pergunta se completou
        while True:
            print("\nOpÃ§Ãµes:")
            print("  [c] Marcar como completo")
            print("  [e] Fazer exercÃ¬cio")
            print("  [v] Voltar")

            choice = input("\nEscolha: ").strip().lower()

            if choice == "c":
                self.task_runner.mark_topic_complete(topic_index)
                print("\nâ§¡ TÃ³pico marcado como completo!")
                break
            elif choice == "e":
                if topic.exercises:
                    print(f"\nExercÃ¬cio: {topic.exercises[0]}")
                    code = input("\nSeu cÃ³digo:\n")
                    # Executa cÃ³digo
                    from .sandbox import PythonSandbox
                    sandbox = PythonSandbox()
                    result = sandbox.execute(code)
                    print(f"\nOutput:\n{result.output}")
                    if result.error:
                        print(f"\nErro:\n{result.error[:200]}")
                else:
                    print("Sem exercÃ¬cios!")
            elif choice == "v":
                break

    def cmd_progress(self):
        """Mostra progresso."""
        print("\nð§¡§ Progresso dos Estudos\n")

        plans = self.plan_manager.list_plans()
        if not plans:
            print("Nenhum plano encontrado.")
            return

        for plan_file in plans:
            plan = self.plan_manager.load_plan(plan_file)
            progress = self.plan_manager.get_progress(plan)

            print(f"Plano: {plan.topic}")
            print(f"  Progresso: {progress['progress_percent']:.0f}%")
            print(f"  TÃ³picos: {progress['completed_topics']}/{progress['total_topics']}")
            print(f"  Horas: {progress['completed_hours']}/{progress['total_hours']}\n")

    def cmd_chat(self, message: str):
        """Chat direto com o BastiÃ£o.

        Args:
            message: Mensagem
        """
        print(f"\nð§¡§ {message}\n")

        messages = [
            ChatMessage(role="user", content=message),
        ]

        response = self.orchestrator.chat(messages)

        print(f"BastiÃ£o: {response}\n")


def main():
    """Ponto de entrada da CLI."""
    parser = argparse.ArgumentParser(
        description="BastiÃ£o Autodidata - Seu assistente de estudos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Comandos")

    # Comando: plan
    plan_parser = subparsers.add_parser("plan", help="Criar plano de estudo")
    plan_parser.add_argument("topic", help="TÃ³pico a estudar")
    plan_parser.add_argument("-l", "--level", default="iniciante", help="NÃ¬vel (iniciante, intermediario, avancado)")
    plan_parser.add_argument("-o", "--objective", default="", help="Objetivo especÃ¬fico")
    plan_parser.add_argument("-h", "--hours", type=int, default=2, help="Horas por dia")

    # Comando: study
    study_parser = subparsers.add_parser("study", help="Iniciar sessÃ£o de estudo")
    study_parser.add_argument("topic", nargs="?", help="TÃ³pico (opcional)")

    # Comando: progress
    subparsers.add_parser("progress", help="Mostrar progresso")

    # Comando: chat
    chat_parser = subparsers.add_parser("chat", help="Chat com o BastiÃ£o")
    chat_parser.add_argument("message", help="Mensagem")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = BastiaoCLI()

    try:
        if args.command == "plan":
            cli.cmd_plan(
                topic=args.topic,
                level=args.level,
                objective=args.objective,
                hours_per_day=args.hours,
            )
        elif args.command == "study":
            cli.cmd_study(topic=args.topic)
        elif args.command == "progress":
            cli.cmd_progress()
        elif args.command == "chat":
            cli.cmd_chat(message=args.message)

    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuÃ¡rio.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"\nErro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
