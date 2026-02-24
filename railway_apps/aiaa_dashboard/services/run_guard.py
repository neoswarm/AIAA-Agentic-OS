"""
In-memory guard for pending/running skill executions per session.
"""

import threading
import uuid
from typing import Dict, Optional


_LOCK = threading.Lock()
_SESSION_RUNS: Dict[str, Dict[str, str]] = {}
_RESERVATION_TO_SESSION: Dict[str, str] = {}
_RUN_TO_SESSION: Dict[str, str] = {}


def reserve_run_slot(session_key: str, max_active_runs: int) -> Optional[str]:
    """Reserve a pending run slot for a session.

    Returns:
        reservation_id if a slot was reserved, otherwise None.
    """
    if max_active_runs < 1:
        max_active_runs = 1

    with _LOCK:
        active_runs = _SESSION_RUNS.setdefault(session_key, {})
        if len(active_runs) >= max_active_runs:
            return None

        reservation_id = f"resv-{uuid.uuid4()}"
        active_runs[reservation_id] = "pending"
        _RESERVATION_TO_SESSION[reservation_id] = session_key
        return reservation_id


def bind_run_to_reservation(session_key: str, reservation_id: str, run_id: str) -> bool:
    """Convert a reserved slot into a concrete run."""
    with _LOCK:
        if _RESERVATION_TO_SESSION.get(reservation_id) != session_key:
            return False

        active_runs = _SESSION_RUNS.get(session_key)
        if not active_runs or reservation_id not in active_runs:
            return False

        status = active_runs.pop(reservation_id, "pending")
        active_runs[run_id] = status

        _RESERVATION_TO_SESSION.pop(reservation_id, None)
        _RUN_TO_SESSION[run_id] = session_key
        return True


def release_run_reservation(session_key: str, reservation_id: str) -> None:
    """Release a reserved slot when execution did not start."""
    with _LOCK:
        active_runs = _SESSION_RUNS.get(session_key)
        if active_runs and reservation_id in active_runs:
            active_runs.pop(reservation_id, None)
            if not active_runs:
                _SESSION_RUNS.pop(session_key, None)

        _RESERVATION_TO_SESSION.pop(reservation_id, None)


def mark_run_running(run_id: str) -> None:
    """Mark a tracked run as running."""
    with _LOCK:
        session_key = _RUN_TO_SESSION.get(run_id)
        if not session_key:
            return

        active_runs = _SESSION_RUNS.get(session_key)
        if active_runs and run_id in active_runs:
            active_runs[run_id] = "running"


def mark_run_finished(run_id: str) -> None:
    """Release a run slot once it is no longer pending/running."""
    with _LOCK:
        session_key = _RUN_TO_SESSION.pop(run_id, None)
        if not session_key:
            return

        active_runs = _SESSION_RUNS.get(session_key)
        if not active_runs:
            return

        active_runs.pop(run_id, None)
        if not active_runs:
            _SESSION_RUNS.pop(session_key, None)


def get_active_run_count(session_key: str) -> int:
    """Return active pending/running run count for a session."""
    with _LOCK:
        return len(_SESSION_RUNS.get(session_key, {}))


def reset_run_guard_state() -> None:
    """Clear run guard state. Used by tests."""
    with _LOCK:
        _SESSION_RUNS.clear()
        _RESERVATION_TO_SESSION.clear()
        _RUN_TO_SESSION.clear()
