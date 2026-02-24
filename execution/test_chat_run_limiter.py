#!/usr/bin/env python3
"""Unit tests for global chat run concurrency limiting."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

try:
    from execution.chat_run_limiter import ChatRunLimiter, ChatRunLimitError
except ImportError:
    from chat_run_limiter import ChatRunLimiter, ChatRunLimitError


def test_run_slot_tracks_active_runs():
    limiter = ChatRunLimiter(max_concurrent_runs=2)

    assert limiter.active_runs == 0
    with limiter.run_slot():
        assert limiter.active_runs == 1
    assert limiter.active_runs == 0


def test_run_slot_releases_after_exception():
    limiter = ChatRunLimiter(max_concurrent_runs=1)

    with pytest.raises(RuntimeError):
        with limiter.run_slot():
            raise RuntimeError("boom")

    # Slot should be released even if the run raises.
    with limiter.run_slot():
        assert limiter.active_runs == 1


def test_max_concurrent_limit_is_enforced():
    limiter = ChatRunLimiter(max_concurrent_runs=1)

    with limiter.run_slot():
        with pytest.raises(ChatRunLimitError):
            with limiter.run_slot():
                pass


def test_limit_is_instance_wide_for_threads():
    limiter = ChatRunLimiter(max_concurrent_runs=1)
    entered = threading.Event()
    release = threading.Event()

    def hold_slot():
        with limiter.run_slot():
            entered.set()
            release.wait(timeout=2)
            return "held"

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(hold_slot)
        assert entered.wait(timeout=2)

        with pytest.raises(ChatRunLimitError):
            with limiter.run_slot():
                pass

        release.set()
        assert future.result(timeout=2) == "held"
