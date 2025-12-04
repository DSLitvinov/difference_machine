"""
Tag command for Forester.
Manages tags: create, list, delete, show.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..core.database import ForesterDB
from ..core.refs import get_current_head_commit

logger = logging.getLogger(__name__)


def create_tag(repo_path: Path, tag_name: str, commit_hash: Optional[str] = None) -> bool:
    """
    Create a tag for a commit.

    Args:
        repo_path: Path to repository root
        tag_name: Name of the tag
        commit_hash: Commit hash to tag (None = current HEAD)

    Returns:
        True if successful

    Raises:
        ValueError: If tag already exists, commit not found, or invalid tag name
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")

    # Validate tag name
    if not tag_name or not tag_name.strip():
        raise ValueError("Tag name cannot be empty")
    
    # Check for invalid characters (basic validation)
    invalid_chars = [' ', '\t', '\n', '\r', '~', '^', ':', '?', '*', '[', '\\']
    if any(char in tag_name for char in invalid_chars):
        raise ValueError(f"Invalid tag name: {tag_name}. Contains invalid characters.")

    # Get commit hash
    if not commit_hash:
        commit_hash = get_current_head_commit(repo_path)
        if not commit_hash:
            raise ValueError("No commit to tag. Repository has no commits.")

    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        # Check if commit exists
        commit_data = db.get_commit(commit_hash)
        if not commit_data:
            raise ValueError(f"Commit {commit_hash} not found")

        # Check if tag already exists
        existing_commit = db.get_commit_by_tag(tag_name)
        if existing_commit:
            raise ValueError(f"Tag '{tag_name}' already exists on commit {existing_commit['hash'][:16]}...")

        # Set tag on commit
        db.set_commit_tag(commit_hash, tag_name)

    return True


def delete_tag(repo_path: Path, tag_name: str) -> bool:
    """
    Delete a tag.

    Args:
        repo_path: Path to repository root
        tag_name: Name of the tag to delete

    Returns:
        True if successful

    Raises:
        ValueError: If tag doesn't exist
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")

    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        # Check if tag exists
        commit_data = db.get_commit_by_tag(tag_name)
        if not commit_data:
            raise ValueError(f"Tag '{tag_name}' does not exist")

        # Remove tag
        db.set_commit_tag(commit_data['hash'], None)

    return True


def list_tags(repo_path: Path) -> List[Dict[str, Any]]:
    """
    List all tags.

    Args:
        repo_path: Path to repository root

    Returns:
        List of tag information dictionaries
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return []

    db_path = dfm_dir / "forester.db"
    if not db_path.exists():
        return []

    with ForesterDB(db_path) as db:
        tags = db.list_tags()
        return tags


def show_tag(repo_path: Path, tag_name: str) -> Optional[Dict[str, Any]]:
    """
    Show information about a tag.

    Args:
        repo_path: Path to repository root
        tag_name: Name of the tag

    Returns:
        Tag information dictionary or None if tag doesn't exist
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return None

    db_path = dfm_dir / "forester.db"
    if not db_path.exists():
        return None

    with ForesterDB(db_path) as db:
        commit_data = db.get_commit_by_tag(tag_name)
        if not commit_data:
            return None

        return {
            'tag': tag_name,
            'commit_hash': commit_data['hash'],
            'author': commit_data.get('author', 'Unknown'),
            'message': commit_data.get('message', ''),
            'timestamp': commit_data.get('timestamp', 0),
            'branch': commit_data.get('branch', 'main'),
            'commit_type': commit_data.get('commit_type', 'project'),
        }



