from unittest.mock import Mock

import requests

from src.github_client import GitHubClient


def test_github_client_configures_retry_and_timeout(monkeypatch):
    monkeypatch.setenv("BASTIAO_GITHUB_TIMEOUT_SECONDS", "7")
    client = GitHubClient("owner", "repo", "token")

    assert client.timeout == 7
    adapter = client.session.get_adapter("https://")
    assert adapter.max_retries.total == 3
    assert adapter.max_retries.backoff_factor == 0.5


def test_has_pull_request_passes_timeout():
    client = GitHubClient("owner", "repo", "token")
    client.session = Mock()
    client.session.get.return_value.json.return_value = []

    assert not client.has_pull_request_for_branch("bastiao/issue-1")
    client.session.get.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/pulls",
        params={"state": "all", "head": "owner:bastiao/issue-1", "per_page": 1},
        timeout=20.0,
    )
