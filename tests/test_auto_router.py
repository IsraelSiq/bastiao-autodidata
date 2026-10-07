import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

SPEC = importlib.util.spec_from_file_location(
    "auto_router_pipe", Path(__file__).parent.parent / "openwebui" / "auto_router_pipe.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def choose(text):
    return mod.Pipe().choose_model([{"role": "user", "content": text}])


def test_routes_code():
    assert choose("corrija esse erro em python")[0] == "qwen2.5-coder:7b"
    assert choose("```x = 1```")[0] == "qwen2.5-coder:7b"


def test_routes_reasoning():
    assert choose("compare as vantagens de duas abordagens")[0] == "qwen3:8b"


def test_routes_fast_for_short_chat():
    assert choose("oi, tudo bem?")[0] == "llama3.2:3b"


def test_long_plain_text_goes_general():
    assert choose("x " * 200)[0] == "qwen3:8b"


def test_image_forces_reasoning_model():
    pipe = mod.Pipe()
    pipe.valves.show_choice = False
    body = {"messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {}}]}]}
    resp = MagicMock()
    resp.__enter__.return_value = resp
    resp.iter_lines.return_value = [b'{"message":{"content":"ok"}}']
    with patch.object(mod.requests, "post", return_value=resp) as post:
        out = "".join(pipe.pipe(body))
    assert out == "ok"
    assert post.call_args.kwargs["json"]["model"] == "qwen3:8b"


def test_error_is_reported():
    pipe = mod.Pipe()
    with patch.object(mod.requests, "post", side_effect=RuntimeError("boom")):
        out = "".join(pipe.pipe({"messages": [{"role": "user", "content": "oi"}]}))
    assert "Erro ao consultar" in out
