from __future__ import annotations

from typing import cast


class FieldValidationError(Exception):
    """
    Validation error of a single schema field.
    """

    def __init__(self, *, field: str, message: str, location: list[str | int]) -> None:
        self.field: str = field
        self.message: str = message
        self.location: list[str | int] = location

    def __str__(self) -> str:
        return f"({self.field}: {self.message}. {self.location})"


class ValidationError(ExceptionGroup[FieldValidationError]):
    """
    Group of schema validation errors.
    """

    @property
    def exceptions(self) -> tuple[FieldValidationError, ...]:
        """
        Field validation errors.
        Contains no nested groups.
        """

        return cast("tuple[FieldValidationError, ...]", super().exceptions)
