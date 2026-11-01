"""PR-06, external failure. CA-12, EC-04, RF-06, EV-03, ADR-002."""

from fastapi.testclient import TestClient
from support import Flow

from royexa.api import create_app
from royexa.bootstrap import build_container
from royexa.notifications.ports import Notification, NotifierUnavailable

CODE_NOTICE = "CODIGO_CONFIRMACION"
RECEIPT = "COMPROBANTE_DESEMBOLSO"
MAX_ATTEMPTS = 5
CHANNEL_ERROR = "channel is down"


class UnreachableChannel:
    """Notifier port adapter whose channel never answers (EV-03)."""

    def __init__(self) -> None:
        self.calls = 0

    def send(self, notification: Notification) -> None:
        self.calls += 1
        raise NotifierUnavailable(CHANNEL_ERROR)


def _notice(flow, disbursement_id, kind):
    return next(n for n in flow.notices(disbursement_id) if n["kind"] == kind)


def test_pr06_failed_receipt_keeps_the_money_confirmed_and_stays_visible(flow, notifier):
    """PR-06 / EV-03 / CA-12: the channel fails after the money moved. Nothing rolls back,
    and the administrator can read that the client was not notified."""
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()
    flow.confirm(disbursement["id"], flow.issued_code(disbursement["id"]))
    notifier.failing = True

    report = flow.dispatch().json()

    assert report == {"attempted": 1, "sent": 0}
    receipt = _notice(flow, disbursement["id"], RECEIPT)
    assert receipt["status"] == "PENDIENTE", "CA-12: pending retry, not given as notified"
    assert receipt["attempts"] == 1
    assert receipt["last_error"]
    assert flow.read(disbursement["id"])["status"] == "CONFIRMADO"
    assert len(flow.ledger(disbursement["id"])) == 1
    assert flow.cash_balance() == opening_balance - disbursement["amount_cents"]


def test_pr06_fifth_failure_marks_the_notice_failed(flow, notifier):
    """PR-06 / EV-03 / EC-04: retries end in a visible failed state."""
    disbursement = flow.approved()
    flow.confirm(disbursement["id"], flow.issued_code(disbursement["id"]))
    notifier.failing = True

    for _ in range(MAX_ATTEMPTS + 2):
        flow.dispatch()

    receipt = _notice(flow, disbursement["id"], RECEIPT)
    assert receipt["status"] == "FALLIDO"
    assert receipt["attempts"] == MAX_ATTEMPTS
    assert receipt["sent_at"] is None


def test_pr06_retry_delivers_once_the_channel_recovers(flow, notifier):
    """PR-06 / CA-12: a pending notice is sent by a later dispatch."""
    disbursement = flow.approved()
    flow.confirm(disbursement["id"], flow.issued_code(disbursement["id"]))
    notifier.failing = True
    flow.dispatch()
    notifier.failing = False

    assert flow.dispatch().json() == {"attempted": 1, "sent": 1}
    assert _notice(flow, disbursement["id"], RECEIPT)["status"] == "ENVIADO"


def test_pr06_undelivered_code_moves_no_money(flow, notifier):
    """PR-06 / RN-03 / EC-04: without the code delivered, the operation stays unconfirmed."""
    opening_balance = flow.cash_balance()
    notifier.failing = True
    disbursement = flow.approved()

    flow.dispatch()

    assert _notice(flow, disbursement["id"], CODE_NOTICE)["status"] == "PENDIENTE"
    assert flow.read(disbursement["id"])["status"] == "APROBADO"
    assert flow.cash_balance() == opening_balance


def test_pr06_code_notice_fails_after_five_dispatches_through_a_replaced_adapter(clock):
    """PR-06 / EV-03 / CA-12: another adapter behind the port, failing on the code notice."""
    channel = UnreachableChannel()
    container = build_container(clock=clock, notifier=channel)
    flow = Flow(TestClient(create_app(container)), channel)
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()

    for dispatch in range(1, MAX_ATTEMPTS + 1):
        assert flow.dispatch().json() == {"attempted": 1, "sent": 0}
        notice = _notice(flow, disbursement["id"], CODE_NOTICE)
        assert notice["attempts"] == dispatch, "each dispatch counts one attempt"
        assert notice["status"] == ("FALLIDO" if dispatch == MAX_ATTEMPTS else "PENDIENTE")

    assert channel.calls == MAX_ATTEMPTS
    assert notice["last_error"] == CHANNEL_ERROR
    assert notice["sent_at"] is None
    assert flow.dispatch().json() == {"attempted": 0, "sent": 0}, "a failed notice leaves the queue"
    assert flow.read(disbursement["id"])["status"] == "APROBADO"
    assert flow.cash_balance() == opening_balance
    assert flow.ledger(disbursement["id"]) == []
