"""
Metadata management for Forester repository.
Handles metadata.json file operations.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import time


class Metadata:
    """
    Manages repository metadata stored in metadata.json.
    """

    def __init__(self, metadata_path: Path):
        """
        Initialize metadata manager.

        Args:
            metadata_path: Path to metadata.json file
        """
        self.metadata_path = metadata_path
        self._data: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """
        Load metadata from file.

        Returns:
            Metadata dictionary

        Raises:
            FileNotFoundError: If metadata file doesn't exist
        """
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_path}")

        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            self._data = json.load(f)

        return self._data

    def save(self) -> None:
        """
        Save metadata to file.

        Raises:
            ValueError: If data is not initialized
        """
        if self._data is None:
            raise ValueError("Metadata not loaded. Call load() or initialize() first.")

        # Ensure parent directory exists
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def initialize(self, current_branch: str = "main", head: Optional[str] = None) -> None:
        """
        Initialize metadata with default values.

        Args:
            current_branch: Name of the current branch (default: "main")
            head: HEAD commit hash (default: None)
        """
        self._data = {
            "version": "1.0",
            "created_at": int(time.time()),
            "current_branch": current_branch,
            "head": head
        }
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value by key.

        Args:
            key: Metadata key
            default: Default value if key doesn't exist

        Returns:
            Metadata value or default
        """
        if self._data is None:
            self.load()

        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set metadata value.

        Args:
            key: Metadata key
            value: Value to set
        """
        if self._data is None:
            if self.metadata_path.exists():
                self.load()
            else:
                self.initialize()

        self._data[key] = value
        self.save()

    @property
    def current_branch(self) -> str:
        """Get current branch name."""
        return self.get("current_branch", "main")

    @current_branch.setter
    def current_branch(self, value: str) -> None:
        """Set current branch name."""
        self.set("current_branch", value)

    @property
    def head(self) -> Optional[str]:
        """Get HEAD commit hash."""
        return self.get("head")

    @head.setter
    def head(self, value: Optional[str]) -> None:
        """Set HEAD commit hash."""
        self.set("head", value)

    def exists(self) -> bool:
        """Check if metadata file exists."""
        return self.metadata_path.exists()




