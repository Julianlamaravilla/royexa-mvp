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
