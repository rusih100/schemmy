from typing import Any

import pytest

from schemmy import Schema, ValidationError


class TestMissingFields:
    """
    Missing fields.
    """

    @pytest.mark.parametrize(
        ("fields", "expected_error_count"),
        [
            ({}, 4),
            ({"a": 1}, 3),
            ({"a": 1, "b": 2.2}, 2),
            ({"b": 2.2}, 3),
            ({"a": 1, "b": 2.2, "c": "3dsfsd"}, 1),
        ],
    )
    def test_missing_field(self, fields: dict[str, Any], expected_error_count: int) -> None:
        class S(Schema):
            a: int
            b: float
            c: str
            d: bool

        with pytest.raises(ValidationError) as exc:
            S.validate(fields)

        assert len(exc.value.exceptions) == expected_error_count, "Check errors count"

        for error in exc.value.exceptions:
            assert "Field required" in error.message, "Check error message"
