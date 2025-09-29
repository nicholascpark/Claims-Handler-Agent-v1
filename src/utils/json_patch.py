"""Trustcall-only JSON Patch utilities for Claims Handler Agent v1

This module provides ONLY trustcall-based JSON patch operations with no fallbacks.
All JSON extraction and patching operations must use trustcall for consistency
and to leverage its inexpensive update capabilities.

Based on: https://github.com/hinthornw/trustcall/blob/main/README.md
"""

from typing import Any, Callable, Dict, List, Optional

try:
    import trustcall
except ImportError:
    trustcall = None


class TrustcallNotAvailableError(Exception):
    """Raised when trustcall is not available but is required"""
    pass


def apply_json_patch(
    target: Dict[str, Any],
    patch_ops: List[Dict[str, Any]],
    on_field_updated: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Apply a list of JSON patch operations to target using ONLY trustcall.

    Each operation is a dict like {"op": "replace", "path": "/a/b", "value": 1}.
    Supported ops: add, replace, remove. Paths must be JSON Pointer format.
    
    This function REQUIRES trustcall to be installed and will raise an error
    if trustcall is not available. No fallback methods are provided.
    
    Args:
        target: The dictionary to apply patches to
        patch_ops: List of RFC 6902 JSON patch operations
        on_field_updated: Optional callback for field update notifications
        
    Returns:
        The updated dictionary
        
    Raises:
        TrustcallNotAvailableError: If trustcall is not available
        ValueError: If patch operations are malformed
    """
    if trustcall is None:
        raise TrustcallNotAvailableError(
            "trustcall is required but not available. Install with: pip install trustcall"
        )
    
    # Validate patch operations format
    for op in patch_ops:
        if not isinstance(op, dict):
            raise ValueError(f"Invalid patch operation format: {op}")
        
        if "op" not in op:
            raise ValueError(f"Missing 'op' field in patch operation: {op}")
        
        if op["op"] not in ["add", "replace", "remove"]:
            raise ValueError(f"Unsupported operation: {op['op']}")
        
        if "path" not in op and "field" not in op:
            raise ValueError(f"Missing 'path' field in patch operation: {op}")

    try:
        # Use trustcall's apply_patch function if available
        if hasattr(trustcall, "apply_patch"):
            updated = trustcall.apply_patch(target, patch_ops)
            
            # Fire callbacks for each operation path
            if on_field_updated:
                for op in patch_ops:
                    path = op.get("path") or op.get("field") or ""
                    if path:
                        try:
                            # Normalize path format for callback
                            normalized_path = path if path.startswith("/") else f"/{path.replace('.', '/')}"
                            on_field_updated(normalized_path)
                        except Exception:
                            # Don't let callback errors break the patching process
                            pass
            
            return updated
        else:
            raise TrustcallNotAvailableError(
                "trustcall.apply_patch function not found. Please update trustcall to latest version."
            )
            
    except Exception as e:
        if isinstance(e, TrustcallNotAvailableError):
            raise
        else:
            raise RuntimeError(f"Trustcall patch operation failed: {str(e)}")


def validate_trustcall_availability() -> bool:
    """
    Validate that trustcall is available and properly configured.
    
    Returns:
        True if trustcall is available, False otherwise
    """
    return trustcall is not None and hasattr(trustcall, "apply_patch")


