from __future__ import annotations

from functools import partial
from typing import Any, cast


class FieldValidationError(Exception):
    """
    Validation error of a single schema field.
    """

    def __init__(self, *, field: str, message: str, location: list[str | int]) -> None:
        super().__init__(message)
        self.field: str = field
        self.message: str = message
        self.location: list[str | int] = location

    def __reduce__(self) -> tuple[Any, ...]:
        """
        Rebuilds the error from its keyword arguments.
        Required for pickle and copy, because the constructor is keyword-only.
        """

        return partial(type(self), field=self.field, message=self.message, location=self.location), ()

    def __str__(self) -> str:
        if not self.field:
            return f"({self.message}. {self.location})"
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
