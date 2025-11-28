"""
Commit utility functions for Forester.
Provides common logic for checking commit usage by branches.
"""

from pathlib import Path
from typing import Set, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.database import ForesterDB


def get_all_commits_used_by_branches(
    repo_path: Path,
    db: 'ForesterDB',
    exclude_branch: Optional[str] = None
) -> Set[str]:
    """
    Get all commits that are used by branches (including parent chains).
    
    This function traces parent chains from all branch references to find
    all commits that are reachable from any branch.
    
    Args:
        repo_path: Path to repository root
        db: Database connection
        exclude_branch: Branch name to exclude from check (optional)
        
    Returns:
        Set of commit hashes used by branches
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return set()
    
    # Get all branch references (excluding specified branch if provided)
    branches_dir = dfm_dir / "refs" / "branches"
    branch_refs = set()
    
    if branches_dir.exists():
        for ref_file in branches_dir.iterdir():
            if ref_file.is_file():
                branch_name = ref_file.name
                if exclude_branch and branch_name == exclude_branch:
                    continue
                    
                with open(ref_file, 'r', encoding='utf-8') as f:
                    commit_hash = f.read().strip()
                    if commit_hash:
                        branch_refs.add(commit_hash)
    
    # Also check HEAD commit
    head_commit = db.get_head()
    if head_commit:
        branch_refs.add(head_commit)
    
    # Get all commits that are referenced by branches (through parent chains)
    commits_used_by_branches = set()
    
    def trace_parent_chain(commit_hash: str, visited: Set[str]) -> None:
        """Recursively trace parent chain to find all commits."""
        if not commit_hash or commit_hash in visited:
            return
        visited.add(commit_hash)
        commits_used_by_branches.add(commit_hash)
        
        commit_info = db.get_commit(commit_hash)
        if commit_info and commit_info.get('parent_hash'):
            trace_parent_chain(commit_info['parent_hash'], visited)
    
    # Trace parent chains from all branch refs
    for ref_commit in branch_refs:
        trace_parent_chain(ref_commit, set())
    
    return commits_used_by_branches


def is_commit_referenced_by_branches(
    repo_path: Path,
    commit_hash: str,
    db: 'ForesterDB',
    exclude_branch: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if commit is directly referenced by any branch (as HEAD commit).
    
    This checks only direct references, not parent chains.
    For full check including parent chains, use get_all_commits_used_by_branches.
    
    Args:
        repo_path: Path to repository root
        commit_hash: Commit hash to check
        db: Database connection
        exclude_branch: Branch name to exclude from check (optional)
        
    Returns:
        Tuple of (is_referenced, branch_name)
        branch_name is None if not referenced or if exclude_branch matches
    """
    from ..core.refs import get_branch_ref, get_current_branch
    
    # Check HEAD commit
    head_commit = db.get_head()
    if head_commit == commit_hash:
        current_branch = get_current_branch(repo_path)
        if not exclude_branch or current_branch != exclude_branch:
            return True, current_branch
    
    # Check all branch references
    dfm_dir = repo_path / ".DFM"
    branches_dir = dfm_dir / "refs" / "branches"
    
    if branches_dir.exists():
        for ref_file in branches_dir.iterdir():
            if ref_file.is_file():
                branch_name = ref_file.name
                if exclude_branch and branch_name == exclude_branch:
                    continue
                
                branch_ref = get_branch_ref(repo_path, branch_name)
                if branch_ref == commit_hash:
                    return True, branch_name
    
    return False, None


def is_commit_head(
    repo_path: Path,
    commit_hash: str,
    db: 'ForesterDB'
) -> Tuple[bool, Optional[str]]:
    """
    Check if commit is the HEAD commit of current branch.
    
    Args:
        repo_path: Path to repository root
        commit_hash: Commit hash to check
        db: Database connection
        
    Returns:
        Tuple of (is_head, branch_name)
    """
    from ..core.refs import get_branch_ref, get_current_branch
    
    current_branch = get_current_branch(repo_path)
    if not current_branch:
        return False, None
    
    branch_ref = get_branch_ref(repo_path, current_branch)
    head_commit = db.get_head()
    
    if (branch_ref == commit_hash or head_commit == commit_hash):
        return True, current_branch
    
    return False, None

