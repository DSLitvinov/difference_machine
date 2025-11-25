"""
Delete commit command for Forester.
"""

from pathlib import Path
from typing import Tuple, Optional
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage
from ..core.refs import get_branch_ref, set_branch_ref, get_current_branch
from ..core.metadata import Metadata
from ..models.commit import Commit


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
        metadata_path = dfm_dir / "metadata.json"
        metadata = Metadata(metadata_path)
        metadata.load()
        
        current_branch = metadata.current_branch
        branch_ref = get_branch_ref(repo_path, current_branch)
        
        if branch_ref == commit_hash and not force:
            return False, "Cannot delete HEAD commit. Use force=True to delete anyway."
        
        # Check if it's referenced by any branch
        from ..commands.branch import list_branches
        branches = list_branches(repo_path)
        for branch in branches:
            if branch.get('commit') and branch['commit']['hash'] == commit_hash:
                if not force:
                    return False, f"Commit is referenced by branch '{branch['name']}'. Use force=True to delete anyway."
        
        # Delete commit from database
        db.delete_commit(commit_hash)
        
        # Delete commit from storage
        storage.delete_commit(commit_hash)
        
        # Update branch reference if this was the HEAD
        if branch_ref == commit_hash:
            # Find parent commit or set to None
            parent_hash = commit_info.get('parent_hash')
            if parent_hash:
                set_branch_ref(repo_path, current_branch, parent_hash)
                metadata.head = parent_hash
            else:
                # No parent - this was the first commit
                set_branch_ref(repo_path, current_branch, None)
                metadata.head = None
            metadata.save()
        
        return True, None
        
    except Exception as e:
        return False, str(e)
    finally:
        db.close()

