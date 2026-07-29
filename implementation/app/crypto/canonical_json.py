import json
from typing import Any

from pydantic import BaseModel


def canonical_json(value: BaseModel | dict[str, Any]) -> bytes:
    data = (
        value.model_dump(mode="json", exclude_none=True)
        if isinstance(value, BaseModel)
        else value
    )

    def reject_float(item: Any) -> None:
        if isinstance(item, float):
            raise TypeError(
                "Floating-point values are not supported in canonical JSON."
            )
        if isinstance(item, dict):
            for nested in item.values():
                reject_float(nested)
        elif isinstance(item, (list, tuple)):
            for nested in item:
                reject_float(nested)

    reject_float(data)
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonicalise_model(model: BaseModel) -> bytes:
    """Use the single protocol canonicaliser shared by service, SDK and CLI."""
    return canonical_json(model)
