from typing import Any

from pydantic import BaseModel
from app.crypto.canonical_json import canonical_json as _canonical_json


def canonical_json(value: BaseModel | dict[str, Any]) -> bytes:
    """Public SDK facade over the authoritative protocol canonicaliser."""
    return _canonical_json(value)


def pretty_json(value: BaseModel | dict[str, Any]) -> str:
    data = (
        value.model_dump(mode="json", exclude_none=True)
        if isinstance(value, BaseModel)
        else value
    )
    import json

    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
