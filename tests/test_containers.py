import typing
from typing import Annotated, Literal

import pytest

from schemmy import Schema, ValidationError


def strip(value: str) -> str:
    """
    Strips the string.
    """
    return value.strip()


class Item(Schema):
    sku: str


class TestLiteral:
    """
    Validation of Literal fields.
    """

    @pytest.mark.parametrize("value", ["new", "done"])
    def test_success(self, value: str) -> None:
        """
        One of the literals passes.
        """

        class S(Schema):
            status: Literal["new", "done"]

        assert S(status=value).status == value

    def test_invalid_value(self) -> None:
        """
        A value outside the literals fails and is shown in the message.
        """

        class S(Schema):
            status: Literal["new", "done"]

        with pytest.raises(ValidationError) as exc:
            S(status="x")

        error = exc.value.exceptions[0]
        assert error.message == "Expected Literal['new', 'done'], got 'x'"
        assert error.location == ["status"]

    @pytest.mark.parametrize("value", [True, 1.0])
    def test_type_must_match(self, value: object) -> None:
        """
        An equal value of another type does not match the literal.
        """

        class S(Schema):
            code: Literal[1]

        with pytest.raises(ValidationError):
            S(code=value)

    def test_bool_literal_rejects_int(self) -> None:
        """
        1 does not match Literal[True].
        """

        class S(Schema):
            flag: Literal[True]

        with pytest.raises(ValidationError):
            S(flag=1)

    def test_optional(self) -> None:
        """
        An optional Literal accepts None.
        """

        class S(Schema):
            status: Literal["new"] | None = None

        assert S().status is None
        assert S(status="new").status == "new"

    def test_in_list(self) -> None:
        """
        Literal errors inside a list have the item index.
        """

        class S(Schema):
            statuses: list[Literal["new", "done"]]

        with pytest.raises(ValidationError) as exc:
            S(statuses=["new", "x"])

        assert exc.value.exceptions[0].location == ["statuses", 1]


class TestDict:
    """
    Validation of dict[K, V] fields.
    """

    def test_success(self) -> None:
        """
        A dict with valid keys and values passes.
        """

        class S(Schema):
            prices: dict[str, int]

        assert S(prices={"A1": 10, "B2": 20}).prices == {"A1": 10, "B2": 20}

    def test_values_normalized(self) -> None:
        """
        Validators of the value type normalize dict values.
        """

        class S(Schema):
            names: dict[str, Annotated[str, strip]]

        assert S(names={"a": "  Ann  "}).names == {"a": "Ann"}

    def test_value_error(self) -> None:
        """
        A value error has the key in its location.
        """

        class S(Schema):
            prices: dict[str, int]

        with pytest.raises(ValidationError) as exc:
            S(prices={"A1": 10, "B2": "x"})

        error = exc.value.exceptions[0]
        assert error.location == ["prices", "B2"]
        assert error.message == "Expected int, got str"

    def test_key_error(self) -> None:
        """
        A key error has the key in its location and a marked message.
        """

        class S(Schema):
            names: dict[int, str]

        with pytest.raises(ValidationError) as exc:
            S(names={"a": "x"})

        error = exc.value.exceptions[0]
        assert error.location == ["names", "a"]
        assert error.message == "Invalid key: Expected int, got str"

    def test_non_scalar_key_location(self) -> None:
        """
        A key that is neither str nor int appears in the location as its repr.
        """

        class S(Schema):
            prices: dict[str, int]

        with pytest.raises(ValidationError) as exc:
            S(prices={(1, 2): 1})

        assert exc.value.exceptions[0].location == ["prices", "(1, 2)"]

    def test_not_a_dict(self) -> None:
        """
        A value other than dict fails.
        """

        class S(Schema):
            prices: dict[str, int]

        with pytest.raises(ValidationError) as exc:
            S(prices=[("A1", 10)])

        assert exc.value.exceptions[0].message == "Expected dict[str, int], got list"

    def test_nested_schemas(self) -> None:
        """
        Schema values are built from dicts and their errors keep the full path.
        """

        class S(Schema):
            items: dict[str, Item]

        assert S(items={"a": {"sku": "A1"}}).items == {"a": Item(sku="A1")}
        with pytest.raises(ValidationError) as exc:
            S(items={"a": {"sku": 1}})

        assert exc.value.exceptions[0].location == ["items", "a", "sku"]

    def test_bare_dict(self) -> None:
        """
        A bare dict annotation accepts any dict.
        """

        class S(Schema):
            data: dict

        assert S(data={1: "a"}).data == {1: "a"}

    def test_to_dict(self) -> None:
        """
        to_dict converts schema values of a dict.
        """

        class S(Schema):
            items: dict[str, Item]

        assert S(items={"a": {"sku": "A1"}}).to_dict() == {"items": {"a": {"sku": "A1"}}}


class TestTuple:
    """
    Validation of tuple fields.
    """

    @pytest.mark.parametrize("value", [[1, 2, 3], (1, 2, 3)])
    def test_variadic_success(self, value: list[int] | tuple[int, ...]) -> None:
        """
        tuple[T, ...] accepts a list or a tuple and stores a tuple.
        """

        class S(Schema):
            ids: tuple[int, ...]

        assert S(ids=value).ids == (1, 2, 3)

    def test_variadic_item_error(self) -> None:
        """
        An item error of tuple[T, ...] has the item index.
        """

        class S(Schema):
            ids: tuple[int, ...]

        with pytest.raises(ValidationError) as exc:
            S(ids=[1, "x"])

        error = exc.value.exceptions[0]
        assert error.location == ["ids", 1]
        assert error.message == "Expected int, got str"

    def test_fixed_success(self) -> None:
        """
        tuple[T1, T2] validates each position against its own type.
        """

        class S(Schema):
            pair: tuple[str, int]

        assert S(pair=["a", 1]).pair == ("a", 1)

    def test_fixed_item_error(self) -> None:
        """
        An item error of a fixed tuple has the item index.
        """

        class S(Schema):
            pair: tuple[str, int]

        with pytest.raises(ValidationError) as exc:
            S(pair=["a", "b"])

        assert exc.value.exceptions[0].location == ["pair", 1]

    @pytest.mark.parametrize("value", [["a"], ["a", 1, 2]])
    def test_fixed_wrong_length(self, value: list[object]) -> None:
        """
        A fixed tuple requires the exact number of items.
        """

        class S(Schema):
            pair: tuple[str, int]

        with pytest.raises(ValidationError) as exc:
            S(pair=value)

        assert exc.value.exceptions[0].message == f"Expected tuple[str, int] with 2 items, got {len(value)}"

    def test_empty_tuple(self) -> None:
        """
        tuple[()] accepts only an empty sequence.
        """

        class S(Schema):
            empty: tuple[()]

        assert S(empty=[]).empty == ()
        with pytest.raises(ValidationError):
            S(empty=[1])

    def test_not_a_sequence(self) -> None:
        """
        A string is not accepted as a tuple.
        """

        class S(Schema):
            ids: tuple[int, ...]

        with pytest.raises(ValidationError) as exc:
            S(ids="123")

        assert exc.value.exceptions[0].message == "Expected tuple[int, ...], got str"

    def test_nested_schemas_round_trip(self) -> None:
        """
        A tuple of schemas survives to_dict and validate.
        """

        class S(Schema):
            items: tuple[Item, ...]

        s = S.validate({"items": [{"sku": "A1"}, {"sku": "B2"}]})

        assert s.items == (Item(sku="A1"), Item(sku="B2"))
        assert s.to_dict() == {"items": ({"sku": "A1"}, {"sku": "B2"})}
        assert S.validate(s.to_dict()) == s


class TestBareTypingAliases:
    """
    typing.List, typing.Dict and typing.Tuple without arguments.
    """

    def test_items_accepted_as_any(self) -> None:
        """
        Items of bare aliases are accepted as Any.
        """

        class S(Schema):
            items: typing.List  # noqa: UP006
            mapping: typing.Dict  # noqa: UP006
            pair: typing.Tuple  # noqa: UP006

        s = S.validate({"items": [1, "a"], "mapping": {1: "a"}, "pair": [1, "a"]})

        assert (s.items, s.mapping, s.pair) == ([1, "a"], {1: "a"}, (1, "a"))

    @pytest.mark.parametrize(
        ("annotation", "message"),
        [
            (typing.List, "Expected list[Any], got str"),  # noqa: UP006
            (typing.Dict, "Expected dict[Any, Any], got str"),  # noqa: UP006
            (typing.Tuple, "Expected tuple[Any, ...], got str"),  # noqa: UP006
        ],
    )
    def test_container_type_checked(self, annotation: object, message: str) -> None:
        """
        A bare alias still requires its container type.
        """

        S = type("S", (Schema,), {"__annotations__": {"value": annotation}})

        with pytest.raises(ValidationError) as exc:
            S.validate({"value": "x"})

        assert exc.value.exceptions[0].message == message
