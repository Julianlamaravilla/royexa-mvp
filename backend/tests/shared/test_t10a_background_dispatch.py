"""T10a (T10-P2): the outbox is dispatched by a loop inside the process, every few seconds,
and a failure of one round does not end it."""

import asyncio
import time

from fastapi.testclient import TestClient
from support import FakeClock, Flow

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.background import dispatch_forever
from royexa.bootstrap import Settings, build_container


def _eventually(check, seconds: float = 3.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(0.02)
    return False


def test_t10a_the_loop_dispatches_every_round_and_survives_a_failure():
    calls: list[int] = []

    def dispatch():
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("the channel exploded")

    async def run():
        stop = asyncio.Event()
        task = asyncio.create_task(dispatch_forever(dispatch, 0.01, stop))
        while len(calls) < 5:
            await asyncio.sleep(0.01)
        stop.set()
        await asyncio.wait_for(task, 1)

    asyncio.run(run())

    assert len(calls) >= 5, "it kept going after the second round failed"


def test_t10a_a_pending_notice_is_sent_without_anyone_calling_the_api():
    notifier = SimulatedNotifier()
    container = build_container(clock=FakeClock(), notifier=notifier)
    app = create_app(container, dispatch_every=0.02)

    with TestClient(app) as api:
        flow = Flow(api, notifier)
        approved = flow.approved()  # the API approval only queues the code notice

        assert _eventually(
            lambda: any(s.disbursement_id == approved["id"] and "code" in s.payload for s in notifier.delivered)
        )


def test_t10a_a_notice_that_failed_goes_out_when_the_channel_recovers():
    notifier = SimulatedNotifier(failing=True)
    container = build_container(clock=FakeClock(), notifier=notifier)
    app = create_app(container, dispatch_every=0.02)

    with TestClient(app) as api:
        flow = Flow(api, notifier)
        approved = flow.approved()
        assert _eventually(lambda: notifier.attempts >= 2), "it retried while failing"
        assert notifier.delivered == []
        notifier.failing = False

        assert _eventually(lambda: any(s.disbursement_id == approved["id"] for s in notifier.delivered))


def test_t10a_without_the_loop_nothing_is_sent_by_itself(flow, notifier):
    flow.approved()

    time.sleep(0.1)

    assert notifier.delivered == [], "the tests keep their determinism: no loop in create_app()"


def test_t10a_the_interval_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("ROYEXA_DISPATCH_SECONDS", raising=False)
    assert Settings.from_env().dispatch_seconds == 30.0
    monkeypatch.setenv("ROYEXA_DISPATCH_SECONDS", "0")
    assert Settings.from_env().dispatch_seconds == 0.0
    monkeypatch.setenv("ROYEXA_DISPATCH_SECONDS", "5")
    assert Settings.from_env().dispatch_seconds == 5.0
