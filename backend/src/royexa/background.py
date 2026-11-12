"""T10a (T10-P2): the outbox dispatcher as a loop inside the process. The production entry point
starts it; `create_app` does not unless asked, so the tests stay deterministic."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from fastapi.concurrency import run_in_threadpool

log = logging.getLogger("royexa.dispatch")


async def dispatch_forever(dispatch: Callable[[], object], interval: float, stop: asyncio.Event) -> None:
    """Every `interval` seconds sends what is pending and retries what failed (T4). A round that
    raises is logged and the loop goes on: a notice is never lost, only late."""
    while not stop.is_set():
        try:
            await run_in_threadpool(dispatch)
        except Exception:  # noqa: BLE001 - the loop must outlive any one round
            log.exception("a dispatch round failed")
        try:
            await asyncio.wait_for(stop.wait(), interval)
        except TimeoutError:
            pass
