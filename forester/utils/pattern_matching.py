"""
Pattern matching utilities for selective checkout.
"""

import fnmatch
from typing import List, Optional


def match_patterns(path: str, patterns: Optional[List[str]]) -> bool:
    """
    Check if path matches any of the patterns.

    Args:
        path: File path to check
        patterns: List of glob patterns (e.g., ["*.json", "textures/*"])

    Returns:
        True if path matches any pattern, False otherwise
        If patterns is None or empty, returns True (matches all)
    """
    if not patterns:
        return True

    if not isinstance(path, str) or not path:
        return False

    path_normalized = path.replace("\\", "/")

    for pattern in patterns:
        # Convert pattern to normalized form
        pattern_normalized = pattern.replace("\\", "/")

        # Check if path matches pattern
        if fnmatch.fnmatch(path_normalized, pattern_normalized):
            return True

        # Also check if pattern matches as prefix
        if pattern_normalized.endswith("/") and path_normalized.startswith(pattern_normalized):
            return True
        if path_normalized.startswith(pattern_normalized.rstrip("/")):
            return True

    return False

