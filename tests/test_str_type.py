import pytest

from schemmy import Schema, ValidationError


class TestStrType:
    """
    Validation of str fields.
    """

    @pytest.mark.parametrize(
        "value",
        [
            "123",
            "bar",
            "asd",
            "8 (950) 288-56-23",
            "",
            "  with spaces  ",
            "ユニコード",  # unicode
        ],
    )
    def test_success(self, value: str) -> None:
        """
        Valid values pass.
        """

        class S(Schema):
            field: str

        s = S(field=value)

        assert s.field == value, "check field value"
        assert isinstance(s.field, str), "check field type"

    @pytest.mark.parametrize(
        "value",
        [None, ..., 1234, 34.43, [], [123, 23], (2, 3), ["string", "fdf"]],
    )
    def test_invalid_type(self, value: str) -> None:
        """
        Values of a wrong type fail.
        """

        class S(Schema):
            field: str

        with pytest.raises(ValidationError) as exc:
            S(field=value)

        error = exc.value.exceptions[0]

        assert len(exc.value.exceptions) == 1, "Check errors count"
        assert "Expected str" in error.message, "Check error message"
        assert error.location == ["field"], "Check error location"
