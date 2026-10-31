"""PR-06, external failure. CA-12, EC-04, RF-06, EV-03, ADR-002."""

CODE_NOTICE = "CODIGO_CONFIRMACION"
RECEIPT = "COMPROBANTE_DESEMBOLSO"
MAX_ATTEMPTS = 5


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
