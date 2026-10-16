from __future__ import annotations

from copy import deepcopy
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Literal,
    Union,
    dataclass_transform,
    get_args,
    get_origin,
    get_type_hints,
)

from schemmy.exceptions import FieldValidationError, ValidationError

if TYPE_CHECKING:
    from types import EllipsisType
    from typing import Self


type FieldName = str
type FieldValue = Any

type FieldsMapping = dict[FieldName, FieldValue]
type TypeHintsMapping = dict[FieldName, Any]


def _type_repr(annotation: Any) -> str:
    """
    Returns a readable name of an annotation for error messages.
    Unions are written as X | Y.
    Annotated metadata is omitted.
    """

    if annotation is NoneType:
        return "None"

    if annotation is Ellipsis:
        return "..."

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Union or origin is UnionType:
        return " | ".join(_type_repr(arg) for arg in args)

    if origin is Annotated:
        return _type_repr(args[0])

    if origin is not None:
        return f"{_type_repr(origin)}[{', '.join(_type_repr(arg) for arg in args)}]"

    if isinstance(annotation, type):
        return annotation.__name__

    return repr(annotation).removeprefix("typing.")


def _dump(value: Any) -> Any:
    """
    Converts schemas inside a value to dicts.
    Lists, tuples and dicts are traversed recursively.
    Other values are returned unchanged.
    """

    if isinstance(value, Schema):
        return value.to_dict()

    if isinstance(value, list):
        return [_dump(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_dump(item) for item in value)

    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}

    return value


@dataclass_transform(kw_only_default=True)
class Schema:
    """
    Base class for data schemas described with type annotations.
    Validates and normalizes input data on instantiation.
    Type checkers derive the constructor signature from the field annotations.
    """

    _schemmy_fields: ClassVar[tuple[TypeHintsMapping, FieldsMapping]]
    _origin_resolvers: ClassVar[dict[Any, str]] = {
        Annotated: "_resolve_validators",
        Union: "_resolve_union_type",
        UnionType: "_resolve_union_type",
        Literal: "_resolve_literal_type",
        list: "_resolve_list_type",
        tuple: "_resolve_tuple_type",
        dict: "_resolve_dict_type",
    }

    def __init__(self, **fields: FieldValue) -> None:
        """
        Validates the fields and sets them as instance attributes.

        :raise ValidationError: Schema validation failed.
        """

        values, errors = type(self)._run_validation(fields)

        for k, v in values.items():
            setattr(self, k, v)

        if errors:
            raise ValidationError(f"{type(self).__name__}: validation failed", errors)

    def __repr__(self) -> str:
        type_hints, _ = type(self)._get_fields()
        fields = ", ".join(f"{name}={getattr(self, name)!r}" for name in type_hints)
        return f"{type(self).__name__}({fields})"

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        type_hints, _ = type(self)._get_fields()
        return all(getattr(self, name) == getattr(other, name) for name in type_hints)

    def to_dict(self) -> dict[str, Any]:
        """
        Returns field values as a dict in field declaration order.
        Nested schemas are converted to dicts.
        Lists, tuples and dicts are traversed recursively.
        """

        type_hints, _ = type(self)._get_fields()
        return {name: _dump(getattr(self, name)) for name in type_hints}

    @classmethod
    def validate(cls, fields: FieldsMapping) -> Self:
        """
        Validates a mapping and returns a schema instance.

        :raise ValidationError: Schema validation failed.
        """

        non_str_keys = [key for key in fields if not isinstance(key, str)]
        if non_str_keys:
            raise ValidationError(
                f"{cls.__name__}: validation failed",
                [
                    FieldValidationError(
                        field=repr(key),
                        message="Field name must be a string",
                        location=[repr(key)],
                    )
                    for key in non_str_keys
                ],
            )

        return cls(**fields)

    @classmethod
    def _get_fields(cls) -> tuple[TypeHintsMapping, FieldsMapping]:
        """
        Returns field annotations and field default values.
        ClassVar annotations are not fields.
        The result is cached on the schema class.

        :returns: Field annotations, default values
        """

        cached = cls.__dict__.get("_schemmy_fields")
        if cached is not None:
            return cached

        type_hints: TypeHintsMapping = {
            name: hint
            for name, hint in get_type_hints(cls, include_extras=True).items()
            if hint is not ClassVar and get_origin(hint) is not ClassVar
        }

        defaults: FieldsMapping = {}
        for klass in reversed(cls.__mro__):
            if klass is Schema or not issubclass(klass, Schema):
                continue
            for name in type_hints:
                if name in klass.__dict__:
                    defaults[name] = klass.__dict__[name]

        cls._schemmy_fields = (type_hints, defaults)
        return cls._schemmy_fields

    @classmethod
    def _run_validation(cls, fields: FieldsMapping) -> tuple[FieldsMapping, list[FieldValidationError]]:
        """
        Validates and normalizes input data against the schema annotations.
        Missing and unknown fields are reported first.
        Value errors follow in field declaration order.

        :returns: Normalized values, validation errors
        """

        errors: list[FieldValidationError] = []
        type_hints, defaults = cls._get_fields()

        errors += cls._validate_missing_fields(fields, type_hints, defaults)
        errors += cls._validate_disallowed_fields(fields, type_hints)

        validated_fields, fields_errors = cls._validate_allowed_fields(fields, type_hints)
        errors += fields_errors

        for field, default in defaults.items():
            if field not in fields:
                validated_fields[field] = deepcopy(default)

        return validated_fields, errors

    @staticmethod
    def _validate_missing_fields(
        fields: FieldsMapping, type_hints: TypeHintsMapping, defaults: FieldsMapping
    ) -> list[FieldValidationError]:
        """
        Reports required fields absent from the input.
        A field with a default value is not required.

        :returns: Validation errors
        """

        return [
            FieldValidationError(
                field=field,
                message="Field required",
                location=[field],
            )
            for field in type_hints
            if field not in fields and field not in defaults
        ]

    @staticmethod
    def _validate_disallowed_fields(fields: FieldsMapping, type_hints: TypeHintsMapping) -> list[FieldValidationError]:
        """
        Reports input fields not declared in the schema.

        :returns: Validation errors
        """

        return [
            FieldValidationError(
                field=field,
                message="Unknown field",
                location=[field],
            )
            for field in fields
            if field not in type_hints
        ]

    @classmethod
    def _validate_allowed_fields(
        cls, fields: FieldsMapping, type_hints: TypeHintsMapping
    ) -> tuple[FieldsMapping, list[FieldValidationError]]:
        """
        Validates the values of declared fields present in the input.

        :returns: Normalized values, validation errors
        """

        errors: list[FieldValidationError] = []
        allowed_fields = [field for field in type_hints if field in fields]
        validated_fields: FieldsMapping = {}

        for field in allowed_fields:
            value = fields[field]
            expected_type = type_hints[field]

            validated_value, validation_errors = cls._check_field_type(field, value, expected_type)

            validated_fields[field] = validated_value
            errors += validation_errors

        return validated_fields, errors

    @classmethod
    def _check_field_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Dispatches a value to the resolver for its annotation.
        Supported annotations are Any, Annotated, unions, Literal, list, tuple, dict, Schema subclasses and plain classes.
        A value that fails validation is replaced with ellipsis.

        :returns: Normalized value, validation errors
        """

        origin = get_origin(expected_type)

        if expected_type is Any:
            return cls._resolve_any_type(field, value, expected_type)

        resolver_name = cls._origin_resolvers.get(origin)
        if resolver_name is not None:
            return getattr(cls, resolver_name)(field, value, expected_type)

        if origin is not None or not isinstance(expected_type, type):
            return cls._resolve_unsupported_type(field, value, expected_type)

        if issubclass(expected_type, Schema):
            return cls._resolve_schema_type(field, value, expected_type)

        if expected_type is float and type(value) is int:
            return cls._resolve_int_as_float(field, value)

        # bool is a subclass of int but is rejected for int fields.
        if not isinstance(value, expected_type) or (expected_type is int and isinstance(value, bool)):
            return cls._resolve_scalar_type(field, value, expected_type)

        return value, []

    @classmethod
    def _resolve_any_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for Any.
        The value is returned unchanged.
        No errors are produced.

        :returns: Normalized value, validation errors
        """

        return value, []

    @classmethod
    def _resolve_int_as_float(
        cls, field: FieldName, value: int
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for an int passed to a float field.
        JSON numbers without a fractional part arrive as int.
        The int is converted only when float represents it exactly.
        bool is not converted.

        :returns: Normalized value, validation errors
        """

        try:
            converted = float(value)
        except OverflowError:
            converted = None

        if converted is None or converted != value:
            return ..., [
                FieldValidationError(
                    field=field,
                    message=f"Expected float, got int {value} that float cannot represent exactly",
                    location=[field],
                )
            ]

        return converted, []

    @classmethod
    def _resolve_union_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for unions such as X | Y and Optional[X].
        None members are skipped for a value other than None.
        A single remaining member validates the value directly and reports its own errors.
        Otherwise members are tried in declaration order and the first match wins.

        :returns: Normalized value, validation errors
        """

        members = [member for member in get_args(expected_type) if value is None or member is not NoneType]

        if len(members) == 1:
            return cls._check_field_type(field, value, members[0])

        for member in members:
            validated_value, errors = cls._check_field_type(field, value, member)
            if not errors:
                return validated_value, []

        return ..., [
            FieldValidationError(
                field=field,
                message=f"Expected {_type_repr(expected_type)}, got {type(value).__name__}",
                location=[field],
            )
        ]

    @classmethod
    def _resolve_literal_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for Literal[...].
        The value must equal one of the literals and have the same type.
        The type check keeps True from matching Literal[1].

        :returns: Normalized value, validation errors
        """

        for literal in get_args(expected_type):
            if type(value) is type(literal) and value == literal:
                return value, []

        return ..., [
            FieldValidationError(
                field=field,
                message=f"Expected {_type_repr(expected_type)}, got {value!r}",
                location=[field],
            )
        ]

    @classmethod
    def _resolve_list_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for list[T].
        The value must be a list.
        Each item is validated against T.

        :returns: Normalized value, validation errors
        """

        if not isinstance(value, list):
            return cls._resolve_scalar_type(field, value, expected_type)

        item_type = get_args(expected_type)[0]
        return cls._validate_items(field, value, [item_type] * len(value))

    @classmethod
    def _resolve_tuple_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for tuple[T, ...] and tuple[T1, T2, ...].
        The value must be a tuple or a list.
        A list is converted to a tuple, because JSON has no tuples.
        tuple[T, ...] validates each item against T.
        tuple[T1, T2, ...] requires the exact number of items.

        :returns: Normalized value, validation errors
        """

        if not isinstance(value, tuple | list):
            return cls._resolve_scalar_type(field, value, expected_type)

        args = get_args(expected_type)

        if len(args) == 2 and args[1] is Ellipsis:
            item_types = [args[0]] * len(value)
        elif len(args) == len(value):
            item_types = list(args)
        else:
            return ..., [
                FieldValidationError(
                    field=field,
                    message=f"Expected {_type_repr(expected_type)} with {len(args)} items, got {len(value)}",
                    location=[field],
                )
            ]

        validated_items, errors = cls._validate_items(field, value, item_types)
        if errors:
            return ..., errors

        return tuple(validated_items), []

    @classmethod
    def _resolve_dict_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for dict[K, V].
        The value must be a dict.
        Each key is validated against K and each value against V.
        The key is added to the location of key and value errors.
        Key error messages start with "Invalid key".

        :returns: Normalized value, validation errors
        """

        if not isinstance(value, dict):
            return cls._resolve_scalar_type(field, value, expected_type)

        key_type, value_type = get_args(expected_type)
        validated_dict: dict[Any, Any] = {}
        errors: list[FieldValidationError] = []

        for key, item in value.items():
            location_key = key if isinstance(key, str | int) else repr(key)

            validated_key, key_errors = cls._check_field_type(field, key, key_type)
            for error in key_errors:
                error.message = f"Invalid key: {error.message}"
                error.location.insert(1, location_key)
            errors.extend(key_errors)

            validated_item, item_errors = cls._check_field_type(field, item, value_type)
            for error in item_errors:
                error.location.insert(1, location_key)
            errors.extend(item_errors)

            if not key_errors and not item_errors:
                validated_dict[validated_key] = validated_item

        if errors:
            return ..., errors

        return validated_dict, []

    @classmethod
    def _validate_items(
        cls, field: FieldName, items: list[Any] | tuple[Any, ...], item_types: list[Any]
    ) -> tuple[list[Any], list[FieldValidationError]]:
        """
        Validates items of a sequence against their types.
        The item index is added to the location of item errors.
        A failed item is replaced with ellipsis.

        :returns: Normalized items, validation errors
        """

        validated_items: list[Any] = []
        errors: list[FieldValidationError] = []

        for index, (item, item_type) in enumerate(zip(items, item_types, strict=True)):
            validated_item, item_errors = cls._check_field_type(field, item, item_type)
            for error in item_errors:
                error.location.insert(1, index)
            errors.extend(item_errors)
            validated_items.append(... if item_errors else validated_item)

        return validated_items, errors

    @classmethod
    def _resolve_unsupported_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for annotations without support, such as set and TypedDict.
        Always produces a single error.

        :returns: Normalized value, validation errors
        """

        return ..., [
            FieldValidationError(
                field=field,
                message=f"Unsupported type: {_type_repr(expected_type)}",
                location=[field],
            )
        ]

    @classmethod
    def _resolve_schema_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for nested Schema subclasses.
        An instance of the expected schema is returned unchanged.
        A dict is validated through expected_type.validate.
        The current field is prepended to the location of nested errors.

        :returns: Normalized value, validation errors
        """

        if isinstance(value, expected_type):
            return value, []

        if isinstance(value, dict):
            try:
                return expected_type.validate(value), []
            except ValidationError as exc:
                return ..., [
                    FieldValidationError(
                        field=error.field,
                        message=error.message,
                        location=[field, *error.location],
                    )
                    for error in exc.exceptions
                ]

        return ..., [
            FieldValidationError(
                field=field,
                message=f"Expected dict or {expected_type.__name__}, got {type(value).__name__}",
                location=[field],
            )
        ]

    @classmethod
    def _resolve_scalar_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for a value that does not match a plain class annotation.
        Always produces a single error with the expected and actual types.

        :returns: Normalized value, validation errors
        """

        return ..., [
            FieldValidationError(
                field=field,
                message=f"Expected {_type_repr(expected_type)}, got {type(value).__name__}",
                location=[field],
            )
        ]

    @classmethod
    def _resolve_validators(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | EllipsisType, list[FieldValidationError]]:
        """
        Resolver for Annotated[T, *validators].
        The value is checked against T first.
        Validators run in order, each receives the result of the previous one.

        :returns: Normalized value, validation errors
        """

        base_type, *validators = get_args(expected_type)
        value, errors = cls._check_field_type(field, value, base_type)

        if errors:
            return ..., errors

        validator_errors: list[FieldValidationError] = []
        for validator in validators:
            try:
                value = validator(value)
            except Exception as exc:
                validator_name = getattr(validator, "__name__", type(validator).__name__)
                validator_errors.append(
                    FieldValidationError(
                        field=field,
                        message=f"Validator {validator_name} failed: {exc}",
                        location=[field],
                    )
                )

        if validator_errors:
            return ..., validator_errors

        return value, []
