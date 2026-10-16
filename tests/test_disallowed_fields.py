from typing import Any

import pytest

from schemmy import Schema, ValidationError


class TestDisallowedFields:
    """
    Unknown fields.
    """

    @pytest.mark.parametrize(
        ("fields", "expected_error_count"),
        [
            ({"a": 1, "field": "sf"}, 1),
            ({"a": 1, "b": 2.2, "field": "sf"}, 2),
            ({"b": 2.2, "field": "sf"}, 1),
            ({"a": 1, "b": 2.2, "c": "3dsfsd", "field": "sf"}, 3),
        ],
    )
    def test_missing_field(self, fields: dict[str, Any], expected_error_count: int) -> None:
        class S(Schema):
            field: str

        with pytest.raises(ValidationError) as exc:
            S.validate(fields)

        assert len(exc.value.exceptions) == expected_error_count, "Check errors count"

        for error in exc.value.exceptions:
            assert "Unknown field" in error.message, "Check error message"
