from typing import Annotated, ClassVar

import pytest

from schemmy import Schema, ValidationError


class CallableValidator:
    """
    Validator implemented as an object with __call__.
    The instance has no __name__ attribute.
    """

    def __call__(self, value: int) -> int:
        raise ValueError("bad")


class TestDefaults:
    """
    Field default values.
    """

    def test_default_used_when_omitted(self) -> None:
        """
        An omitted field gets its default value.
        """

        class S(Schema):
            name: str
            limit: int = 10

        assert S(name="a").limit == 10

    def test_default_overridden(self) -> None:
        """
        A passed value replaces the default value.
        """

        class S(Schema):
            limit: int = 10

        assert S(limit=3).limit == 3

    def test_passed_value_validated(self) -> None:
        """
        A passed value is validated even when a default exists.
        """

        class S(Schema):
            limit: int = 10

        with pytest.raises(ValidationError) as exc:
            S(limit="3")

        assert exc.value.exceptions[0].location == ["limit"]

    def test_mutable_default_not_shared(self) -> None:
        """
        A mutable default value is copied for each instance.
        """

        class S(Schema):
            tags: list[str] = []  # noqa: RUF012

        first, second = S(), S()
        first.tags.append("x")

        assert second.tags == []

    def test_inherited_default(self) -> None:
        """
        A default value is inherited and can be overridden in a subclass.
        """

        class Base(Schema):
            a: int = 1
            b: int = 2

        class Child(Base):
            b: int = 20

        child = Child()

        assert (child.a, child.b) == (1, 20)


class TestClassVar:
    """
    ClassVar annotations.
    """

    def test_classvar_not_required(self) -> None:
        """
        A ClassVar is not a field and is not required in the input.
        """

        class S(Schema):
            limit: ClassVar[int] = 10
            x: int

        assert S(x=1).x == 1

    def test_classvar_not_accepted(self) -> None:
        """
        A ClassVar is not accepted in the input.
        """

        class S(Schema):
            limit: ClassVar[int] = 10

        with pytest.raises(ValidationError) as exc:
            S(limit=1)

        assert exc.value.exceptions[0].message == "Unknown field"


class TestErrorsOrder:
    """
    Error order.
    """

    def test_errors_follow_declaration_order(self) -> None:
        """
        Field errors follow field declaration order.
        """

        class S(Schema):
            c: int
            a: int
            b: int

        with pytest.raises(ValidationError) as exc:
            S(a="x", b="y", c="z")

        assert [error.location for error in exc.value.exceptions] == [["c"], ["a"], ["b"]]


class TestNonStringKeys:
    """
    Non-string keys in the input.
    """

    def test_validate_non_str_keys(self) -> None:
        """
        A non-string key passed to validate fails.
        """

        class S(Schema):
            a: int

        with pytest.raises(ValidationError) as exc:
            S.validate({1: 2})

        error = exc.value.exceptions[0]
        assert error.message == "Field name must be a string"
        assert error.location == ["1"]

    def test_nested_non_str_keys(self) -> None:
        """
        A non-string key in a nested schema fails with the field path.
        """

        class Inner(Schema):
            a: int

        class Outer(Schema):
            inner: Inner

        with pytest.raises(ValidationError) as exc:
            Outer(inner={1: 2})

        assert exc.value.exceptions[0].location == ["inner", "1"]


class TestNonDictInput:
    """
    Input other than a dict.
    """

    @pytest.mark.parametrize(
        ("value", "type_name"),
        [(None, "NoneType"), ([("a", 1)], "list"), ("a", "str"), (1, "int")],
    )
    def test_validate_non_dict(self, value: object, type_name: str) -> None:
        """
        Input other than a dict fails with a single error and an empty location.
        """

        class S(Schema):
            a: int

        with pytest.raises(ValidationError) as exc:
            S.validate(value)

        assert [(error.location, error.message) for error in exc.value.exceptions] == [
            ([], f"Expected dict, got {type_name}")
        ]


class TestSelfField:
    """
    Field named self.
    """

    def test_unknown_self_field(self) -> None:
        """
        An undeclared self key in the input is reported as an unknown field.
        """

        class S(Schema):
            a: int

        with pytest.raises(ValidationError) as exc:
            S.validate({"a": 1, "self": 2})

        assert [(error.location, error.message) for error in exc.value.exceptions] == [(["self"], "Unknown field")]

    def test_declared_self_field(self) -> None:
        """
        A declared self field is validated like any other field.
        """

        class S(Schema):
            self: int

        assert S.validate({"self": 1}).self == 1


class TestMisc:
    """
    Other cases.
    """

    def test_callable_object_validator(self) -> None:
        """
        An error from a validator object contains its class name.
        """

        class S(Schema):
            x: Annotated[int, CallableValidator()]

        with pytest.raises(ValidationError) as exc:
            S(x=1)

        assert exc.value.exceptions[0].message == "Validator CallableValidator failed: bad"

    def test_nested_instance_passed(self) -> None:
        """
        A nested schema instance is accepted unchanged.
        """

        class Inner(Schema):
            a: int

        class Outer(Schema):
            inner: Inner

        inner = Inner(a=1)

        assert Outer(inner=inner).inner is inner

    def test_nested_not_dict(self) -> None:
        """
        A nested schema accepts only a dict or a schema instance.
        """

        class Inner(Schema):
            a: int

        class Outer(Schema):
            inner: Inner

        with pytest.raises(ValidationError) as exc:
            Outer(inner=[1])

        error = exc.value.exceptions[0]
        assert error.message == "Expected dict or Inner, got list"
        assert str(error) == "(inner: Expected dict or Inner, got list. ['inner'])"

    def test_unsupported_type(self) -> None:
        """
        An unsupported annotation fails.
        """

        class S(Schema):
            x: set[int]

        with pytest.raises(ValidationError) as exc:
            S(x={1})

        assert exc.value.exceptions[0].message.startswith("Unsupported type")

    def test_unsupported_type_name(self) -> None:
        """
        The unsupported type error names the annotation with its arguments.
        """

        class S(Schema):
            x: frozenset[int | None]

        with pytest.raises(ValidationError) as exc:
            S(x=frozenset())

        assert exc.value.exceptions[0].message == "Unsupported type: frozenset[int | None]"

    def test_fields_cached_per_class(self) -> None:
        """
        Parent and subclass fields are resolved and cached separately.
        """

        class Base(Schema):
            a: int

        class Child(Base):
            b: int

        Base(a=1)

        assert Child(a=1, b=2).b == 2
        with pytest.raises(ValidationError):
            Base(a=1, b=2)
