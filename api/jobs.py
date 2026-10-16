"""
Thread pool executor and concurrency locks for asynchronous audit jobs.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict

_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="veritas-worker")
_LOCKS: Dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def get_run_lock(run_id: str) -> threading.Lock:
    """Get or create a mutex for a specific run."""
    with _LOCKS_GUARD:
        if run_id not in _LOCKS:
            _LOCKS[run_id] = threading.Lock()
        return _LOCKS[run_id]


def submit_job(fn: Callable, *args, **kwargs) -> None:
    """Submit a task to the background worker pool."""
    _EXECUTOR.submit(fn, *args, **kwargs)
