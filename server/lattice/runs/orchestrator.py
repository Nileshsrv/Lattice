"""Run orchestrator: executes registered tools in limited worker subprocesses.

Timeout or memory breach kills the worker pool and rebuilds it; such a run is
failed, never left half-written (architecture.md §3). The memory cap is a
watchdog polling worker RSS — rlimit-style caps do not exist on Windows.
"""

import concurrent.futures as cf
import threading

import psutil

from .. import config
from . import worker


class RunTimeout(RuntimeError):
    pass


class RunMemoryExceeded(RuntimeError):
    pass


def rss_over_limit(pids: list[int], limit_bytes: int) -> int | None:
    """Return the RSS of the first process over the limit, else None."""
    for pid in pids:
        try:
            rss = psutil.Process(pid).memory_info().rss
        except psutil.Error:
            continue
        if rss > limit_bytes:
            return rss
    return None


class Orchestrator:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pool = self._new_pool()

    def _new_pool(self) -> cf.ProcessPoolExecutor:
        pool = cf.ProcessPoolExecutor(max_workers=1, initializer=worker.warm)
        return pool

    def _kill_pool(self) -> None:
        with self._lock:
            self._pool.shutdown(wait=False, cancel_futures=True)
            for proc in getattr(self._pool, "_processes", {}).values():
                proc.terminate()
            self._pool = self._new_pool()

    def execute(self, tool_id: str, category: str, params: dict, data: dict) -> dict:
        timeout = config.RUN_TIMEOUT_SECONDS.get(category, 60)
        limit_bytes = config.RUN_MEMORY_LIMIT_MB * 1024 * 1024
        with self._lock:
            pool = self._pool
        future = pool.submit(worker.execute_tool, tool_id, params, data)
        waited = 0.0
        poll = 0.25
        while True:
            try:
                return future.result(timeout=poll)
            except cf.TimeoutError:
                waited += poll
                pids = list(getattr(pool, "_processes", {}).keys())
                rss = rss_over_limit(pids, limit_bytes)
                if rss is not None:
                    self._kill_pool()
                    raise RunMemoryExceeded(
                        f"run used {rss // (1024 * 1024)} MB, over the "
                        f"{config.RUN_MEMORY_LIMIT_MB} MB limit"
                    )
                if waited >= timeout:
                    self._kill_pool()
                    raise RunTimeout(
                        f"run exceeded the {timeout}s limit for {category} tools"
                    )

    def shutdown(self) -> None:
        with self._lock:
            self._pool.shutdown(wait=False, cancel_futures=True)


_orchestrator: Orchestrator | None = None
_orch_lock = threading.Lock()


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    with _orch_lock:
        if _orchestrator is None:
            _orchestrator = Orchestrator()
        return _orchestrator
