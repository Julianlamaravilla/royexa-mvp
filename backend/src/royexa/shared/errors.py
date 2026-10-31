"""Base errors shared by every module."""


class DomainError(Exception):
    """A business rule refused the operation."""


class NotFound(DomainError):
    """The referenced aggregate does not exist."""


class WriteConflict(DomainError):
    """A concurrent transaction won the race; this one was rolled back."""


class StaleWrite(WriteConflict):
    """The aggregate changed after this transaction read it."""
