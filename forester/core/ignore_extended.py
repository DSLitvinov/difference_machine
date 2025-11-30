"""
Extended ignore rules that exclude meshes/ directory.
Used for commits and stashes where meshes are handled separately.
"""

from pathlib import Path
from .ignore import IgnoreRules


class ExtendedIgnoreRules(IgnoreRules):
    """
    Extended ignore rules that also exclude meshes/ directory.
    Used for commits and stashes where meshes are handled separately.
    """

    def should_ignore(self, path: Path, base_path: Path) -> bool:
        """
        Check if path should be ignored, including meshes/ directory.

        Args:
            path: Path to check
            base_path: Base path of repository

        Returns:
            True if path should be ignored
        """
        # First check standard ignore rules
        if super().should_ignore(path, base_path):
            return True

        # Also ignore meshes/ directory
        try:
            rel_path = (
                path.relative_to(base_path)
                if path.is_absolute() else path
            )
            if str(rel_path).startswith("meshes/"):
                return True
        except ValueError:
            pass

        return False

