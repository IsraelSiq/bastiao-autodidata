from unittest.mock import Mock, patch

import requests

from src import health


def _response(status: int) -> Mock:
    response = Mock()
    response.status_code = status
    response.ok = 200 <= status < 400
    return response


def test_github_check_never_reports_token(monkeypatch):
    monkeypatch.setenv("GITHUB_OWNER", "o")
    monkeypatch.setenv("GITHUB_REPO", "r")
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")

    with patch("src.health.requests.get", return_value=_response(200)) as get:
        check = health.check_github(1)

    assert check.ok
    assert "secret-token" not in str(check.to_dict())
    assert get.call_args.kwargs["timeout"] == 1


def test_github_check_requires_configuration(monkeypatch):
    for name in ("GITHUB_OWNER", "GITHUB_REPO", "GITHUB_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    assert not health.check_github(1).ok


def test_ollama_check_avoids_duplicate_v1(monkeypatch):
    monkeypatch.setenv("OMNIROUTE_URL", "http://ollama:11434/v1")

    with patch("src.health.requests.get", return_value=_response(200)) as get:
        assert health.check_ollama(1).ok

    assert get.call_args.args[0] == "http://ollama:11434/v1/models"


def test_ollama_check_reports_connection_failure(monkeypatch):
    with patch("src.health.requests.get", side_effect=requests.ConnectionError("down")):
        check = health.check_ollama(1)

    assert not check.ok
    assert check.detail == "ConnectionError"


def test_workspace_check_requires_git_checkout(tmp_path, monkeypatch):
    monkeypatch.setenv("BASTIAO_WORKSPACE", str(tmp_path))
    assert not health.check_workspace().ok

    (tmp_path / ".git").mkdir()
    assert health.check_workspace().ok


def test_chroma_falls_back_to_v1_heartbeat(monkeypatch):
    monkeypatch.setenv("CHROMA_URL", "http://chroma:8000")

    with patch(
        "src.health.requests.get", side_effect=[_response(404), _response(200)]
    ) as get:
        assert health.check_chroma(1).ok

    assert get.call_args.args[0] == "http://chroma:8000/api/v1/heartbeat"


def test_optional_chroma_failure_does_not_fail_overall(tmp_path, monkeypatch):
    monkeypatch.setenv("BASTIAO_WORKSPACE", str(tmp_path))
    (tmp_path / ".git").mkdir()

    with patch.multiple(
        "src.health",
        check_github=Mock(return_value=health.HealthCheck("github", True, "ok", 0)),
        check_ollama=Mock(return_value=health.HealthCheck("ollama", True, "ok", 0)),
        check_chroma=Mock(return_value=health.HealthCheck("chroma", False, "down", 0, False)),
    ):
        report = health.collect_health(1)

    assert report["ok"]
    assert [check["name"] for check in report["checks"]] == [
        "github",
        "ollama",
        "workspace",
        "chroma",
    ]


def test_required_failure_fails_overall(tmp_path, monkeypatch):
    monkeypatch.setenv("BASTIAO_WORKSPACE", str(tmp_path / "missing"))

    with patch.multiple(
        "src.health",
        check_github=Mock(return_value=health.HealthCheck("github", True, "ok", 0)),
        check_ollama=Mock(return_value=health.HealthCheck("ollama", True, "ok", 0)),
        check_chroma=Mock(return_value=health.HealthCheck("chroma", False, "ok", 0, False)),
    ):
        assert not health.collect_health(1)["ok"]
