from typing import Any, assert_type

import pytest

from schemmy import Schema


class Item(Schema):
    sku: str
    qty: int = 1


class Order(Schema):
    id: int
    items: list[Item]
    note: str | None = None
    meta: Any = None


class TestToDict:
    """
    Conversion of schemas to dicts.
    """

    def test_nested(self) -> None:
        """
        Nested schemas and lists of schemas are converted recursively.
        """

        order = Order.validate({"id": 1, "items": [{"sku": "A1", "qty": 2}, {"sku": "B2"}]})

        assert order.to_dict() == {
            "id": 1,
            "items": [{"sku": "A1", "qty": 2}, {"sku": "B2", "qty": 1}],
            "note": None,
            "meta": None,
        }

    def test_declaration_order(self) -> None:
        """
        Keys follow field declaration order.
        """

        order = Order.validate({"meta": 1, "note": "n", "items": [], "id": 1})

        assert list(order.to_dict()) == ["id", "items", "note", "meta"]

    def test_schema_inside_any(self) -> None:
        """
        Schemas inside dicts and lists of an Any field are converted.
        """

        order = Order(id=1, items=[], meta={"items": [Item(sku="A1")]})

        assert order.to_dict()["meta"] == {"items": [{"sku": "A1", "qty": 1}]}

    def test_result_detached(self) -> None:
        """
        Changing the returned lists does not change the schema.
        """

        order = Order.validate({"id": 1, "items": [{"sku": "A1"}]})
        order.to_dict()["items"].clear()

        assert len(order.items) == 1

    def test_round_trip(self) -> None:
        """
        validate restores an equal schema from the to_dict result.
        """

        order = Order.validate({"id": 1, "items": [{"sku": "A1"}], "note": "n"})

        assert Order.validate(order.to_dict()) == order


class TestRepr:
    """
    String representation of schemas.
    """

    def test_repr(self) -> None:
        """
        repr lists fields in declaration order.
        """

        assert repr(Item(sku="A1", qty=2)) == "Item(sku='A1', qty=2)"

    def test_nested_repr(self) -> None:
        """
        Nested schemas use their own repr.
        """

        order = Order(id=1, items=[Item(sku="A1")])

        assert repr(order) == "Order(id=1, items=[Item(sku='A1', qty=1)], note=None, meta=None)"


class TestEquality:
    """
    Equality of schemas.
    """

    def test_equal(self) -> None:
        """
        Schemas of the same class with equal fields are equal.
        """

        assert Item(sku="A1") == Item(sku="A1", qty=1)

    def test_not_equal(self) -> None:
        """
        Schemas with different field values are not equal.
        """

        assert Item(sku="A1") != Item(sku="A1", qty=2)

    def test_different_classes(self) -> None:
        """
        Schemas of different classes are not equal even with the same fields.
        """

        class Other(Schema):
            sku: str
            qty: int = 1

        assert Item(sku="A1") != Other(sku="A1")

    def test_not_equal_to_dict(self) -> None:
        """
        A schema is not equal to a dict with the same data.
        """

        assert Item(sku="A1") != {"sku": "A1", "qty": 1}

    def test_unhashable(self) -> None:
        """
        Schemas are mutable and therefore unhashable.
        """

        with pytest.raises(TypeError):
            hash(Item(sku="A1"))


class TestTyping:
    """
    Static types seen by type checkers.
    The assertions are checked by ty and are no-ops at runtime.
    """

    def test_static_types(self) -> None:
        """
        Field and constructor types follow the annotations.
        """

        item = Item(sku="A1")
        order = Order.validate({"id": 1, "items": []})

        assert_type(item.qty, int)
        assert_type(order, Order)
        assert_type(order.note, str | None)
        assert_type(order.to_dict(), dict[str, Any])
