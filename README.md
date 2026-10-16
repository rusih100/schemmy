# schemmy

Data validation and normalization driven by type annotations. Zero dependencies, one base class, no magic.

```bash
pip install schemmy
# or
uv add schemmy
```

Requires Python 3.12+.

## Example

```python
from typing import Annotated

from schemmy import Schema, ValidationError


def positive(value: int) -> int:
    if value <= 0:
        raise ValueError("must be greater than zero")
    return value


class Item(Schema):
    sku: str
    qty: Annotated[int, positive]


class Order(Schema):
    id: int
    items: list[Item]


order = Order.validate({"id": 1, "items": [{"sku": "A1", "qty": 2}]})
order.items[0].qty  # 2
```

All errors are collected at once, not just the first one. Each error carries the path to the field:

```python
try:
    Order.validate({"id": "1", "items": [{"sku": "A1", "qty": 0}, {"qty": 3}], "note": "x"})
except ValidationError as exc:
    for error in exc.exceptions:
        print(error.location, error.message)
```

```text
['note'] Unknown field
['id'] Expected int, got str
['items', 0, 'qty'] Validator positive failed: must be greater than zero
['items', 1, 'sku'] Field required
```

Errors come in a stable order: missing and unknown fields first, then value errors in field declaration order.

`ValidationError` is an `ExceptionGroup`, so `except*` works too.

## What is supported

| Annotation | Behavior |
|---|---|
| `int`, `str`, `float`, `bool`, any class | `isinstance` check, no type coercion. `bool` is rejected for `int` fields |
| `Any` | Value is accepted as is |
| `list[T]` | Each item is checked against `T`; the item index is added to the error path |
| `tuple[T, ...]`, `tuple[T1, T2]` | Accepts a tuple or a list and stores a tuple, since JSON has no tuples. A fixed tuple requires the exact length |
| `dict[K, V]` | Each key is checked against `K` and each value against `V`; the key is added to the error path |
| `Literal[...]` | The value must equal one of the literals and have the same type, so `True` does not match `Literal[1]` |
| `X \| Y`, `Optional[X]` | Members are tried in order, the first match wins. For `X \| None`, errors of `X` are reported as is |
| `Schema` subclass | Accepts a schema instance or a `dict` |
| `Annotated[T, *validators]` | `T` is checked first, then validators run in order |

A validator is a callable that takes a value and returns it, possibly changed. To report an error, a validator raises an exception. The returned value is stored in the schema, so validators can normalize data, for example bring a phone number to a single format.

Unknown fields and missing required fields are validation errors as well.

A field with a default value is optional. If the field is not passed, the schema gets a copy of the default. The default value itself is not validated.

`ClassVar` annotations are not fields.

## Working with instances

```python
order.to_dict()
# {'id': 1, 'items': [{'sku': 'A1', 'qty': 2}]}

order
# Order(id=1, items=[Item(sku='A1', qty=2)])

Order.validate(order.to_dict()) == order
# True
```

`to_dict` converts nested schemas recursively and keeps field declaration order. Schemas compare by class and field values. Schemas are mutable and therefore unhashable.

## Type checking

Type checkers derive the constructor signature from the annotations, so wrong types, unknown and missing fields are reported before runtime:

```python
Item(sku=1, qty=2)  # error: expected str
Item(sku="A1", qyt=2)  # error: unknown argument
```

The constructor is typed for already typed values. Use `Schema.validate` for raw data such as parsed JSON, where nested schemas arrive as dicts.

## Limitations

`set`, `frozenset`, `TypedDict` and other annotations not listed above are not supported yet. A field with such an annotation produces an "unsupported type" error.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run ty check
```

## License

MIT
