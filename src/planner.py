"""BastiÃ£o Autodidata - Planejador de Estudos

Gera planos de estudo personalizados usando LLM.
"""

import json
import logging
from typing import Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from .orchestrator import BastiaoOrchestrator, ChatMessage
from .logging_config import get_logger

logger = get_logger("bastiao.planner")


@dataclass
class StudyTopic:
    """TÃ³pico de estudo."""
    name: str
    description: str
    duration_hours: int
    prerequisites: list[str]
    resources: list[str]
    exercises: list[str]
    completed: bool = False


@dataclass
class StudyPlan:
    """Plano de estudo completo."""
    topic: str
    level: str
    objective: str
    total_hours: int
    topics: list[StudyTopic]
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Converte para dict."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Converte para JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class StudyPlanner:
    """Planeja estudos usando LLM."""

    def __init__(
        self,
        orchestrator: BastiaoOrchestrator,
        model: Optional[str] = None,
    ):
        """Inicializa o planner.

        Args:
            orchestrator: Orchestrator para chamar LLM
            model: Modelo a usar (default: do orchestrator)
        """
        self.orchestrator = orchestrator
        self.model = model
        self.logger = logging.getLogger(__name__)

    def create_plan(
        self,
        topic: str,
        level: str = "iniciante",
        objective: str = "",
        hours_per_day: int = 2,
    ) -> StudyPlan:
        """Cria plano de estudo.

        Args:
            topic: TÃ³pico a estudar (ex: "Python", "Machine Learning")
            level: NÃ¬vel atual (iniciante, intermediÃ¡rio, avanÃ§ado)
            objective: Objetivo especÃ¬fico
            hours_per_day: Horas por dia disponÃ¬veis

        Returns:
            StudyPlan com currÃ¬culo completo
        """
        self.logger.info(f"Creating study plan: {topic} ({level})")

        # Prompt de planejamento
        prompt = f"""VocÃª ÃƒÂ© um professor especialista em criar planos de estudo personalizados.

Tarefa: Criar um plano de estudo completo para o tÃ³pico abaixo.

**TÃ³pico:** {topic}
**NÃ¬vel atual:** {level}
**Objetivo:** {objective or "Aprender o tÃ³pico de forma completa"}
**Tempo disponÃ¬vel:** {hours_per_day} horas por dia

Retorne um plano estrutuido em **JSON** com o seguinte formato:

```json
{{
  "topic": "{topic}",
  "level": "{level}",
  "objective": "...",
  "total_hours": 0,
  "topics": [
    {{
      "name": "Nome do tÃ³pico",
      "description": "DescriÃ§Ã£o do que serÃ¡ aprendido",
      "duration_hours": 0,
      "prerequisites": [],
      "resources": ["link ou nome do recurso"],
      "exercises": ["descriÃ§Ã£o do exercÃ¬cio"]
    }}
  ]
}}
```

Importante:
- Divida o tÃ³pico em subtÃ³picos lÃ³gicos
- Estime horas realistas para cada subtÃ³pico
- Inclua recursos gratuitos (docs, tutoriais, vÃ¬deos)
- Inclua exercÃ¬cios prÃ¡ticos para cada tÃ³pico
- Retorne APENAS o JSON, sem texto adicional"""

        messages = [
            ChatMessage(role="system", content="VocÃª ÃƒÂ© um professor especialista em criar planos de estudo. Retorne APENAS JSON vÃ¡lido."),
            ChatMessage(role="user", content=prompt),
        ]

        try:
            response = self.orchestrator.chat(messages, model=self.model)

            # Extrai JSON da resposta
            plan_json = self._extract_json(response)
            plan_data = json.loads(plan_json)

            # Converte para StudyPlan
            topics = [
                StudyTopic(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    duration_hours=t.get("duration_hours", 0),
                    prerequisites=t.get("prerequisites", []),
                    resources=t.get("resources", []),
                    exercises=t.get("exercises", []),
                )
                for t in plan_data.get("topics", [])
            ]

            plan = StudyPlan(
                topic=plan_data.get("topic", topic),
                level=plan_data.get("level", level),
                objective=plan_data.get("objective", objective),
                total_hours=plan_data.get("total_hours", sum(t.duration_hours for t in topics)),
                topics=topics,
            )

            self.logger.info(f"Study plan created: {len(topics)} topics, {plan.total_hours} hours total")

            return plan

        except Exception as e:
            self.logger.error(f"Error creating study plan: {e}")
            raise

    def _extract_json(self, text: str) -> str:
        """Extrai JSON de texto (remove markdown code blocks)."""
        import re

        # Remove code blocks markdown
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()

        # Tenta achar JSON direto
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return match.group(0).strip()

        # Retorna texto original
        return text.strip()

    def generate_schedule(
        self,
        plan: StudyPlan,
        start_date: Optional[datetime] = None,
        hours_per_day: int = 2,
    ) -> list[dict]:
        """Gera cronograma de estudos.

        Args:
            plan: Plano de estudo
            start_date: Data de inÃ¬cio
            hours_per_day: Horas por dia

        Returns:
            Lista de sessÃµes de estudo
        """
        start_date = start_date or datetime.now()
        schedule = []

        current_date = start_date
        for topic in plan.topics:
            days_needed = max(1, topic.duration_hours // hours_per_day)

            for day in range(days_needed):
                session = {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "topic": topic.name,
                    "description": topic.description,
                    "duration_hours": min(hours_per_day, topic.duration_hours - day * hours_per_day),
                    "exercises": topic.exercises[:2] if topic.exercises else [],
                    "completed": False,
                }
                schedule.append(session)
                current_date += timedelta(days=1)

        self.logger.info(f"Schedule generated: {len(schedule)} sessions")

        return schedule


def main():
    """Teste do planner."""
    from .orchestrator import BastiaoOrchestrator

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    orchestrator = BastiaoOrchestrator()
    planner = StudyPlanner(orchestrator, model="auto/best-fast")

    # Cria plano
    print("Creating study plan for Python...")
    plan = planner.create_plan(
        topic="Python",
        level="iniciante",
        objective="Aprender Python para anÃ¡lise de dados",
        hours_per_day=2,
    )

    print(f"\nPlano criado: {plan.topic}")
    print(f"Total de tÃ³picos: {len(plan.topics)}")
    print(f"Total de horas: {plan.total_hours}")

    print("\nTÃ³picos:")
    for i, topic in enumerate(plan.topics[:5], 1):
        print(f"  {i}. {topic.name} ({topic.duration_hours}h)")

    # Gera cronograma
    print("\nGenerating schedule...")
    schedule = planner.generate_schedule(plan, hours_per_day=2)

    print(f"\nCronograma: {len(schedule)} sessÃµes")
    for session in schedule[:5]:
        print(f"  - {session['date']}: {session['topic']} ({session['duration_hours']}h)")


if __name__ == "__main__":
    main()
