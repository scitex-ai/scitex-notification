"""Tests for the file-backed per-key rate limiter."""

import multiprocessing
import os

import pytest

from scitex_notification import RateLimiter


def test_first_event_is_allowed(tmp_path):
    # Arrange
    limiter = RateLimiter(60, tmp_path)
    # Act
    allowed = limiter.allow("disk-full:/data", now=1000.0)
    # Assert
    assert allowed is True


def test_repeat_within_window_is_suppressed(tmp_path):
    # Arrange
    limiter = RateLimiter(60, tmp_path)
    limiter.allow("disk-full:/data", now=1000.0)
    # Act
    allowed = limiter.allow("disk-full:/data", now=1059.0)
    # Assert
    assert allowed is False


def test_event_after_window_is_allowed_again(tmp_path):
    # Arrange
    limiter = RateLimiter(60, tmp_path)
    limiter.allow("disk-full:/data", now=1000.0)
    # Act
    allowed = limiter.allow("disk-full:/data", now=1060.0)
    # Assert
    assert allowed is True


def test_keys_are_independent(tmp_path):
    # Arrange
    limiter = RateLimiter(60, tmp_path)
    limiter.allow("a", now=1000.0)
    # Act
    allowed = limiter.allow("b", now=1000.0)
    # Assert
    assert allowed is True


def test_max_events_allows_that_many_per_window(tmp_path):
    # Arrange
    limiter = RateLimiter(60, tmp_path, max_events=2)
    # Act
    results = [limiter.allow("k", now=1000.0 + i) for i in range(3)]
    # Assert
    assert results == [True, True, False]


def test_peek_does_not_record(tmp_path):
    # Arrange
    limiter = RateLimiter(60, tmp_path)
    limiter.peek("k", now=1000.0)
    # Act
    allowed = limiter.allow("k", now=1000.0)
    # Assert
    assert allowed is True


def test_hold_does_not_record_when_the_block_fails(tmp_path):
    # Arrange
    limiter = RateLimiter(60, tmp_path)
    try:
        with limiter.hold("k", now=1000.0):
            raise OSError("send failed")
    except OSError:
        pass
    # Act
    allowed = limiter.allow("k", now=1001.0)
    # Assert
    assert allowed is True


def test_suppressions_are_counted(tmp_path):
    # Arrange
    limiter = RateLimiter(3600, tmp_path)
    for _ in range(3):
        limiter.allow("k")
    # Act
    count = limiter.suppressed_count("k")
    # Assert
    assert count == 2


def test_state_files_are_owner_only(tmp_path):
    # Arrange
    limiter = RateLimiter(60, tmp_path / "state")
    limiter.allow("k")
    # Act
    modes = {p.stat().st_mode & 0o777 for p in (tmp_path / "state").glob("*.json")}
    # Assert
    assert modes == {0o600}


@pytest.fixture
def rate_limit_env(tmp_path):
    previous = os.environ.get("SCITEX_NOTIFICATION_RATE_LIMIT_DIR")
    os.environ["SCITEX_NOTIFICATION_RATE_LIMIT_DIR"] = str(tmp_path / "rl")
    yield tmp_path / "rl"
    if previous is None:
        os.environ.pop("SCITEX_NOTIFICATION_RATE_LIMIT_DIR", None)
    else:
        os.environ["SCITEX_NOTIFICATION_RATE_LIMIT_DIR"] = previous


def test_state_dir_defaults_to_env(rate_limit_env):
    # Arrange
    expected = rate_limit_env
    # Act
    limiter = RateLimiter(60)
    # Assert
    assert limiter.state_dir == expected


@pytest.mark.parametrize("window", [0, -5, None])
def test_window_must_be_positive(window, tmp_path):
    # Arrange
    call = lambda: RateLimiter(window, tmp_path)  # noqa: E731
    # Act
    expected = ValueError
    # Assert
    with pytest.raises(expected):
        call()


def _allow_in_child(state_dir, queue):
    queue.put(RateLimiter(3600, state_dir).allow("shared-key"))


def test_concurrent_processes_allow_exactly_one(tmp_path):
    # Arrange
    queue = multiprocessing.get_context("fork").Queue()
    workers = [
        multiprocessing.get_context("fork").Process(
            target=_allow_in_child, args=(str(tmp_path), queue)
        )
        for _ in range(6)
    ]
    # Act
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=20)
    results = sorted(queue.get(timeout=5) for _ in workers)
    # Assert
    assert results == [False] * 5 + [True]
