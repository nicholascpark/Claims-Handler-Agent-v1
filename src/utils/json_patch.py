"""Lightweight JSON Patch utilities with optional Trustcall integration.

This module provides a minimal JSON patch application capability for updating
deeply nested claim data maps. It supports a subset of RFC 6902 operations
(add, replace, remove) using either JSON Pointer paths ("/a/b/0") or dotted
paths ("a.b.0"). When available, it can optionally delegate to Trustcall for
more robust and inexpensive patching on complex structures.
"""

from typing import Any, Callable, Dict, List, Optional


def _split_path(path: str) -> List[str]:
    """Split a path expressed as JSON Pointer or dotted notation into parts."""
    if not path:
        return []
    if path.startswith("/"):
        # JSON Pointer: unescape ~1 -> /, ~0 -> ~
        parts = [p.replace("~1", "/").replace("~0", "~") for p in path.split("/") if p != ""]
        return parts
    return path.split(".")


def _navigate(container: Any, parts: List[str]) -> (Any, str):
    """Navigate to parent container for the final part, return (parent, last_key)."""
    if not parts:
        raise ValueError("Path cannot be empty")
    node = container
    for key in parts[:-1]:
        idx = None
        if isinstance(node, list):
            try:
                idx = int(key)
            except ValueError:
                raise KeyError(f"List index expected, got '{key}'")
            if idx < 0 or idx >= len(node):
                raise IndexError(f"List index out of range: {idx}")
            node = node[idx]
        else:
            if key not in node or not isinstance(node[key], (dict, list)):
                # Create missing dict nodes
                node[key] = {}
            node = node[key]
    return node, parts[-1]


def _set_value(parent: Any, key: str, value: Any) -> None:
    if isinstance(parent, list):
        idx = int(key)
        if idx == len(parent):
            parent.append(value)
        else:
            parent[idx] = value
    else:
        parent[key] = value


def _add_value(parent: Any, key: str, value: Any) -> None:
    if isinstance(parent, list):
        if key == "-":
            parent.append(value)
            return
        idx = int(key)
        parent.insert(idx, value)
    else:
        if key in parent:
            # Align with RFC 6902: add replaces if key exists? RFC says add allows creating new member
            # but many implementations also allow replacing. We'll treat as set.
            parent[key] = value
        else:
            parent[key] = value


def _remove_value(parent: Any, key: str) -> None:
    if isinstance(parent, list):
        idx = int(key)
        del parent[idx]
    else:
        if key in parent:
            del parent[key]


def apply_json_patch(
    target: Dict[str, Any],
    patch_ops: List[Dict[str, Any]],
    on_field_updated: Optional[Callable[[str], None]] = None,
    prefer_trustcall: bool = True,
) -> Dict[str, Any]:
    """Apply a list of JSON patch operations to target in-place and return it.

    Each operation is a dict like {"op": "replace", "path": "/a/b", "value": 1}.
    Supported ops: add, replace, remove. Paths can be JSON Pointer or dotted.
    If Trustcall is installed and prefer_trustcall=True, we will attempt to use
    it; on failure or absence, fallback to the lightweight implementation.
    """

    if prefer_trustcall:
        try:
            # Best-effort import. The exact API may differ; we guard safely.
            import trustcall  # type: ignore

            if hasattr(trustcall, "apply_patch"):
                updated = trustcall.apply_patch(target, patch_ops)  # type: ignore[attr-defined]
                # Fire callbacks for each op path
                if on_field_updated:
                    for op in patch_ops:
                        path = op.get("path") or op.get("field") or ""
                        if path:
                            try:
                                on_field_updated(path if path.startswith("/") else path.replace(".", "/"))
                            except Exception:
                                pass
                return updated
        except Exception:
            # Fall back to internal implementation silently
            pass

    # Internal minimal patcher
    for op in patch_ops:
        operation = op.get("op")
        path = op.get("path") or op.get("field")
        if not operation or not path:
            raise ValueError(f"Invalid patch operation: {op}")

        parts = _split_path(path)
        parent, last = _navigate(target, parts)

        if operation == "replace":
            _set_value(parent, last, op.get("value"))
        elif operation == "add":
            _add_value(parent, last, op.get("value"))
        elif operation == "remove":
            _remove_value(parent, last)
        else:
            raise ValueError(f"Unsupported op: {operation}")

        if on_field_updated:
            try:
                on_field_updated(path)
            except Exception:
                pass

    return target


