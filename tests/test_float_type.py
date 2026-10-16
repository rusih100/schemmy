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
            0,
            34,
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
