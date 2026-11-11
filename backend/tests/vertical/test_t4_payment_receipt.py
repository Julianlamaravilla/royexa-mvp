"""T4, RF-06: every payment issues a receipt through the outbox; CA-11 and CA-12.

Runs on both adapters (fixture `backend`). FakeClock starts on Friday 2026-10-30, so the
first installment of a loan confirmed that day falls on Saturday 2026-10-31.
"""

from support import ADMIN

RECEIPT = "COMPROBANTE_PAGO"
MAX_ATTEMPTS = 5


def _paid(flow, amount: int = 3_000, method: str = "EFECTIVO") -> tuple[dict, dict]:
    loan = flow.confirmed()["loan"]
    result = flow.pay(loan["id"], amount, method)
    assert result.status_code == 201, result.text
    return loan, result.json()["payment"]


def _receipts(flow, payment_id: str) -> list[dict]:
    response = flow._get(f"/v1/notifications?payment_id={payment_id}", ADMIN)
    assert response.status_code == 200, response.text
    return response.json()


def _delivered(notifier, payment_id: str):
    return [n for n in notifier.delivered if n.payment_id == payment_id]


def test_ca11_a_payment_issues_a_receipt_with_amount_balance_and_next_due_date(flow, notifier):
    loan, payment = _paid(flow, 3_000)

    queued = _receipts(flow, payment["id"])
    assert [(n["kind"], n["status"]) for n in queued] == [(RECEIPT, "PENDIENTE")]
    assert flow.dispatch().status_code == 200

    sent = _delivered(notifier, payment["id"])
    assert len(sent) == 1
    assert sent[0].kind.value == RECEIPT
    assert sent[0].client_id == payment["client_id"]
    assert sent[0].disbursement_id is None
    assert sent[0].payload == {
        "amount_cents": "3000",
        "outstanding_cents": "117000",
        "next_due_date": "2026-10-31",
    }
    assert [(n["status"], n["attempts"]) for n in _receipts(flow, payment["id"])] == [("ENVIADO", 1)]


def test_ca11_the_next_due_date_moves_on_when_an_installment_is_settled(flow, notifier):
    _, payment = _paid(flow, 6_000)

    flow.dispatch()

    assert _delivered(notifier, payment["id"])[0].payload["next_due_date"] == "2026-11-02"


def test_ca11_a_transfer_issues_its_receipt_too(flow, notifier):
    _, payment = _paid(flow, 3_000, "TRANSFERENCIA")

    flow.dispatch()

    assert len(_delivered(notifier, payment["id"])) == 1


def test_ca11_a_settled_loan_has_no_next_due_date(flow, notifier):
    payment = flow.pay("prestamo-impago", 70_000).json()["payment"]

    flow.dispatch()

    assert _delivered(notifier, payment["id"])[0].payload == {
        "amount_cents": "70000",
        "outstanding_cents": "0",
        "next_due_date": "",
    }


def test_t4_each_payment_has_exactly_one_receipt_and_a_refused_payment_none(flow):
    loan, first = _paid(flow, 3_000)
    second = flow.pay(loan["id"], 1_000).json()["payment"]
    refused = flow.pay(loan["id"], 999_999)

    assert refused.status_code == 422
    assert len(_receipts(flow, first["id"])) == 1
    assert len(_receipts(flow, second["id"])) == 1
    notices = flow._get("/v1/notifications", ADMIN).json()
    assert [n["kind"] for n in notices].count(RECEIPT) == 2


def test_t4_the_notice_api_never_exposes_the_payload(flow):
    _, payment = _paid(flow, 3_000)

    notice = _receipts(flow, payment["id"])[0]

    assert "payload" not in notice
    assert (notice["payment_id"], notice["disbursement_id"]) == (payment["id"], None)


def test_ca12_a_failed_receipt_keeps_the_payment_and_stays_visible_to_the_administrator(
    flow, notifier
):
    loan, payment = _paid(flow, 3_000)
    box = flow.cash_balance()
    notifier.failing = True

    flow.dispatch()

    notice = _receipts(flow, payment["id"])[0]
    assert (notice["status"], notice["attempts"]) == ("PENDIENTE", 1)
    assert notice["last_error"]
    assert notice["sent_at"] is None
    assert flow._get(f"/v1/loans/{loan['id']}").json()["outstanding_cents"] == 117_000
    assert len(flow._get(f"/v1/loans/{loan['id']}/payments").json()) == 1
    assert flow.cash_balance() == box


def test_ca12_the_receipt_is_not_lost_it_is_retried_and_ends_failed_after_five_attempts(
    flow, notifier
):
    _, payment = _paid(flow, 3_000)
    notifier.failing = True

    for _ in range(MAX_ATTEMPTS + 2):
        flow.dispatch()

    notice = _receipts(flow, payment["id"])[0]
    assert (notice["status"], notice["attempts"]) == ("FALLIDO", MAX_ATTEMPTS)


def test_ca12_a_receipt_pending_a_retry_is_delivered_when_the_channel_recovers(flow, notifier):
    _, payment = _paid(flow, 3_000)
    notifier.failing = True
    flow.dispatch()
    notifier.failing = False

    flow.dispatch()

    assert [n["status"] for n in _receipts(flow, payment["id"])] == ["ENVIADO"]
    assert _delivered(notifier, payment["id"])[0].payload["outstanding_cents"] == "117000"
