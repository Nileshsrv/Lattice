"""Run orchestrator: executes registered tools in limited worker subprocesses.

Timeout handling kills the worker pool and rebuilds it; a timed-out run is
failed, never left half-written (architecture.md §3). Memory caps are a known
Windows gap for the slice (docs/stage3).
"""

import concurrent.futures as cf
import threading

from .. import config
from . import worker


class RunTimeout(RuntimeError):
    pass


class Orchestrator:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pool = self._new_pool()

    def _new_pool(self) -> cf.ProcessPoolExecutor:
        pool = cf.ProcessPoolExecutor(max_workers=1, initializer=worker.warm)
        return pool

    def execute(self, tool_id: str, category: str, params: dict, data: dict) -> dict:
        timeout = config.RUN_TIMEOUT_SECONDS.get(category, 60)
        with self._lock:
            pool = self._pool
        future = pool.submit(worker.execute_tool, tool_id, params, data)
        try:
            return future.result(timeout=timeout)
        except cf.TimeoutError:
            with self._lock:
                self._pool.shutdown(wait=False, cancel_futures=True)
                for proc in getattr(self._pool, "_processes", {}).values():
                    proc.terminate()
                self._pool = self._new_pool()
            raise RunTimeout(f"run exceeded the {timeout}s limit for {category} tools")

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
