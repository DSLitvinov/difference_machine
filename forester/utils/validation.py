"""
Validation utilities for Forester.
"""

from typing import Tuple, Optional


def validate_branch_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate branch name according to git-like rules.

    Args:
        name: Branch name to validate

    Returns:
        Tuple of (is_valid, error_message)
        If valid: (True, None)
        If invalid: (False, error_message)
    """
    if not name:
        return False, "Branch name cannot be empty"

    if len(name) > 255:
        return False, "Branch name too long (max 255 characters)"

    # Check for forbidden patterns
    forbidden_patterns = ['..', '~', '^', ':', '?', '*', '[', '\\']
    for pattern in forbidden_patterns:
        if pattern in name:
            return False, f"Branch name cannot contain '{pattern}'"

    # Check for leading/trailing dots or spaces
    if name.startswith('.') or name.endswith('.'):
        return False, "Branch name cannot start or end with '.'"

    if name.startswith(' ') or name.endswith(' '):
        return False, "Branch name cannot start or end with space"

    # Check for control characters
    if any(ord(c) < 32 for c in name):
        return False, "Branch name cannot contain control characters"

    return True, None


