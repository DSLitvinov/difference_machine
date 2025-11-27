"""
Reference management for Forester.
Handles branch references.
"""

from pathlib import Path
from typing import Optional


def get_branch_ref(repo_path: Path, branch: str) -> Optional[str]:
    """
    Get commit hash for a branch.
    
    Args:
        repo_path: Path to repository root
        branch: Branch name
        
    Returns:
        Commit hash or None if branch doesn't exist or has no commits
    """
    ref_file = repo_path / ".DFM" / "refs" / "branches" / branch
    
    if not ref_file.exists():
        return None
    
    with open(ref_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    return content if content else None


def set_branch_ref(repo_path: Path, branch: str, commit_hash: Optional[str]) -> None:
    """
    Set commit hash for a branch.
    
    Args:
        repo_path: Path to repository root
        branch: Branch name
        commit_hash: Commit hash (None to clear)
    """
    ref_file = repo_path / ".DFM" / "refs" / "branches" / branch
    
    # Ensure directory exists
    ref_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(ref_file, 'w', encoding='utf-8') as f:
        if commit_hash:
            f.write(commit_hash)
        else:
            f.write("")  # Empty file means no commit


def get_current_branch(repo_path: Path) -> Optional[str]:
    """
    Get current branch name from metadata.
    
    Args:
        repo_path: Path to repository root
        
    Returns:
        Branch name or None
    """
    from .metadata import Metadata
    
    metadata_path = repo_path / ".DFM" / "metadata.json"
    if not metadata_path.exists():
        return None
    
    metadata = Metadata(metadata_path)
    metadata.load()
    return metadata.current_branch


def get_current_head_commit(repo_path: Path) -> Optional[str]:
    """
    Get current HEAD commit hash.
    
    Args:
        repo_path: Path to repository root
        
    Returns:
        Commit hash or None
    """
    branch = get_current_branch(repo_path)
    if not branch:
        return None
    
    # First try to get from branch ref
    commit_hash = get_branch_ref(repo_path, branch)
    if commit_hash:
        return commit_hash
    
    # Fallback to metadata.head if branch ref is empty
    from .metadata import Metadata
    metadata_path = repo_path / ".DFM" / "metadata.json"
    if metadata_path.exists():
        try:
            metadata = Metadata(metadata_path)
            metadata.load()
            return metadata.head
        except Exception:
            # If metadata can't be loaded, return None
            pass
    
    return None




