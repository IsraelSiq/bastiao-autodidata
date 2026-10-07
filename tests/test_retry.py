from unittest.mock import Mock

import pytest
import requests

from src.metrics import CycleMetrics
from src.retry import retry_transient


def _http_error(status: int) -> requests.HTTPError:
    response = Mock()
    response.status_code = status
    return requests.HTTPError(response=response)


def test_retry_recovers_after_transient_failure():
    func = Mock(side_effect=[requests.ConnectionError(), "ok"])
    sleep = Mock()

    assert retry_transient(func, attempts=3, base_delay=1, sleep=sleep) == "ok"
    sleep.assert_called_once_with(1)


def test_retry_is_bounded_and_backs_off():
    func = Mock(side_effect=requests.Timeout())
    sleep = Mock()

    with pytest.raises(requests.Timeout):
        retry_transient(func, attempts=3, base_delay=1, sleep=sleep)

    assert func.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]


def test_retry_caps_delay():
    func = Mock(side_effect=requests.Timeout())
    sleep = Mock()

    with pytest.raises(requests.Timeout):
        retry_transient(func, attempts=4, base_delay=10, max_delay=15, sleep=sleep)

    assert [call.args[0] for call in sleep.call_args_list] == [10, 15, 15]


@pytest.mark.parametrize("status", [401, 403, 404])
def test_retry_does_not_retry_client_errors(status):
    func = Mock(side_effect=_http_error(status))

    with pytest.raises(requests.HTTPError):
        retry_transient(func, attempts=3, sleep=Mock())

    assert func.call_count == 1


@pytest.mark.parametrize("status", [429, 502])
def test_retry_retries_rate_limit_and_server_errors(status):
    func = Mock(side_effect=[_http_error(status), "ok"])

    assert retry_transient(func, attempts=2, base_delay=0, sleep=Mock()) == "ok"


def test_status_keeps_first_unavailable_timestamp_until_recovery(tmp_path):
    metrics = CycleMetrics(str(tmp_path))
    metrics.record({"status": "github_unavailable"}, 0.1)
    first = metrics.read_status()["github_unavailable_since"]
    metrics.record({"status": "github_unavailable"}, 0.1)

    assert metrics.read_status()["github_unavailable_since"] == first

    metrics.record({"status": "no_open_issues"}, 0.1)
    status = metrics.read_status()
    assert "github_unavailable_since" not in status
    assert status["last_cycle"]["status"] == "no_open_issues"
