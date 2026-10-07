"""
title: Bastiao Auto (roteador de modelos)
description: Escolhe automaticamente o modelo local mais adequado (codigo, raciocinio ou resposta rapida) para cada solicitacao.
requirements: requests
version: 0.1.0
"""

import json
import re
from typing import Iterator

import requests
from pydantic import BaseModel, Field

CODE_RE = re.compile(
    r"```|traceback|stack ?trace|\b(def|class|import|function|const|SELECT|docker|compose|bash|powershell|"
    r"python|javascript|typescript|java|rust|golang|sql|regex|git|commit|pull request|bug|refator\w*|"
    r"codigo|código|script|erro de compila\w+|pytest|api|endpoint)\b",
    re.IGNORECASE,
)
REASON_RE = re.compile(
    r"\b(analis\w+|planej\w+|plano|compar\w+|arquitetur\w+|estrat[eé]gi\w+|por que|porque|explique|"
    r"demonstr\w+|calcul\w+|prove|trade-?off|decis[aã]o|prós e contras|vantagens)\b",
    re.IGNORECASE,
)


def last_user_text(messages: list) -> str:
    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, list):
            return " ".join(p.get("text", "") for p in content if p.get("type") == "text")
        return content or ""
    return ""


def has_image(messages: list) -> bool:
    return any(
        isinstance(m.get("content"), list) and any(p.get("type") == "image_url" for p in m["content"])
        for m in messages or []
    )


class Pipe:
    class Valves(BaseModel):
        ollama_base_url: str = Field("http://ollama:11434", description="URL do Ollama na rede Docker")
        code_model: str = Field("qwen2.5-coder:7b")
        reasoning_model: str = Field("qwen3:8b")
        fast_model: str = Field("llama3.2:3b")
        fast_max_chars: int = Field(160, description="Mensagens ate esse tamanho, sem sinais de codigo/raciocinio, usam o modelo rapido")
        long_context_chars: int = Field(6000, description="Conversas maiores que isso vao para o modelo de raciocinio")
        show_choice: bool = Field(True, description="Mostrar qual modelo foi escolhido no inicio da resposta")
        timeout: int = Field(600)

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self):
        return [{"id": "bastiao-auto", "name": "Bastiao Auto"}]

    def choose_model(self, messages: list) -> tuple[str, str]:
        text = last_user_text(messages)
        total = sum(len(str(m.get("content", ""))) for m in messages or [])
        if CODE_RE.search(text):
            return self.valves.code_model, "codigo"
        if REASON_RE.search(text) or total > self.valves.long_context_chars:
            return self.valves.reasoning_model, "raciocinio"
        if len(text) <= self.valves.fast_max_chars and total <= self.valves.long_context_chars:
            return self.valves.fast_model, "rapido"
        return self.valves.reasoning_model, "geral"

    def pipe(self, body: dict) -> Iterator[str]:
        messages = body.get("messages", [])
        model, reason = self.choose_model(messages)
        if has_image(messages):
            model, reason = self.valves.reasoning_model, "imagem"
        if self.valves.show_choice:
            yield f"_[Bastiao Auto: {model} - {reason}]_\n\n"
        payload = {"model": model, "messages": messages, "stream": True}
        try:
            with requests.post(
                f"{self.valves.ollama_base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=self.valves.timeout,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
        except Exception as exc:
            yield f"\n\nErro ao consultar {model}: {exc}"
