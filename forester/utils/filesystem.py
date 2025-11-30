"""
Filesystem utilities for Forester.
"""

import shutil
from pathlib import Path
from typing import List
from ..core.ignore import IgnoreRules


def scan_directory(directory: Path, ignore_rules: IgnoreRules,
                   base_path: Path = None) -> List[Path]:
    """
    Scan directory and return list of files (excluding ignored paths).

    Args:
        directory: Directory to scan
        ignore_rules: IgnoreRules instance
        base_path: Base path for relative matching (defaults to directory)

    Returns:
        List of file paths (not directories)
    """
    if base_path is None:
        base_path = directory

    files: List[Path] = []

    if not directory.exists() or not directory.is_dir():
        return files

    try:
        for item in directory.rglob('*'):
            # Skip directories
            if item.is_dir():
                continue

            # Check if should be ignored
            if ignore_rules.should_ignore(item, base_path):
                continue

            files.append(item)
    except PermissionError:
        # Skip directories we can't access
        pass

    return files


def copy_file(src: Path, dst: Path, create_parents: bool = True) -> None:
    """
    Copy file from source to destination.

    Args:
        src: Source file path
        dst: Destination file path
        create_parents: Create parent directories if they don't exist

    Raises:
        FileNotFoundError: If source doesn't exist
        IOError: If copy fails
    """
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")

    if create_parents:
        dst.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(src, dst)


def remove_directory(directory: Path) -> None:
    """
    Remove directory and all its contents.

    Args:
        directory: Directory to remove

    Raises:
        OSError: If removal fails
    """
    if directory.exists() and directory.is_dir():
        shutil.rmtree(directory)
    elif directory.exists():
        directory.unlink()


def ensure_directory(directory: Path) -> None:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        directory: Directory path
    """
    directory.mkdir(parents=True, exist_ok=True)




