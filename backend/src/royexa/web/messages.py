"""What the pages say when the domain refuses something. T7d closes the list."""

from royexa.cash_box.domain import (
    CashBoxClosed,
    CashClose,
    CashCloseNotAllowed,
    InvalidPeriod,
    NoOpenCashBox,
    PendingVisitsRemain,
)
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
    ApproverRoleRequired,
    CodeLocked,
    DeciderRoleRequired,
    SelfApprovalForbidden,
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
from royexa.web.format import money
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
    ReasonRequired: "Escribe el motivo.",
    SelfApprovalForbidden: "No puedes aprobar una solicitud que tú mismo originaste: la aprueba otro administrador.",
    ApproverRoleRequired: "Solo un administrador aprueba.",
    DeciderRoleRequired: "Solo un administrador rechaza.",
    PendingVisitsRemain: (
        "Quedan clientes pendientes de visita: registra su pago o su no pago antes de cerrar la caja."
    ),
    CashCloseNotAllowed: "Solo el cobrador de la caja la cierra.",
    InvalidPeriod: "El período debe ir de una fecha a otra posterior y abarcar como máximo un año.",
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
    CodeLocked: "Se escribieron 5 códigos incorrectos seguidos: la solicitud queda bloqueada 15 minutos. Vuelve a intentarlo después.",
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


_BADGES = {
    DisbursementStatus.REQUESTED: ("wait", "En espera"),
    DisbursementStatus.PENDING_AUTHORIZATION: ("wait", "Por autorizar"),
    DisbursementStatus.APPROVED: ("info", "Aprobado"),
    DisbursementStatus.REJECTED: ("bad", "Rechazado"),
    DisbursementStatus.CONFIRMED: ("ok", "Entregado"),
    DisbursementStatus.EXPIRED: ("bad", "Caducado"),
}


def status_kind(disbursement: Disbursement) -> str:
    return _BADGES[disbursement.status][0]


def status_short(disbursement: Disbursement) -> str:
    return _BADGES[disbursement.status][1]


def status_text(disbursement: Disbursement) -> str:
    return _STATUS[disbursement.status]


def waiting_text(disbursement: Disbursement) -> str:
    """For the administrator: what the request is waiting for."""
    if disbursement.status is DisbursementStatus.PENDING_AUTHORIZATION:
        return "Esperando la autorización: supera el límite del cobrador."
    return "Esperando la aprobación."


def close_summary(close: CashClose, symbol: str = "") -> str:
    """RF-02, CA-03: what the day should have delivered, what was delivered and the gap."""
    gap = close.discrepancy.cents
    if gap == 0:
        tail = "Sin descuadre."
    else:
        tail = f"{'Sobran' if gap > 0 else 'Faltan'} {money(abs(gap), symbol)}."
    expected, delivered = money(close.expected.cents, symbol), money(close.delivered.cents, symbol)
    return f"Esperado {expected}. Entregado {delivered}. {tail}"


def describe(error: DomainError) -> str:
    for kind in type(error).__mro__:
        if kind in _MESSAGES:
            return _MESSAGES[kind]
    return GENERIC
