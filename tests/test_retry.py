import pytest

from kb.retry import is_transient, retry


class Err(Exception):
    def __init__(self, code):
        self.code = code


def test_succeeds_after_transient_failures_with_backoff():
    calls, sleeps = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise Err(503)
        return "ok"

    assert retry(flaky, attempts=4, base_delay=1, sleep=sleeps.append) == "ok"
    assert sleeps == [1, 2]


def test_non_transient_error_not_retried():
    calls = []

    def bad():
        calls.append(1)
        raise Err(400)

    with pytest.raises(Err):
        retry(bad, sleep=lambda s: None)
    assert len(calls) == 1


def test_gives_up_after_max_attempts():
    calls = []

    def always():
        calls.append(1)
        raise Err(429)

    with pytest.raises(Err):
        retry(always, attempts=3, sleep=lambda s: None)
    assert len(calls) == 3


def test_delay_is_capped():
    sleeps = []
    with pytest.raises(Err):
        retry(lambda: (_ for _ in ()).throw(Err(500)), attempts=6, base_delay=10, max_delay=15, sleep=sleeps.append)
    assert max(sleeps) == 15


def test_is_transient_classification():
    assert is_transient(Err(429)) and is_transient(TimeoutError())
    assert not is_transient(Err(400)) and not is_transient(ValueError("x"))
