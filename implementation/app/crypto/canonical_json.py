import json
from typing import Any

from pydantic import BaseModel


def canonicalise_model(model: BaseModel) -> bytes:
    """
    Serialize a Pydantic model into deterministic UTF-8 JSON bytes.

    Current experimental rules:

    1. Fields are serialized using JSON-compatible values.
    2. Object keys are sorted alphabetically.
    3. Insignificant whitespace is removed.
    4. Unicode characters are serialized directly.
    5. The result is encoded using UTF-8.

    This is an experimental canonical format and may later be replaced by
    RFC 8785 JSON Canonicalization Scheme.
    """

    data: Any = model.model_dump(
        mode="json",
        exclude_none=True,
    )

    canonical_json = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return canonical_json.encode("utf-8")
