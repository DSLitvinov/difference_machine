"""
Delete commit command for Forester.
"""

from pathlib import Path
from typing import Tuple, Optional, Set
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage
from ..core.refs import get_branch_ref, set_branch_ref, get_current_branch

# Export helper functions for use in other modules (e.g., branch.py)
__all__ = [
    'delete_commit',
    'is_commit_head',
    'is_commit_referenced_by_branches',
    'get_all_commits_used_by_branches',
]


def is_commit_head(repo_path: Path, commit_hash: str, db: ForesterDB) -> Tuple[bool, Optional[str]]:
    """
    Check if commit is the HEAD commit of current branch.
    
    Args:
        repo_path: Path to repository root
        commit_hash: Commit hash to check
        db: Database connection
        
    Returns:
        Tuple of (is_head, branch_name)
    """
    current_branch = get_current_branch(repo_path)
    if not current_branch:
        return False, None
    
    branch_ref = get_branch_ref(repo_path, current_branch)
    head_commit = db.get_head()
    
    if (branch_ref == commit_hash or head_commit == commit_hash):
        return True, current_branch
    
    return False, None


def is_commit_referenced_by_branches(
    repo_path: Path,
    commit_hash: str,
    db: ForesterDB,
    exclude_branch: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if commit is directly referenced by any branch (as HEAD commit).
    
    This checks only direct references, not parent chains.
    
    Args:
        repo_path: Path to repository root
        commit_hash: Commit hash to check
        db: Database connection
        exclude_branch: Branch name to exclude from check (optional)
        
    Returns:
        Tuple of (is_referenced, branch_name)
        branch_name is None if not referenced or if exclude_branch matches
    """
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


def get_all_commits_used_by_branches(
    repo_path: Path,
    db: ForesterDB,
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


def delete_commit(repo_path: Path, commit_hash: str, force: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Delete a commit from the repository.
    
    Args:
        repo_path: Path to repository root
        commit_hash: Hash of commit to delete
        force: Force deletion even if it's the HEAD commit
        
    Returns:
        Tuple of (success, error_message)
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return False, "Repository not initialized"
    
    db_path = dfm_dir / "forester.db"
    db = ForesterDB(db_path)
    db.connect()
    
    try:
        storage = ObjectStorage(dfm_dir)
        
        # Check if commit exists
        commit_info = db.get_commit(commit_hash)
        if not commit_info:
            return False, f"Commit {commit_hash[:16]}... not found"
        
        # Check if it's the HEAD commit
        is_head, branch_name = is_commit_head(repo_path, commit_hash, db)
        if is_head and not force:
            return False, "Cannot delete HEAD commit. Use force=True to delete anyway."
        
        # Check if it's referenced by any branch
        is_referenced, ref_branch = is_commit_referenced_by_branches(repo_path, commit_hash, db)
        if is_referenced and not force:
            return False, f"Commit is referenced by branch '{ref_branch}'. Use force=True to delete anyway."
        
        # Get full commit data from storage before deletion
        commit_data = None
        try:
            commit_data = storage.load_commit(commit_hash)
        except FileNotFoundError:
            # Commit file doesn't exist, but we have DB record
            pass
        
        # Extract object hashes from commit
        tree_hash = commit_info.get('tree_hash') or (commit_data.get('tree_hash') if commit_data else None)
        mesh_hashes = []
        if commit_data:
            mesh_hashes = commit_data.get('mesh_hashes', [])
        elif commit_info.get('mesh_hashes'):
            # Try to parse from DB if stored as JSON
            import json
            try:
                mesh_hashes = json.loads(commit_info['mesh_hashes']) if isinstance(commit_info.get('mesh_hashes'), str) else commit_info.get('mesh_hashes', [])
            except (json.JSONDecodeError, TypeError):
                mesh_hashes = []
        
        # Delete commit from database
        db.delete_commit(commit_hash)
        
        # Delete commit from storage
        storage.delete_commit(commit_hash)
        
        # Delete tree and its blobs if not used by other commits
        if tree_hash:
            using_commits = db.get_commits_using_tree(tree_hash)
            # Remove current commit from list if present
            using_commits = [c for c in using_commits if c != commit_hash]
            
            if len(using_commits) == 0:
                # Tree is not used by other commits, safe to delete
                # First, get all blobs in this tree
                blob_hashes = db.get_all_blobs_in_tree(tree_hash)
                
                # Delete blobs that are not used by other commits
                for blob_hash in blob_hashes:
                    blob_using_commits = db.get_commits_using_blob(blob_hash)
                    # Remove current commit from list if present
                    blob_using_commits = [c for c in blob_using_commits if c != commit_hash]
                    
                    if len(blob_using_commits) == 0:
                        # Blob is not used, safe to delete
                        db.delete_blob(blob_hash)
                        storage.delete_blob(blob_hash)
                
                # Delete tree from database and storage
                db.delete_tree(tree_hash)
                storage.delete_tree(tree_hash)
        
        # Delete meshes if not used by other commits
        for mesh_hash in mesh_hashes:
            using_commits = db.get_commits_using_mesh(mesh_hash, storage)
            # Remove current commit from list if present
            using_commits = [c for c in using_commits if c != commit_hash]
            
            if len(using_commits) == 0:
                # Mesh is not used by other commits, safe to delete
                db.delete_mesh(mesh_hash)
                storage.delete_mesh(mesh_hash)
        
        # Update branch reference and HEAD if this was the HEAD
        is_head, current_branch = is_commit_head(repo_path, commit_hash, db)
        if is_head and current_branch:
            # Find parent commit or set to None
            parent_hash = commit_info.get('parent_hash')
            if parent_hash:
                set_branch_ref(repo_path, current_branch, parent_hash)
                db.set_head(parent_hash)
            else:
                # No parent - this was the first commit
                set_branch_ref(repo_path, current_branch, None)
                db.set_head(None)
        
        return True, None
        
    except Exception as e:
        return False, str(e)
    finally:
        db.close()



