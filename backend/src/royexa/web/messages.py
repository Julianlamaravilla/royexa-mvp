"""What the pages say when the domain refuses something. T7c and T7d add their cases."""

from royexa.cash_box.domain import CashBoxClosed, NoOpenCashBox
from royexa.clients.domain import ClientNotFound
from royexa.loans.domain import (
    InvalidCommitmentDate,
    LoanAlreadySettled,
    LoanNotFound,
    PaymentExceedsBalance,
    PaymentNotAllowed,
    ReasonRequired,
    VisitNotAllowed,
)
from royexa.shared.errors import DomainError, NotFound, WriteConflict
from royexa.shared.money import InvalidAmount

GENERIC = "No se pudo completar la operación."

_MESSAGES: dict[type[DomainError], str] = {
    PaymentExceedsBalance: "El pago es mayor que el saldo del préstamo. Escribe un importe igual o menor al saldo.",
    InvalidAmount: "El importe debe ser mayor que cero.",
    PaymentNotAllowed: "Este cliente no es de tu ruta: solo su cobrador registra pagos.",
    VisitNotAllowed: "Este cliente no es de tu ruta: solo su cobrador registra visitas.",
    LoanAlreadySettled: "El préstamo ya está liquidado: no hay saldo por cobrar.",
    InvalidCommitmentDate: "La fecha de compromiso debe ser posterior a hoy.",
    ReasonRequired: "Escribe el motivo del no pago.",
    CashBoxClosed: "La caja del día ya está cerrada: no admite más movimientos.",
    NoOpenCashBox: "Hoy no hay caja disponible: no es día de cobranza.",
    WriteConflict: "Otra operación se cruzó con esta y no se guardó nada. Revisa la ruta e inténtalo de nuevo.",
    LoanNotFound: "No se encontró el préstamo.",
    ClientNotFound: "No se encontró el cliente.",
    NotFound: "No se encontró lo que se pedía.",
}


def describe(error: DomainError) -> str:
    for kind in type(error).__mro__:
        if kind in _MESSAGES:
            return _MESSAGES[kind]
    return GENERIC
