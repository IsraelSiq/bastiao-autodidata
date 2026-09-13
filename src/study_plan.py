"""BastiÃ£o Autodidata - Gerenciador de Plano de Estudos

Gerencia criaÃ§Ã£o, salvamento e acompanhamento de planos de estudo.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from .planner import StudyPlanner, StudyPlan
from .orchestrator import BastiaoOrchestrator
from .logging_config import get_logger

logger = get_logger("bastiao.study_plan")


class StudyPlanManager:
    """Gerencia planos de estudo."""

    def __init__(
        self,
        orchestrator: BastiaoOrchestrator,
        data_dir: str = "data",
    ):
        """Inicializa o gerenciador.

        Args:
            orchestrator: Orchestrator para chamar LLM
            data_dir: DiretÃ³rio para salvar planos
        """
        self.orchestrator = orchestrator
        self.planner = StudyPlanner(orchestrator)
        self.data_dir = Path(data_dir)
        self.plans_dir = self.data_dir / "study_plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logger

    def create_plan(
        self,
        topic: str,
        level: str = "iniciante",
        objective: str = "",
        hours_per_day: int = 2,
        save: bool = True,
    ) -> StudyPlan:
        """Cria e salva plano de estudo.

        Args:
            topic: TÃ³pico a estudar
            level: NÃ¬vel atual
            objective: Objetivo especÃ¬fico
            hours_per_day: Horas por dia
            save: Se deve salvar em arquivo

        Returns:
            StudyPlan criado
        """
        self.logger.info(f"Creating study plan: {topic}")

        plan = self.planner.create_plan(
            topic=topic,
            level=level,
            objective=objective,
            hours_per_day=hours_per_day,
        )

        if save:
            self.save_plan(plan)

        return plan

    def save_plan(self, plan: StudyPlan, filename: Optional[str] = None) -> Path:
        """Salva plano em arquivo JSON.

        Args:
            plan: Plano a salvar
            filename: Nome do arquivo (opcional)

        Returns:
            Caminho do arquivo salvo
        """
        if not filename:
            safe_topic = plan.topic.lower().replace(" ", "_").replace("/", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_topic}_{timestamp}.json"

        filepath = self.plans_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(plan.to_json())

        self.logger.info(f"Plan saved: {filepath}")

        return filepath

    def load_plan(self, filepath: str) -> StudyPlan:
        """Carrega plano de arquivo JSON.

        Args:
            filepath: Caminho do arquivo

        Returns:
            StudyPlan carregado
        """
        from .planner import StudyTopic

        filepath = Path(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        topics = [
            StudyTopic(
                name=t["name"],
                description=t["description"],
                duration_hours=t["duration_hours"],
                prerequisites=t["prerequisites"],
                resources=t["resources"],
                exercises=t["exercises"],
                completed=t.get("completed", False),
            )
            for t in data.get("topics", [])
        ]

        plan = StudyPlan(
            topic=data["topic"],
            level=data["level"],
            objective=data["objective"],
            total_hours=data["total_hours"],
            topics=topics,
            created_at=data.get("created_at", ""),
        )

        self.logger.info(f"Plan loaded: {filepath}")

        return plan

    def list_plans(self) -> list[Path]:
        """Lista todos os planos salvos.

        Returns:
            Lista de caminhos
        """
        plans = list(self.plans_dir.glob("*.json"))
        self.logger.info(f"Found {len(plans)} plans")
        return plans

    def get_progress(self, plan: StudyPlan) -> dict:
        """Calcula progresso do plano.

        Args:
            plan: Plano

        Returns:
            Dict com progresso
        """
        total_topics = len(plan.topics)
        completed_topics = sum(1 for t in plan.topics if t.completed)
        total_hours = plan.total_hours
        completed_hours = sum(t.duration_hours for t in plan.topics if t.completed)

        progress = {
            "topic": plan.topic,
            "total_topics": total_topics,
            "completed_topics": completed_topics,
            "progress_percent": (completed_topics / total_topics * 100) if total_topics > 0 else 0,
            "total_hours": total_hours,
            "completed_hours": completed_hours,
            "remaining_hours": total_hours - completed_hours,
        }

        return progress


def main():
    """Teste do gerenciador."""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    orchestrator = BastiaoOrchestrator()
    manager = StudyPlanManager(orchestrator)

    # Cria plano
    print("Creating study plan...")
    plan = manager.create_plan(
        topic="Python para Data Science",
        level="iniciante",
        objective="Aprender Python para anÃ¡lise de dados",
        hours_per_day=2,
    )

    print(f"\nPlano criado: {plan.topic}")
    print(f"TÃ³picos: {len(plan.topics)}")
    print(f"Horas totais: {plan.total_hours}")

    # Salva
    filepath = manager.save_plan(plan)
    print(f"\nSalvo em: {filepath}")

    # Lista planos
    plans = manager.list_plans()
    print(f"\nPlanos salvos: {len(plans)}")
    for p in plans:
        print(f"  - {p.name}")

    # Progresso
    progress = manager.get_progress(plan)
    print(f"\nProgresso: {progress['progress_percent']:.1f}%")
    print(f"Horas: {progress['completed_hours']}/{progress['total_hours']}")


if __name__ == "__main__":
    main()
