from typing import Annotated, Optional

import pytest

from schemmy import Schema, ValidationError


def positive(value: int) -> int:
    """
    Only positive ints pass.
    """
    if value <= 0:
        raise ValueError("must be > 0")
    return value


class Item(Schema):
    sku: str


class TestOptional:
    """
    Optional fields declared as X | None and Optional[X].
    """

    @pytest.mark.parametrize("value", [None, 0, 42])
    def test_pipe_syntax_success(self, value: int | None) -> None:
        """
        X | None accepts None and values of X.
        """

        class S(Schema):
            field: int | None

        assert S(field=value).field == value

    @pytest.mark.parametrize("value", [None, 42])
    def test_optional_syntax_success(self, value: int | None) -> None:
        """
        Optional[X] accepts None and values of X.
        """

        class S(Schema):
            field: Optional[int]  # noqa: UP045

        assert S(field=value).field == value

    def test_invalid_value_reports_member_error(self) -> None:
        """
        A value other than None is validated by the single non-None member.
        """

        class S(Schema):
            field: int | None

        with pytest.raises(ValidationError) as exc:
            S(field="x")

        error = exc.value.exceptions[0]
        assert error.message == "Expected int, got str"
        assert error.location == ["field"]

    def test_none_for_required_type(self) -> None:
        """
        None is rejected for a type that is not optional.
        """

        class S(Schema):
            field: int

        with pytest.raises(ValidationError) as exc:
            S(field=None)

        assert exc.value.exceptions[0].message == "Expected int, got NoneType"

    def test_default_none(self) -> None:
        """
        An optional field with a None default can be omitted.
        """

        class S(Schema):
            field: int | None = None

        assert S().field is None

    def test_nested_schema_errors_kept(self) -> None:
        """
        Errors of an optional nested schema keep the nested path.
        """

        class S(Schema):
            item: Item | None

        with pytest.raises(ValidationError) as exc:
            S(item={"sku": 1})

        error = exc.value.exceptions[0]
        assert error.location == ["item", "sku"]
        assert error.message == "Expected str, got int"

    @pytest.mark.parametrize(("value", "expected"), [(None, None), ({"sku": "A1"}, Item(sku="A1"))])
    def test_nested_schema_success(self, value: dict[str, str] | None, expected: Item | None) -> None:
        """
        An optional nested schema accepts None and a dict.
        """

        class S(Schema):
            item: Item | None

        assert S(item=value).item == expected

    def test_optional_list_errors_indexed(self) -> None:
        """
        Errors of an optional list keep the item index.
        """

        class S(Schema):
            field: list[int] | None

        with pytest.raises(ValidationError) as exc:
            S(field=[1, "x"])

        assert exc.value.exceptions[0].location == ["field", 1]

    def test_optional_annotated(self) -> None:
        """
        Validators of an optional Annotated member run for values other than None.
        """

        class S(Schema):
            field: Annotated[int, positive] | None

        assert S(field=None).field is None
        with pytest.raises(ValidationError) as exc:
            S(field=0)

        assert exc.value.exceptions[0].message == "Validator positive failed: must be > 0"


class TestUnion:
    """
    Unions of several types.
    """

    @pytest.mark.parametrize("value", [1, "a"])
    def test_success(self, value: int | str) -> None:
        """
        A value of any member passes.
        """

        class S(Schema):
            field: int | str

        assert S(field=value).field == value

    def test_no_member_matches(self) -> None:
        """
        A value matching no member produces a single error with the whole union.
        """

        class S(Schema):
            field: int | str | None

        with pytest.raises(ValidationError) as exc:
            S(field=1.5)

        assert len(exc.value.exceptions) == 1
        assert exc.value.exceptions[0].message == "Expected int | str | None, got float"

    def test_error_names_annotated_member_by_base_type(self) -> None:
        """
        The union error names an Annotated member by its base type.
        """

        class S(Schema):
            field: Annotated[int, positive] | str

        with pytest.raises(ValidationError) as exc:
            S(field=1.5)

        assert exc.value.exceptions[0].message == "Expected int | str, got float"

    @pytest.mark.parametrize("annotation", [int | bool, bool | int])
    def test_bool_matches_bool_member(self, annotation: object) -> None:
        """
        True keeps the bool type in a union of int and bool.
        """

        class S(Schema):
            field: annotation  # ty: ignore[invalid-type-form]

        assert S(field=True).field is True

    def test_first_matching_member_wins(self) -> None:
        """
        Members are tried in declaration order.
        """

        class Wide(Schema):
            sku: str

        class Narrow(Schema):
            sku: str
            qty: int = 1

        class S(Schema):
            item: Wide | Narrow

        assert type(S(item={"sku": "A1"}).item) is Wide


class TestUnionErrors:
    """
    Errors of a union that no member matches.
    """

    def test_validator_error_of_matching_member(self) -> None:
        """
        A validator error is reported when only its member accepts the value type.
        """

        class S(Schema):
            field: Annotated[int, positive] | str

        with pytest.raises(ValidationError) as exc:
            S(field=-1)

        assert [(error.location, error.message) for error in exc.value.exceptions] == [
            (["field"], "Validator positive failed: must be > 0")
        ]

    def test_item_error_of_matching_member(self) -> None:
        """
        An item error is reported when only its member accepts the container.
        """

        class S(Schema):
            field: list[int] | str

        with pytest.raises(ValidationError) as exc:
            S(field=[1, "a"])

        assert [(error.location, error.message) for error in exc.value.exceptions] == [
            (["field", 1], "Expected int, got str")
        ]

    def test_no_member_matches_type(self) -> None:
        """
        A value of another type produces a single error that lists the members.
        """

        class S(Schema):
            field: Annotated[int, positive] | str

        with pytest.raises(ValidationError) as exc:
            S(field=1.5)

        assert [error.message for error in exc.value.exceptions] == ["Expected int | str, got float"]

    def test_several_members_match_type(self) -> None:
        """
        A dict rejected by several schema members produces a single error that lists the members.
        """

        class A(Schema):
            a: int

        class B(Schema):
            b: int

        class S(Schema):
            item: A | B

        with pytest.raises(ValidationError) as exc:
            S(item={"c": 1})

        assert [error.message for error in exc.value.exceptions] == ["Expected A | B, got dict"]
