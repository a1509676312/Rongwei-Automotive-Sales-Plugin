"""JSON Schema compatibility helpers for model tool-calling APIs.

Several tool-call providers accept a JSON Schema subset. Pydantic may emit local
$defs/$ref structures; inline those references for simpler provider interoperability.
The source Pydantic models remain the validation authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel


def inline_local_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON Schema with local #/$defs references expanded recursively."""
    definitions = deepcopy(schema.get("$defs", {}))

    def expand(node: Any, stack: tuple[str, ...] = ()) -> Any:
        if isinstance(node, list):
            return [expand(item, stack) for item in node]
        if not isinstance(node, dict):
            return node

        if "$ref" in node:
            ref = node["$ref"]
            prefix = "#/$defs/"
            if not isinstance(ref, str) or not ref.startswith(prefix):
                raise ValueError(f"Unsupported external or non-local JSON Schema reference: {ref}")
            name = ref[len(prefix):].replace("~1", "/").replace("~0", "~")
            if name not in definitions:
                raise ValueError(f"Unresolved JSON Schema definition: {name}")
            if name in stack:
                raise ValueError(f"Recursive JSON Schema reference is not supported: {name}")
            resolved = expand(deepcopy(definitions[name]), (*stack, name))
            siblings = {key: value for key, value in node.items() if key != "$ref"}
            if siblings:
                if not isinstance(resolved, dict):
                    raise ValueError(f"Cannot merge JSON Schema reference siblings for {name}")
                resolved.update(expand(siblings, stack))
            return resolved

        return {
            key: expand(value, stack)
            for key, value in node.items()
            if key not in {"$defs", "$schema", "title"}
        }

    expanded = expand({key: value for key, value in schema.items() if key != "$defs"})
    if not isinstance(expanded, dict):
        raise ValueError("A tool parameter schema must be a JSON object schema.")
    expanded.setdefault("type", "object")
    expanded.setdefault("additionalProperties", False)
    return expanded


def tool_parameters_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Build a flattened JSON Schema suitable for provider function/tool parameters."""
    return inline_local_refs(model.model_json_schema(mode="validation"))
