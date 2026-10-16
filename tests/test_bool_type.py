import pytest

from schemmy import Schema, ValidationError


class TestBoolType:
    """
    Validation of bool fields.
    """

    @pytest.mark.parametrize(
        "value",
        [
            True,
            False,
        ],
    )
    def test_success(self, value: bool) -> None:
        """
        Valid values pass.
        """

        class S(Schema):
            field: bool

        s = S(field=value)

        assert s.field == value, "check field value"
        assert isinstance(s.field, bool), "check field type"

    @pytest.mark.parametrize(
        "value",
        [
            "true",
            "True",
            "False",
            1,
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
    def test_invalid_type(self, value: bool) -> None:
        """
        Values of a wrong type fail.
        """

        class S(Schema):
            field: bool

        with pytest.raises(ValidationError) as exc:
            S(field=value)

        error = exc.value.exceptions[0]

        assert len(exc.value.exceptions) == 1, "Check errors count"
        assert "Expected bool" in error.message, "Check error message"
        assert error.location == ["field"], "Check error location"
