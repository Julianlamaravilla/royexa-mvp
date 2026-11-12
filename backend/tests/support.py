"""Test doubles and a small client for the disbursement flow."""

from datetime import UTC, datetime, timedelta

from httpx import Response

COLLECTOR = "cobrador-1"
ADMIN = "admin-1"
OTHER_ADMIN = "admin-2"
CLIENT = "cliente-1"
DEVICE_TIME = "2026-10-30T13:59:00+00:00"


class FakeClock:
    """Deterministic Clock port implementation."""

    def __init__(self, start: datetime = datetime(2026, 10, 30, 14, 0, tzinfo=UTC)) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class Flow:
    """Drives the HTTP API the way a collector and an administrator would."""

    def __init__(self, api, notifier) -> None:
        self.api = api
        self.notifier = notifier

    def _post(self, path: str, actor: str, body: dict | None = None) -> Response:
        return self.api.post(path, headers={"X-Actor-Id": actor}, json=body or {})

    def _get(self, path: str, actor: str = ADMIN) -> Response:
        return self.api.get(path, headers={"X-Actor-Id": actor})

    def request(
        self,
        actor: str = COLLECTOR,
        client: str = CLIENT,
        amount_cents: int = 100_000,
        term_days: int = 20,
        installment_count: int = 20,
    ) -> Response:
        return self._post(
            "/v1/disbursements",
            actor,
            {
                "client_id": client,
                "amount_cents": amount_cents,
                "term_days": term_days,
                "installment_count": installment_count,
            },
        )

    def requested(self, **kwargs) -> dict:
        response = self.request(**kwargs)
        assert response.status_code == 201, response.text
        return response.json()

    def approve(self, disbursement_id: str, actor: str = ADMIN, reason: str | None = None) -> Response:
        return self._post(f"/v1/disbursements/{disbursement_id}/approve", actor, {"reason": reason})

    def reject(self, disbursement_id: str, actor: str = ADMIN, reason: str | None = None) -> Response:
        return self._post(f"/v1/disbursements/{disbursement_id}/reject", actor, {"reason": reason})

    def approved(self, **kwargs) -> dict:
        disbursement = self.requested(**kwargs)
        response = self.approve(disbursement["id"])
        assert response.status_code == 200, response.text
        return response.json()

    def dispatch(self) -> Response:
        return self._post("/v1/notifications/dispatch", ADMIN)

    def issued_code(self, disbursement_id: str) -> str:
        assert self.dispatch().status_code == 200
        codes = [
            sent.payload["code"]
            for sent in self.notifier.delivered
            if sent.disbursement_id == disbursement_id and "code" in sent.payload
        ]
        assert len(codes) == 1
        return codes[0]

    def confirm(
        self,
        disbursement_id: str,
        code: str,
        actor: str = COLLECTOR,
        device_time: str = DEVICE_TIME,
    ) -> Response:
        return self._post(
            f"/v1/disbursements/{disbursement_id}/confirm",
            actor,
            {"code": code, "device_time": device_time},
        )

    def read(self, disbursement_id: str) -> dict:
        response = self._get(f"/v1/disbursements/{disbursement_id}")
        assert response.status_code == 200, response.text
        return response.json()

    def ledger(self, disbursement_id: str | None = None) -> list[dict]:
        suffix = f"?disbursement_id={disbursement_id}" if disbursement_id else ""
        response = self._get(f"/v1/ledger{suffix}")
        assert response.status_code == 200, response.text
        return response.json()

    def cash_balance(self, collector: str = COLLECTOR) -> int:
        response = self._get(f"/v1/cash-boxes/{collector}")
        assert response.status_code == 200, response.text
        return response.json()["balance_cents"]

    def notices(self, disbursement_id: str | None = None) -> list[dict]:
        suffix = f"?disbursement_id={disbursement_id}" if disbursement_id else ""
        response = self._get(f"/v1/notifications{suffix}")
        assert response.status_code == 200, response.text
        return response.json()

    def grant_exception(self, client: str, actor: str = ADMIN, reason: str = "cliente recurrente") -> Response:
        return self._post(f"/v1/clients/{client}/renewal-exceptions", actor, {"reason": reason})

    def pay(
        self,
        loan_id: str,
        amount_cents: int,
        method: str = "EFECTIVO",
        actor: str = COLLECTOR,
        device_time: str = DEVICE_TIME,
    ) -> Response:
        return self._post(
            f"/v1/loans/{loan_id}/payments",
            actor,
            {"amount_cents": amount_cents, "method": method, "device_time": device_time},
        )

    def loan_of(self, disbursement_id: str) -> dict:
        return self.read(disbursement_id)["loan"]

    def confirmed(self, **kwargs) -> dict:
        """A confirmed disbursement; returns it with its loan."""
        disbursement = self.approved(**kwargs)
        response = self.confirm(disbursement["id"], self.issued_code(disbursement["id"]))
        assert response.status_code == 200, response.text
        return response.json()

    def non_pay(
        self,
        loan_id: str,
        reason: str = "no tiene dinero",
        commitment_date: str | None = "2026-10-31",
        actor: str = COLLECTOR,
        device_time: str = DEVICE_TIME,
    ) -> Response:
        body = {"reason": reason, "device_time": device_time}
        if commitment_date is not None:
            body["commitment_date"] = commitment_date
        return self._post(f"/v1/loans/{loan_id}/non-payments", actor, body)

    def pending(self, route: str = "ruta-1", day: str | None = None, actor: str = COLLECTOR):
        suffix = f"?date={day}" if day else ""
        return self._get(f"/v1/routes/{route}/pending-visits{suffix}", actor)

    def pending_clients(
        self, route: str = "ruta-1", day: str | None = None, actor: str = COLLECTOR
    ) -> list[str]:
        response = self.pending(route, day, actor)
        assert response.status_code == 200, response.text
        return [row["client_id"] for row in response.json()]

    def close_box(
        self,
        delivered_cents: int,
        actor: str = COLLECTOR,
        collector: str = COLLECTOR,
        device_time: str = DEVICE_TIME,
    ) -> Response:
        return self._post(
            f"/v1/cash-boxes/{collector}/close",
            actor,
            {"delivered_cents": delivered_cents, "device_time": device_time},
        )

    def cash_closes(self, suffix: str = "", actor: str = ADMIN) -> Response:
        return self._get(f"/v1/cash-closes{suffix}", actor)

    def visit_everyone(self) -> None:
        """Ends every pending visit of route 1 with a non-payment, so the box can close."""
        for row in self.pending().json():
            assert self.non_pay(row["loan_id"], commitment_date="2026-11-30").status_code == 201

    def panels(self, collector: str = COLLECTOR, actor: str = COLLECTOR) -> Response:
        return self._get(f"/v1/cash-boxes/{collector}/panels", actor)
