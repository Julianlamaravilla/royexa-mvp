"""PR-05, invariant. UC-03. RN-04, INV-02, EV-12, ADR-004."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from threading import Barrier

from support import COLLECTOR

from royexa.adapters.memory import InMemoryUnitOfWork
from royexa.sales.application import ConfirmDisbursement

DEVICE_TIME = datetime(2026, 10, 30, 13, 59, tzinfo=UTC)
RECEIPT = "COMPROBANTE_DESEMBOLSO"


def _assert_settled_once(flow, disbursement, opening_balance):
    assert len(flow.ledger(disbursement["id"])) == 1
    assert flow.cash_balance() == opening_balance - disbursement["amount_cents"]
    receipts = [n for n in flow.notices(disbursement["id"]) if n["kind"] == RECEIPT]
    assert len(receipts) == 1


def test_pr05_retry_returns_the_first_result_without_a_second_effect(flow):
    """PR-05 / EV-12 / RN-04: a repeated confirmation changes nothing."""
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])

    first = flow.confirm(disbursement["id"], code)
    retry = flow.confirm(disbursement["id"], code)

    assert (first.status_code, retry.status_code) == (200, 200)
    assert retry.json() == first.json()
    _assert_settled_once(flow, disbursement, opening_balance)


def test_pr05_loser_of_the_uniqueness_race_recovers_the_committed_result(flow, container):
    """PR-05 / EV-12 / ADR-004: the transaction that loses at commit re-reads the first
    result; it reports no error and produces no second deduction or notice."""
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])
    actor = container.directory.user(COLLECTOR)
    competitor_ran = []

    class LosesTheRace(InMemoryUnitOfWork):
        def commit(self) -> None:
            if not competitor_ran:
                competitor_ran.append(True)
                container.confirm.execute(actor, disbursement["id"], code, DEVICE_TIME)
            super().commit()

    racing = replace(container.context, uow=lambda: LosesTheRace(container.store))

    result = ConfirmDisbursement(racing).execute(actor, disbursement["id"], code, DEVICE_TIME)

    assert competitor_ran
    assert result.status == "CONFIRMADO"
    _assert_settled_once(flow, disbursement, opening_balance)


def test_pr05_two_simultaneous_confirmations_settle_once(flow):
    """PR-05 / EV-12: the same guarantee across real threads, whatever the interleaving."""
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])
    start = Barrier(2)

    def confirm(_: int):
        start.wait()
        return flow.confirm(disbursement["id"], code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(confirm, range(2)))

    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    _assert_settled_once(flow, disbursement, opening_balance)
