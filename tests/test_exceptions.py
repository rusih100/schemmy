import copy
import pickle
from collections.abc import Callable

import pytest

from schemmy import FieldValidationError, Schema, ValidationError


class Item(Schema):
    sku: str
    qty: int


def make_error() -> ValidationError:
    """
    Returns a validation error with two field errors.
    """

    try:
        Item.validate({"sku": 1, "qty": "2"})
    except ValidationError as exc:
        return exc
    raise AssertionError("validation passed")


class TestFieldValidationError:
    """
    Single field error.
    """

    def test_args(self) -> None:
        """
        The message is the only exception argument.
        """

        error = make_error().exceptions[0]

        assert error.args == ("Expected str, got int",)
        assert repr(error) == "FieldValidationError('Expected str, got int')"

    @pytest.mark.parametrize(
        "clone",
        [copy.copy, copy.deepcopy, lambda e: pickle.loads(pickle.dumps(e))],  # noqa: S301
    )
    def test_clone(self, clone: Callable[[FieldValidationError], FieldValidationError]) -> None:
        """
        copy, deepcopy and pickle keep field, message and location.
        """

        error = make_error().exceptions[0]
        cloned = clone(error)

        assert type(cloned) is FieldValidationError
        assert (cloned.field, cloned.message, cloned.location) == (error.field, error.message, error.location)

    def test_str_without_field(self) -> None:
        """
        An error without a field name omits it from the string.
        """

        with pytest.raises(ValidationError) as exc:
            Item.validate(None)

        assert str(exc.value.exceptions[0]) == "(Expected dict, got NoneType. [])"


class TestValidationError:
    """
    Group of field errors.
    """

    def test_pickle(self) -> None:
        """
        A pickled group keeps its type, message and field errors.
        """

        error = make_error()
        restored = pickle.loads(pickle.dumps(error))  # noqa: S301

        assert type(restored) is ValidationError
        assert restored.message == error.message
        assert [(e.location, e.message) for e in restored.exceptions] == [
            (e.location, e.message) for e in error.exceptions
        ]

    def test_except_star(self) -> None:
        """
        except* catches field errors by FieldValidationError.
        """

        caught: list[FieldValidationError] = []

        try:
            Item.validate({"sku": 1, "qty": 2})
        except* FieldValidationError as group:
            caught.extend(group.exceptions)

        assert [error.location for error in caught] == [["sku"]]
