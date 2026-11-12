"""Test doubles and a small client for the disbursement flow."""

from datetime import UTC, datetime, timedelta

from httpx import Response

from royexa.seed import demo_password

COLLECTOR = "cobrador-1"
ADMIN = "admin-1"
OTHER_ADMIN = "admin-2"
CLIENT = "cliente-1"
PHONE = {"width": 360, "height": 740}
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
        self._tokens: dict[str, str] = {}

    def _token(self, actor: str) -> str:
        """One session per user, opened on first use with the documented demo password. A
        user that cannot log in gets a token that is refused, so a test still sees the 401."""
        if actor not in self._tokens:
            response = self.api.post(
                "/v1/auth/login", json={"user_id": actor, "password": demo_password(actor)}
            )
            self._tokens[actor] = (
                response.json()["token"] if response.status_code == 200 else "sin-sesion"
            )
        return self._tokens[actor]

    def _send(self, method: str, path: str, actor: str, body: dict | None = None) -> Response:
        """Tests move the FakeClock by days; a session that lapsed meanwhile is renewed once.
        A 401 means the request was refused before it ran, so repeating it is safe."""
        for attempt in (1, 2):
            token = self._token(actor)
            options: dict = {"headers": {"Authorization": f"Bearer {token}"}}
            if method == "POST":
                options["json"] = body or {}
            response = self.api.request(method, path, **options)
            if response.status_code != 401 or token == "sin-sesion" or attempt == 2:
                return response
            if not response.json().get("type", "").endswith("/sesion-requerida"):
                return response
            self._tokens.pop(actor, None)
        return response

    def _post(self, path: str, actor: str, body: dict | None = None) -> Response:
        return self._send("POST", path, actor, body)

    def _get(self, path: str, actor: str = ADMIN) -> Response:
        return self._send("GET", path, actor)

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

    def adjust(
        self,
        entry_id: str,
        amount_cents: int,
        reason: str | None = "error de captura del importe",
        actor: str = ADMIN,
        device_time: str = DEVICE_TIME,
    ) -> Response:
        body: dict = {"amount_cents": amount_cents, "device_time": device_time}
        if reason is not None:
            body["reason"] = reason
        return self._post(f"/v1/ledger/{entry_id}/adjustments", actor, body)

    def payment_entry(self, payment_id: str) -> dict:
        return next(e for e in self.ledger() if e["payment_id"] == payment_id)


def assert_fits_phone(page) -> None:
    """T7-P3: the page does not scroll sideways at the phone's width."""
    widths = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert widths[0] <= widths[1] == PHONE["width"], f"horizontal scroll on {page.url}: {widths}"
