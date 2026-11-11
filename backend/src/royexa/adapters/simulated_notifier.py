"""EXT-05: simulated notifier (RES-03). `failing` reproduces EC-04 and EV-03."""

from __future__ import annotations

from collections.abc import Callable

from royexa.notifications.ports import Notification, NotifierUnavailable


class SimulatedNotifier:
    def __init__(self, sink: Callable[[str], None] | None = None, failing: bool = False) -> None:
        self._sink = sink
        self.failing = failing
        self.delivered: list[Notification] = []
        self.attempts = 0

    def send(self, notification: Notification) -> None:
        self.attempts += 1
        if self.failing:
            raise NotifierUnavailable("simulated channel did not confirm the delivery")
        self.delivered.append(notification)
        if self._sink is not None:
            self._sink(
                f"[EXT-05] to={notification.client_id} kind={notification.kind.value} "
                f"disbursement={notification.disbursement_id} payment={notification.payment_id} "
                f"payload={notification.payload}"
            )
