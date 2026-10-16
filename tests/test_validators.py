from __future__ import annotations

from typing import Annotated, Any

import pytest

from schemmy import Schema, ValidationError


def v_positive_int(x: int) -> int:
    """
    Only positive ints pass.
    """
    if x <= 0:
        raise ValueError("must be > 0")
    return x


def v_strip(x: str) -> str:
    """
    Strips the string.
    """
    return x.strip()


def v_lower(x: str) -> str:
    """
    Lowercases the string.
    """
    return x.lower()


def v_non_empty_list(x: list[Any]) -> list[Any]:
    """
    The list must not be empty.
    """
    if not x:
        raise ValueError("list is empty")
    return x


def v_max_len_3(x: list[Any]) -> list[Any]:
    """
    List length is limited to 3.
    """
    if len(x) > 3:
        raise ValueError("list is too long")
    return x


def v_even(x: int) -> int:
    """
    Only even numbers pass.
    """
    if x % 2 != 0:
        raise ValueError("odd value")
    return x


class TestAnnotatedScalar:
    """
    Validators on scalar fields via Annotated[T, *validators].
    Validator behavior and call order are defined in _resolve_validators.
    The base type is checked first.
    Validators then run in order, an exception produces a FieldValidationError
    with the message 'Validator {name} failed: {exc}' and location=[field].
    """

    def test_scalar_transform_success(self) -> None:
        """
        A validator transforms a valid value.
        """

        class S(Schema):
            field: Annotated[str, v_strip, v_lower]

        s = S(field="  HeLLo  ")
        assert s.field == "hello"

    def test_scalar_validator_error(self) -> None:
        """
        A failing validator produces the documented message and location.
        """

        class S(Schema):
            field: Annotated[int, v_positive_int]

        with pytest.raises(ValidationError) as exc:
            S(field=0)

        err = exc.value.exceptions[0]
        assert "Validator v_positive_int failed: must be > 0" in err.message
        assert err.location == ["field"]

    def test_scalar_type_error_before_validators(self) -> None:
        """
        Validators are not called when the base type does not match.
        """

        class S(Schema):
            field: Annotated[int, v_positive_int]

        with pytest.raises(ValidationError) as exc:
            S(field="123")

        err = exc.value.exceptions[0]
        assert "Expected int" in err.message
        assert err.location == ["field"]


class TestAnnotatedLists:
    """
    Annotated validation of lists.
    A list-level validator is declared as Annotated[list[T], *validators].
    An item-level validator is declared as list[Annotated[T, *validators]].
    _resolve_list_type adds the item index to error locations.
    """

    def test_list_level_validators_success(self) -> None:
        """
        List-level validators receive the whole list after the items are checked.
        """

        class S(Schema):
            field: Annotated[list[int], v_non_empty_list, v_max_len_3]

        s = S(field=[1, 2, 3])
        assert s.field == [1, 2, 3]

    def test_list_level_validator_error_empty(self) -> None:
        """
        A list-level validator rejects an empty list.
        """

        class S(Schema):
            field: Annotated[list[int], v_non_empty_list]

        with pytest.raises(ValidationError) as exc:
            S(field=[])

        err = exc.value.exceptions[0]
        assert "Validator v_non_empty_list failed: list is empty" in err.message
        assert err.location == ["field"]

    def test_list_item_validators_success(self) -> None:
        """
        An item-level validator runs for each item.
        """

        class S(Schema):
            field: list[Annotated[int, v_even, v_positive_int]]

        s = S(field=[2, 4, 6])
        assert s.field == [2, 4, 6]

    def test_list_item_validator_error_indexed(self) -> None:
        """
        Item validator errors have the item index in the location: ['field', idx].
        """

        class S(Schema):
            field: list[Annotated[int, v_even, v_positive_int]]

        with pytest.raises(ValidationError) as exc:
            S(field=[2, 3, -4])

        errors = exc.value.exceptions
        assert len(errors) == 2

        assert errors[0].location == ["field", 1]
        assert "Validator v_even failed: odd value" in errors[0].message

        assert errors[1].location == ["field", 2]
        assert "Validator v_positive_int failed: must be > 0" in errors[1].message

    def test_list_root_type_error(self) -> None:
        """
        A non-list value for Annotated[list[T], ...] produces a list type error.
        """

        class S(Schema):
            field: Annotated[list[int], v_non_empty_list]

        with pytest.raises(ValidationError) as exc:
            S(field="not-a-list")

        err = exc.value.exceptions[0]
        assert "Expected list[" in err.message
        assert err.location == ["field"]
