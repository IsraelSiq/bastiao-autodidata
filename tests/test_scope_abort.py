from unittest.mock import Mock

from src.env import SandboxEnv
from src.swe_agent import SWEAgent


def test_swe_agent_aborts_immediately_after_scope_violation():
    model = Mock()
    model.query.return_value = (
        "write src/blocked.py value\n"
        "write src/allowed.py value\n"
        "complete"
    )
    env = SandboxEnv(allowed_paths=["src/allowed.py"], strict_scope=True)

    assert not SWEAgent(model=model, env=env, max_iterations=3).solve("task")
    assert not (env.tools.repo_path / "src" / "allowed.py").exists()
