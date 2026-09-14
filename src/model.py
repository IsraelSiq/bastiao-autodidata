"""Bastiao - Model Interface

Interface com OmniRoute (proxy de LLMs).
"""

import os
import requests
from typing import Optional


class OmniRouteModel:
    """Modelo via OmniRoute."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Inicializa o modelo.

        Args:
            base_url: URL do OmniRoute
            model: Nome do modelo
            api_key: API key (opcional)
        """
        self.base_url = (
            base_url or os.getenv("OMNIROUTE_URL", "http://127.0.0.1:11434/v1")
        ).rstrip("/")
        self.model = model or os.getenv("BASTIAO_MODEL", "llama3.2:3b")
        self.api_key = api_key or os.getenv("OMNIROUTE_API_KEY", "")

        self.session = requests.Session()
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def query(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        """Faz query ao modelo.

        Args:
            system_prompt: Prompt de sistema
            user_prompt: Prompt do usuario
            max_tokens: Maximo de tokens

        Returns:
            Resposta do modelo
        """
        url = (
            f"{self.base_url}/chat/completions"
            if self.base_url.endswith("/v1")
            else f"{self.base_url}/v1/chat/completions"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        response = self.session.post(url, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    # Teste
    model = OmniRouteModel()

    response = model.query(
        system_prompt="Voce é um assistente util.",
        user_prompt="Ola! Qual seu nome?",
    )

    print(f"Response: {response}")
