"""
Review tools commands for Forester.
Handles comments and approval workflow.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from ..core.database import ForesterDB
from ..core.refs import get_current_branch


def add_comment(repo_path: Path, asset_hash: str, asset_type: str,
                author: str, text: str, x: Optional[float] = None,
                y: Optional[float] = None) -> int:
    """
    Add comment to asset (mesh, blob, commit).

    Args:
        repo_path: Path to repository root
        asset_hash: Hash of the asset
        asset_type: Type ('mesh', 'blob', 'commit')
        author: Author name
        text: Comment text
        x: X coordinate for annotation (optional)
        y: Y coordinate for annotation (optional)

    Returns:
        Comment ID

    Raises:
        ValueError: If repository not initialized
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")

    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        return db.add_comment(asset_hash, asset_type, author, text, x, y)


def get_comments(repo_path: Path, asset_hash: str, asset_type: str,
                 include_resolved: bool = False) -> List[Dict[str, Any]]:
    """
    Get comments for asset.

    Args:
        repo_path: Path to repository root
        asset_hash: Hash of the asset
        asset_type: Type ('mesh', 'blob', 'commit')
        include_resolved: Include resolved comments

    Returns:
        List of comment dictionaries
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return []

    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        return db.get_comments(asset_hash, asset_type, include_resolved)


def resolve_comment(repo_path: Path, comment_id: int) -> bool:
    """Mark comment as resolved."""
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return False

    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        return db.resolve_comment(comment_id)


def delete_comment(repo_path: Path, comment_id: int) -> bool:
    """Delete comment."""
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return False

    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        return db.delete_comment(comment_id)


def set_approval(repo_path: Path, asset_hash: str, asset_type: str,
                 approver: str, status: str, comment: Optional[str] = None) -> bool:
    """
    Set approval status for asset.

    Args:
        repo_path: Path to repository root
        asset_hash: Hash of the asset
        asset_type: Type ('mesh', 'blob', 'commit')
        approver: Approver name
        status: Status ('pending', 'approved', 'rejected')
        comment: Optional comment

    Returns:
        True if successful

    Raises:
        ValueError: If repository not initialized
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")

    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        return db.set_approval(asset_hash, asset_type, approver, status, comment)


def get_approval(repo_path: Path, asset_hash: str, asset_type: str,
                 approver: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get approval status for asset.

    Args:
        repo_path: Path to repository root
        asset_hash: Hash of the asset
        asset_type: Type ('mesh', 'blob', 'commit')
        approver: Filter by approver (optional)

    Returns:
        Approval dictionary or None
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return None

    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        return db.get_approval(asset_hash, asset_type, approver)


def get_all_approvals(repo_path: Path, asset_hash: str, asset_type: str) -> List[Dict[str, Any]]:
    """Get all approvals for asset."""
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return []

    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        return db.get_all_approvals(asset_hash, asset_type)

