import pytest

from schemmy import Schema, ValidationError


class TestNestedSchemas:
    """
    Nested schemas and lists of schemas.
    """

    def test_success_nested_schema(self) -> None:
        """
        A nested schema passes.
        """

        class Address(Schema):
            city: str
            zip_code: int

        class User(Schema):
            id: int
            address: Address

        user = User(id=1, address={"city": "Moscow", "zip_code": 101000})

        assert isinstance(user.address, Address), "address must be an Address instance"
        assert user.address.city == "Moscow"
        assert user.address.zip_code == 101000

    def test_invalid_type_in_nested_schema(self) -> None:
        """
        A wrong type inside a nested schema fails.
        """

        class Address(Schema):
            city: str
            zip_code: int

        class User(Schema):
            id: int
            address: Address

        with pytest.raises(ValidationError) as exc:
            User(id=1, address={"city": "Moscow", "zip_code": "bad"})

        error = exc.value.exceptions[0]
        assert "Expected int" in error.message
        assert error.location == ["address", "zip_code"]

    def test_list_of_nested_schemas_success(self) -> None:
        """
        A list of nested schemas passes.
        """

        class Item(Schema):
            sku: str
            qty: int

        class Order(Schema):
            items: list[Item]

        order = Order(
            items=[
                {"sku": "A1", "qty": 2},
                {"sku": "B2", "qty": 5},
            ]
        )

        assert all(isinstance(i, Item) for i in order.items)
        assert order.items[0].sku == "A1"
        assert order.items[1].qty == 5

    def test_list_of_nested_schemas_with_errors(self) -> None:
        """
        Invalid data in a list of nested schemas fails.
        """

        class Item(Schema):
            sku: str
            qty: int

        class Order(Schema):
            items: list[Item]

        with pytest.raises(ValidationError) as exc:
            Order(
                items=[
                    {"sku": "A1", "qty": "bad"},
                    {"sku": 123, "qty": 10},
                ]
            )

        errors = exc.value.exceptions
        assert len(errors) == 2
        assert errors[0].location == ["items", 0, "qty"]
        assert "Expected int" in errors[0].message
        assert errors[1].location == ["items", 1, "sku"]
        assert "Expected str" in errors[1].message

    def test_invalid_list_type(self) -> None:
        """
        A non-list value for a list field fails.
        """

        class Item(Schema):
            sku: str

        class Order(Schema):
            items: list[Item]

        with pytest.raises(ValidationError) as exc:
            Order(items="not-a-list")

        error = exc.value.exceptions[0]
        assert "Expected list[" in error.message
        assert error.location == ["items"]
