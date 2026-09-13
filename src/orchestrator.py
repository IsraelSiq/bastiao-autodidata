"""BastiÃ£o Autodidata - Orchestrator

Orquestra chamadas LLM via OmniRoute.
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Tenta carregar .env (se python-dotenv estiver instalado)
try:
    from dotenv import load_dotenv
    # Carrega .env da raiz do projeto
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")
    else:
        print("No .env found, using environment variables")
except ImportError:
    print("python-dotenv not installed, using environment variables only")


@dataclass
class ChatMessage:
    """Mensagem de chat."""
    role: str  # 'system', 'user', 'assistant'
    content: str


class BastiaoOrchestrator:
    """Orquestra chamadas LLM via OmniRoute."""

    def __init__(
        self,
        omniroute_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: str = "github/gpt-4o-mini",
        timeout: int = 60,
    ):
        """Inicializa o orchestrator.

        Args:
            omniroute_url: URL do OmniRoute (default: http://localhost:20128)
            api_key: API key do OmniRoute (opcional)
            default_model: Modelo padrÃ£o para chat
            timeout: Timeout em segundos
        """
        self.omniroute_url = omniroute_url or os.getenv(
            "OMNIROUTE_URL", "http://localhost:20128"
        )
        self.api_key = api_key or os.getenv("OMNIROUTE_API_KEY")
        self.default_model = default_model
        self.timeout = timeout

        # Configura logging
        self.logger = logging.getLogger(__name__)

        # Configura sessÃ£o HTTP com retry
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.logger.info(
            f"Orchestrator initialized: {self.omniroute_url} (model: {self.default_model})"
        )

    def _get_headers(self) -> dict:
        """Retorna headers HTTP."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def list_models(self) -> list:
        """Lista modelos disponÃ¬veis.

        Returns:
            Lista de dicts com info dos modelos
        """
        url = f"{self.omniroute_url}/v1/models"

        try:
            response = self.session.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            models = data.get("data", [])
            self.logger.info(f"Listed {len(models)} models")
            return models
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
            raise

    def chat(
        self,
        messages: list[ChatMessage | dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Envia mensagem de chat.

        Args:
            messages: Lista de mensagens (dict ou ChatMessage)
            model: Modelo a usar (default: default_model)
            temperature: Temperatura (0-2)
            max_tokens: MÃ¡ximo de tokens

        Returns:
            Resposta do LLM
        """
        model = model or self.default_model

        # Converte ChatMessage para dict
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                formatted_messages.append({"role": msg.role, "content": msg.content})
            else:
                formatted_messages.append(msg)

        url = f"{self.omniroute_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": formatted_messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        start_time = datetime.now()

        try:
            response = self.session.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            elapsed = (datetime.now() - start_time).total_seconds()

            self.logger.info(
                f"Chat completed: model={model}, tokens={data.get('usage', {}).get('total_tokens', 'N/A')}, time={elapsed:.2f}s"
            )

            return content

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Chat error: model={model}, time={elapsed:.2f}s, error={e}")
            raise

    def test_connection(self) -> bool:
        """Testa conexÃ£o com OmniRoute.

        Returns:
            True se conexÃ£o OK
        """
        try:
            self.list_models()
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False


def main():
    """Teste bÃ¡sico."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    orchestrator = BastiaoOrchestrator()

    # Testa conexÃ£o
    print("Testing connection...")
    if not orchestrator.test_connection():
        print("Connection failed!")
        return

    # Lista modelos
    print("\nAvailable models:")
    models = orchestrator.list_models()
    for model in models[:5]:  # Mostra primeiros 5
        print(f"  - {model.get('id', 'N/A')}")

    # Testa chat
    print("\nTesting chat...")
    messages = [
        ChatMessage(role="system", content="VocÃª ÃƒÂ© um assistente ÃƒÂºtil."),
        ChatMessage(role="user", content="OlÃ¡! Qual ÃƒÂ© seu nome?"),
    ]

    response = orchestrator.chat(messages)
    print(f"Response: {response}")


if __name__ == "__main__":
    main()
