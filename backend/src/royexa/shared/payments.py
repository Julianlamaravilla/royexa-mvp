"""How a payment was received. RES-01: it is information, never a flow of funds."""

from enum import StrEnum


class PaymentMethod(StrEnum):
    CASH = "EFECTIVO"
    TRANSFER = "TRANSFERENCIA"
