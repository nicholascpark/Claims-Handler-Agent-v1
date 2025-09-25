"""Schema accessor and safe field utilities for claims data.

This module centralizes access to schema field names and provides
helpers to set/get fields by (possibly nested) paths while emitting
field-level update notifications without leaking values.
"""

from typing import Any, Callable, Dict, Iterable, List, Optional

try:
    # Pydantic v2
    from pydantic import BaseModel  # type: ignore
except Exception:  # pragma: no cover
    BaseModel = object  # type: ignore


def _collect_model_field_names(model_cls: Any) -> List[str]:
    """Return list of field names for a Pydantic model (v1 or v2)."""
    # pydantic v2
    if hasattr(model_cls, "model_fields"):
        return list(getattr(model_cls, "model_fields").keys())
    # pydantic v1
    if hasattr(model_cls, "__fields__"):
        return list(getattr(model_cls, "__fields__").keys())
    # Fallback: best-effort dir scan (shouldn't happen in normal use)
    return [k for k in dir(model_cls) if not k.startswith("_")]


def _collect_required_field_names(model_cls: Any) -> List[str]:
    """Derive required field names from a Pydantic model (v1 or v2).

    Required means: not Optional and has no default value.
    """
    required: List[str] = []
    # pydantic v2
    if hasattr(model_cls, "model_fields"):
        for name, field in model_cls.model_fields.items():  # type: ignore[attr-defined]
            if getattr(field, "is_required", False):
                required.append(name)
        return required
    # pydantic v1
    if hasattr(model_cls, "__fields__"):
        for name, field in model_cls.__fields__.items():  # type: ignore[attr-defined]
            if getattr(field, "required", False):
                required.append(name)
        return required
    return required


class _FieldNames:
    """Dynamic accessor for field names.

    Example: F.incident_date -> "incident_date" if present in the model.
    """

    def __init__(self, valid_fields: Iterable[str]):
        self._valid_fields = set(valid_fields)

    def __getattr__(self, attr: str) -> str:
        if attr in self._valid_fields:
            return attr
        raise AttributeError(f"Field '{attr}' is not defined in the schema.")

    def has(self, name: str) -> bool:
        return name in self._valid_fields

    def all(self) -> List[str]:
        return sorted(self._valid_fields)


class ClaimSchemaAccessor:
    """Introspection and helpers for claims schema models."""

    def __init__(self, model_cls: Any):
        self.model_cls = model_cls
        self._all_fields = _collect_model_field_names(model_cls)
        self._required_fields = _collect_required_field_names(model_cls)
        self.field_names = _FieldNames(self._all_fields)

    def all_fields(self) -> List[str]:
        return list(self._all_fields)

    def required_fields(self) -> List[str]:
        return list(self._required_fields)


def _ensure_container_for_path(root: Dict[str, Any], parts: List[str]) -> Dict[str, Any]:
    """Ensure intermediate dicts exist for a dotted path except for the last key."""
    node = root
    for key in parts[:-1]:
        if key not in node or not isinstance(node[key], dict):
            node[key] = {}
        node = node[key]
    return node


def set_claim_field(
    claim_data: Dict[str, Any],
    field_path: str,
    value: Any,
    on_field_updated: Optional[Callable[[str], None]] = None,
) -> None:
    """Set a (possibly nested) field on claim_data and notify via callback.

    field_path supports dotted notation for nested updates, e.g. "incident.location.city".
    Only the field path is reported to the callback, never the value.
    """
    parts = field_path.split(".") if "." in field_path else [field_path]
    parent = _ensure_container_for_path(claim_data, parts)
    parent[parts[-1]] = value
    if on_field_updated:
        try:
            on_field_updated(field_path)
        except Exception:
            # Do not let logging failures affect business logic
            pass


def get_claim_field(claim_data: Dict[str, Any], field_path: str, default: Any = None) -> Any:
    """Get a (possibly nested) field value from claim_data using dotted path."""
    node: Any = claim_data
    for key in field_path.split("."):
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


# Convenience: initialize accessor bound to the current simplified schema
try:
    from src.schema.simplified_payload import SimplifiedClaim  # local import to avoid cycles
    accessor = ClaimSchemaAccessor(SimplifiedClaim)
    F = accessor.field_names  # Field name accessor
except Exception:  # pragma: no cover
    accessor = None  # type: ignore
    F = _FieldNames([])  # type: ignore


