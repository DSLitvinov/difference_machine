"""
Delete commit command for Forester.
"""

from pathlib import Path
from typing import Tuple, Optional
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage
from ..core.refs import get_branch_ref, set_branch_ref, get_current_branch
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
        current_branch = get_current_branch(repo_path)
        if not current_branch:
            return False, "Cannot determine current branch"
        
        branch_ref = get_branch_ref(repo_path, current_branch)
        
        # Also check HEAD from database
        head_commit = db.get_head()
        if (branch_ref == commit_hash or head_commit == commit_hash) and not force:
            return False, "Cannot delete HEAD commit. Use force=True to delete anyway."
        
        # Check if it's referenced by any branch
        from ..commands.branch import list_branches
        branches = list_branches(repo_path)
        for branch in branches:
            if branch.get('commit') and branch['commit']['hash'] == commit_hash:
                if not force:
                    return False, f"Commit is referenced by branch '{branch['name']}'. Use force=True to delete anyway."
        
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
        if branch_ref == commit_hash or head_commit == commit_hash:
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



