import pytest

from schemmy import Schema, ValidationError


class TestFloatType:
    """
    Validation of float fields.
    """

    @pytest.mark.parametrize(
        "value",
        [
            -123.0,
            0.0,
            23.34,
            1.00000001,
        ],
    )
    def test_success(self, value: float) -> None:
        """
        Valid values pass.
        """

        class S(Schema):
            field: float

        s = S(field=value)

        assert s.field == value, "check field value"
        assert isinstance(s.field, float), "check field type"

    @pytest.mark.parametrize(
        "value",
        [
            None,
            ...,
            "1234",
            "",
            "123.32",
            True,
            False,
            [],
            [123, 23],
            (2, 3),
        ],
    )
    def test_invalid_type(self, value: int) -> None:
        """
        Values of a wrong type fail.
        """

        class S(Schema):
            field: float

        with pytest.raises(ValidationError) as exc:
            S(field=value)

        error = exc.value.exceptions[0]

        assert len(exc.value.exceptions) == 1, "Check errors count"
        assert "Expected float" in error.message, "Check error message"
        assert error.location == ["field"], "Check error location"

    @pytest.mark.parametrize("value", [0, 34, -7, 2**53])
    def test_int_converted(self, value: int) -> None:
        """
        An int that float represents exactly is converted to float.
        """

        class S(Schema):
            field: float

        s = S(field=value)

        assert s.field == value
        assert type(s.field) is float

    @pytest.mark.parametrize("value", [2**53 + 1, 10**400])
    def test_int_not_representable(self, value: int) -> None:
        """
        An int that float cannot represent exactly fails.
        """

        class S(Schema):
            field: float

        with pytest.raises(ValidationError) as exc:
            S(field=value)

        assert exc.value.exceptions[0].message == f"Expected float, got int {value} that float cannot represent exactly"

    def test_int_in_float_list(self) -> None:
        """
        Ints inside list[float] are converted.
        """

        class S(Schema):
            field: list[float]

        assert S(field=[1, 2.5]).field == [1.0, 2.5]
        assert all(type(item) is float for item in S(field=[1, 2.5]).field)

    def test_union_order(self) -> None:
        """
        In int | float an int stays int because the first matching member wins.
        """

        class S(Schema):
            field: int | float

        assert type(S(field=1).field) is int
