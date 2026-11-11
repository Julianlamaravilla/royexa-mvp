"""T3a, RN-01 and EC-03: the allocation of a payment is exact and repeatable. Pure domain."""

from datetime import date
from fractions import Fraction

import pytest

from royexa.loans.domain import (
    Installment,
    Loan,
    PaymentExceedsBalance,
    exact_decimal,
)
from royexa.shared.money import InvalidAmount, Money


def _loan(count: int = 20, amount: int = 5_000) -> Loan:
    return Loan(
        "prestamo-1",
        "cliente-1",
        None,
        Money(count * amount),
        Money(0),
        tuple(Installment(n, date(2026, 11, 2 + n), Money(amount)) for n in range(1, count + 1)),
    )


def test_ec03_25_over_a_20_installment_loan_of_50_leaves_19_5_remaining():
    loan, allocations = _loan().apply_payment(Money(2_500))

    assert exact_decimal(loan.remaining_installments) == "19.5"
    assert loan.installment_count == 20
    assert [(item.sequence, item.amount) for item in allocations] == [(1, Money(2_500))]
    assert loan.installments[0].pending == Money(2_500)
    assert loan.outstanding == Money(97_500)


def test_ec03_the_same_case_gives_the_same_result_every_time():
    results = {
        (exact_decimal(loan.remaining_installments), loan.outstanding.cents)
        for loan in (_loan().apply_payment(Money(2_500))[0] for _ in range(50))
    }

    assert results == {("19.5", 97_500)}


def test_ec03_an_exact_payment_settles_one_installment():
    loan, allocations = _loan().apply_payment(Money(5_000))

    assert exact_decimal(loan.remaining_installments) == "19"
    assert [(a.sequence, a.amount) for a in allocations] == [(1, Money(5_000))]


def test_ec03_an_excess_goes_to_the_next_installment():
    loan, allocations = _loan().apply_payment(Money(7_000))

    assert [(a.sequence, a.amount) for a in allocations] == [(1, Money(5_000)), (2, Money(2_000))]
    assert exact_decimal(loan.remaining_installments) == "18.6"


def test_rn01_payments_accumulate_on_the_oldest_pending_installment():
    first, _ = _loan().apply_payment(Money(2_500))
    second, allocations = first.apply_payment(Money(2_500))

    assert [(a.sequence, a.amount) for a in allocations] == [(1, Money(2_500))]
    assert exact_decimal(second.remaining_installments) == "19"
    assert second.installments[0].pending == Money(0)


def test_rn01_the_whole_balance_settles_the_loan():
    loan, allocations = _loan(count=2).apply_payment(Money(10_000))

    assert loan.is_settled
    assert loan.remaining_installments == Fraction(0)
    assert len(allocations) == 2


def test_rn01_a_payment_never_exceeds_the_balance_and_changes_nothing_when_refused():
    loan = _loan(count=2)

    with pytest.raises(PaymentExceedsBalance):
        loan.apply_payment(Money(10_001))

    assert loan.outstanding == Money(10_000)


@pytest.mark.parametrize("cents", [0, -1])
def test_rn01_a_payment_must_be_positive(cents):
    with pytest.raises(InvalidAmount):
        _loan().apply_payment(Money(cents))


def test_ec03_the_counter_is_exact_even_when_it_has_no_finite_decimal():
    loan = Loan("p", "c", None, Money(3), Money(0), (Installment(1, date(2026, 11, 2), Money(3)),))

    partial, _ = loan.apply_payment(Money(1))

    assert partial.remaining_installments == Fraction(2, 3)
    assert exact_decimal(partial.remaining_installments) == "2/3"


def test_ec03_unequal_installments_count_each_one_by_its_own_amount():
    loan = Loan(
        "p",
        "c",
        None,
        Money(150),
        Money(0),
        (
            Installment(1, date(2026, 11, 2), Money(50)),
            Installment(2, date(2026, 11, 3), Money(100)),
        ),
    )

    partial, _ = loan.apply_payment(Money(25))

    assert exact_decimal(partial.remaining_installments) == "1.5"
