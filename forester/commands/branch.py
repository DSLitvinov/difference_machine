"""
Branch command for Forester.
Manages branches: create, list, delete.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from ..core.database import ForesterDB
from ..core.refs import get_branch_ref, set_branch_ref, get_current_branch
from ..models.commit import Commit


def create_branch(repo_path: Path, branch_name: str, 
                  from_branch: Optional[str] = None) -> bool:
    """
    Create a new branch.
    
    Args:
        repo_path: Path to repository root
        branch_name: Name of the new branch
        from_branch: Branch to copy from (None = current branch)
        
    Returns:
        True if successful
        
    Raises:
        ValueError: If branch already exists or invalid name
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")
    
    # Check if branch already exists
    ref_file = dfm_dir / "refs" / "branches" / branch_name
    if ref_file.exists():
        raise ValueError(f"Branch '{branch_name}' already exists")
    
    # Validate branch name (basic validation)
    if not branch_name or '/' in branch_name or '\\' in branch_name:
        raise ValueError(f"Invalid branch name: {branch_name}")
    
    # Get source branch commit
    if from_branch:
        source_commit = get_branch_ref(repo_path, from_branch)
        if source_commit is None:
            raise ValueError(f"Source branch '{from_branch}' has no commits")
    else:
        # Use current branch
        current_branch = get_current_branch(repo_path)
        if current_branch:
            source_commit = get_branch_ref(repo_path, current_branch)
        else:
            source_commit = None
    
    # Create branch reference
    set_branch_ref(repo_path, branch_name, source_commit)
    
    return True


def list_branches(repo_path: Path) -> List[Dict[str, Any]]:
    """
    List all branches.
    
    Args:
        repo_path: Path to repository root
        
    Returns:
        List of branch information dictionaries
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return []
    
    branches_dir = dfm_dir / "refs" / "branches"
    if not branches_dir.exists():
        return []
    
    # Get current branch
    current_branch = get_current_branch(repo_path)
    
    branches = []
    
    # Iterate through branch reference files
    for ref_file in branches_dir.iterdir():
        if not ref_file.is_file():
            continue
        
        branch_name = ref_file.name
        
        # Read commit hash
        with open(ref_file, 'r', encoding='utf-8') as f:
            commit_hash = f.read().strip()
        
        # Get commit info if exists
        commit_info = None
        if commit_hash:
            db_path = dfm_dir / "forester.db"
            with ForesterDB(db_path) as db:
                commit_data = db.get_commit(commit_hash)
                if commit_data:
                    commit_info = {
                        "hash": commit_data['hash'],
                        "message": commit_data.get('message', ''),
                        "timestamp": commit_data['timestamp'],
                        "author": commit_data.get('author', '')
                    }
        
        branches.append({
            "name": branch_name,
            "current": branch_name == current_branch,
            "commit_hash": commit_hash if commit_hash else None,
            "commit": commit_info
        })
    
    # Sort by name
    branches.sort(key=lambda b: b['name'])
    
    return branches


def delete_branch(repo_path: Path, branch_name: str, force: bool = False) -> bool:
    """
    Delete a branch.
    
    Args:
        repo_path: Path to repository root
        branch_name: Name of branch to delete
        force: If True, delete even if it's the current branch
        
    Returns:
        True if successful
        
    Raises:
        ValueError: If branch doesn't exist or is current branch (and force=False)
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")
    
    # Check if branch exists
    ref_file = dfm_dir / "refs" / "branches" / branch_name
    if not ref_file.exists():
        raise ValueError(f"Branch '{branch_name}' does not exist")
    
    # Check if it's the current branch
    current_branch = get_current_branch(repo_path)
    if branch_name == current_branch and not force:
        raise ValueError(f"Cannot delete current branch '{branch_name}'. Use force=True or switch branch first.")
    
    # Get all commits in branch
    branch_commit = get_branch_ref(repo_path, branch_name)
    
    # Delete branch reference file
    ref_file.unlink()
    
    # Note: We don't delete commits here - they may be referenced by other branches
    # Commit deletion is handled separately (see delete_commit command)
    
    return True


def get_branch_commits(repo_path: Path, branch_name: str) -> List[Dict[str, Any]]:
    """
    Get all commits in a branch.
    
    Args:
        repo_path: Path to repository root
        branch_name: Name of branch
        
    Returns:
        List of commit dictionaries, ordered from oldest to newest
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return []
    
    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        commits = db.get_commits_by_branch(branch_name)
        return [dict(c) for c in commits]


def switch_branch(repo_path: Path, branch_name: str) -> bool:
    """
    Switch to a different branch (without checkout).
    This only updates database, doesn't change working directory.
    
    Args:
        repo_path: Path to repository root
        branch_name: Name of branch to switch to
        
    Returns:
        True if successful
        
    Raises:
        ValueError: If branch doesn't exist
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")
    
    # Check if branch exists
    ref_file = dfm_dir / "refs" / "branches" / branch_name
    if not ref_file.exists():
        raise ValueError(f"Branch '{branch_name}' does not exist")
    
    # Update database
    db_path = dfm_dir / "forester.db"
    if not db_path.exists():
        raise ValueError(f"Database not found at {db_path}")
    
    from ..core.database import ForesterDB
    
    # Get branch commit hash
    branch_commit = get_branch_ref(repo_path, branch_name)
    
    with ForesterDB(db_path) as db:
        db.set_branch_and_head(branch_name, branch_commit)
    
    return True




