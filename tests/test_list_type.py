import pytest

from schemmy import Schema, ValidationError


class TestListType:
    """
    Validation of lists: lists of scalars, lists of schemas, nested lists,
    list[Any], multiple errors and a wrong root type.
    """

    @pytest.mark.parametrize(
        "value",
        [
            [1, 2, 3],
            [],
            [10**6, 0, -5],
        ],
    )
    def test_list_of_int_success(self, value: list[int]) -> None:
        """
        list[int] passes.
        """

        class S(Schema):
            field: list[int]

        s = S(field=value)
        assert s.field == value
        assert all(isinstance(x, int) for x in s.field)

    @pytest.mark.parametrize(
        "value",
        [
            ["a", "b", "c"],
            [],
            ["", "café", "ユニコード"],
        ],
    )
    def test_list_of_str_success(self, value: list[str]) -> None:
        """
        list[str] passes.
        """

        class S(Schema):
            field: list[str]

        s = S(field=value)
        assert s.field == value
        assert all(isinstance(x, str) for x in s.field)

    def test_list_of_int_with_invalid_element(self) -> None:
        """
        An item of a wrong type fails.
        The item index is inserted into the location: ["field", <idx>].
        """

        class S(Schema):
            field: list[int]

        with pytest.raises(ValidationError) as exc:
            S(field=[1, "bad", 3])

        errors = exc.value.exceptions
        assert len(errors) == 1, "Expected a single error"
        assert "Expected int" in errors[0].message
        assert errors[0].location == ["field", 1]

    def test_list_of_str_multiple_invalids(self) -> None:
        """
        Errors at several indexes of list[str] are all reported.
        Both errors have correct locations.
        """

        class S(Schema):
            field: list[str]

        with pytest.raises(ValidationError) as exc:
            S(field=["ok", 123, 4.5, "also ok"])

        errors = exc.value.exceptions

        assert len(errors) == 2
        assert errors[0].location == ["field", 1]
        assert "Expected str" in errors[0].message
        assert errors[1].location == ["field", 2]
        assert "Expected str" in errors[1].message

    def test_invalid_list_root_type(self) -> None:
        """
        A non-list value for list[T] fails.
        """

        class S(Schema):
            field: list[int]

        with pytest.raises(ValidationError) as exc:
            S(field="not-a-list")

        error = exc.value.exceptions[0]
        assert "Expected list[" in error.message
        assert error.location == ["field"]

    def test_list_of_schema_success(self) -> None:
        """
        A list of nested schemas passes.
        """

        class Item(Schema):
            sku: str
            qty: int

        class Order(Schema):
            items: list[Item]

        order = Order(items=[{"sku": "A1", "qty": 2}, {"sku": "B2", "qty": 5}])

        assert all(isinstance(i, Item) for i in order.items)
        assert order.items[0].sku == "A1"
        assert order.items[1].qty == 5

    def test_list_of_schema_with_child_errors(self) -> None:
        """
        A nested schema inside a list fails.
        Nested errors are unwrapped with the index: ["items", idx, <child_field>].
        """

        class Item(Schema):
            sku: str
            qty: int

        class Order(Schema):
            items: list[Item]

        with pytest.raises(ValidationError) as exc:
            Order(items=[{"sku": "A1", "qty": "bad"}, {"sku": 123, "qty": 10}])

        errors = exc.value.exceptions
        assert len(errors) == 2
        assert errors[0].location == ["items", 0, "qty"]
        assert "Expected int" in errors[0].message
        assert errors[1].location == ["items", 1, "sku"]
        assert "Expected str" in errors[1].message

    def test_nested_lists_success(self) -> None:
        """
        Nested lists list[list[int]] pass.
        """

        class S(Schema):
            field: list[list[int]]

        s = S(field=[[1, 2], [], [3]])
        assert s.field == [[1, 2], [], [3]]
        assert all(isinstance(x, list) for x in s.field)
        assert all(all(isinstance(v, int) for v in row) for row in s.field)

    def test_nested_lists_with_errors(self) -> None:
        """
        Errors inside nested lists list[list[int]].
        Both indexes are set: ["field", i, j].
        """

        class S(Schema):
            field: list[list[int]]

        with pytest.raises(ValidationError) as exc:
            S(field=[[1, "bad"], ["also", "bad"], [3]])

        errors = exc.value.exceptions
        assert len(errors) == 3
        assert errors[0].location == ["field", 0, 1]
        assert "Expected int" in errors[0].message
        assert errors[1].location == ["field", 1, 0]
        assert "Expected int" in errors[1].message
        assert errors[2].location == ["field", 1, 1]
        assert "Expected int" in errors[2].message

    @pytest.mark.parametrize(
        "value",
        [
            [1, "two", 3.14, {"k": "v"}, [5, 6]],
            [],
        ],
    )
    def test_list_of_any(self, value: list) -> None:
        """
        Items of list[Any] are returned unchanged.
        """

        from typing import Any

        class S(Schema):
            field: list[Any]

        s = S(field=value)
        assert s.field == value
