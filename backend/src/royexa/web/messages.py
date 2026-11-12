"""What the pages say when the domain refuses something. T7d adds its cases."""

from royexa.cash_box.domain import CashBoxClosed, NoOpenCashBox
from royexa.clients.domain import ClientNotFound
from royexa.loans.domain import (
    InvalidCommitmentDate,
    InvalidLoanTerms,
    LoanAlreadySettled,
    LoanNotFound,
    PaymentExceedsBalance,
    PaymentNotAllowed,
    PriorLoanNotSettled,
    ReasonRequired,
    VisitNotAllowed,
)
from royexa.sales.domain import (
    AmountExceedsRouteLimit,
    ClientOutsideRoute,
    ConfirmationCodeExpired,
    Disbursement,
    DisbursementNotFound,
    DisbursementStatus,
    InvalidConfirmationCode,
    InvalidTransition,
    RequesterNotAllowed,
    ValidatorNotAllowed,
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
    AmountExceedsRouteLimit: "El monto supera el límite de la ruta. Pide uno menor.",
    ClientOutsideRoute: "Este cliente no es de tu ruta: solo su cobrador solicita desembolsos.",
    RequesterNotAllowed: "Tu usuario no puede solicitar desembolsos.",
    PriorLoanNotSettled: "El cliente tiene un préstamo anterior sin liquidar. Debe pagarlo antes de recibir otro.",
    InvalidLoanTerms: "El plazo debe tener al menos un día de cobro por cuota, y las cuotas y el monto deben ser mayores que cero.",
    InvalidConfirmationCode: "El código no es correcto. Revisa que sea el que recibió el cliente.",
    ConfirmationCodeExpired: (
        "El código caducó. La solicitud quedó caducada y el intento quedó registrado en el libro; "
        "no se entregó dinero. Pide una solicitud nueva."
    ),
    ValidatorNotAllowed: "Solo el cobrador de la ruta valida el código.",
    InvalidTransition: "La solicitud no está en un estado que permita esta operación.",
    DisbursementNotFound: "No se encontró la solicitud.",
    NotFound: "No se encontró lo que se pedía.",
}


_STATUS = {
    DisbursementStatus.REQUESTED: "Esperando la aprobación del administrador.",
    DisbursementStatus.PENDING_AUTHORIZATION: (
        "Esperando la autorización del administrador: supera tu límite."
    ),
    DisbursementStatus.APPROVED: (
        "Aprobado. Pídele al cliente el código que recibió y escríbelo aquí."
    ),
    DisbursementStatus.REJECTED: "Rechazado por el administrador.",
    DisbursementStatus.CONFIRMED: "Confirmado: el dinero ya se entregó.",
    DisbursementStatus.EXPIRED: "El código caducó. Esta solicitud ya no se puede confirmar.",
}


def status_text(disbursement: Disbursement) -> str:
    return _STATUS[disbursement.status]


def describe(error: DomainError) -> str:
    for kind in type(error).__mro__:
        if kind in _MESSAGES:
            return _MESSAGES[kind]
    return GENERIC
