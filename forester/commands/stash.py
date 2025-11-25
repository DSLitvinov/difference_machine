"""
Stash command for Forester.
Manages stashes (frozen states) for uncommitted changes.
"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from ..core.database import ForesterDB
from ..core.ignore import IgnoreRules
from ..core.metadata import Metadata
from ..core.storage import ObjectStorage
from ..core.refs import get_current_branch
from ..models.tree import Tree
from ..models.commit import Commit
from ..utils.filesystem import scan_directory
from .commit import has_uncommitted_changes
from .checkout import restore_files_from_tree, restore_meshes_from_commit


def create_stash(repo_path: Path, message: Optional[str] = None) -> Optional[str]:
    """
    Create a stash from current working directory state.
    
    Args:
        repo_path: Path to repository root
        message: Optional stash message
        
    Returns:
        Stash hash if successful, None if no changes to stash
        
    Raises:
        ValueError: If repository is not initialized
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")
    
    # Check if there are changes to stash
    if not has_uncommitted_changes(repo_path):
        return None  # Nothing to stash
    
    # Get current branch
    branch = get_current_branch(repo_path)
    if not branch:
        branch = "main"
    
    # Initialize components
    db_path = dfm_dir / "forester.db"
    db = ForesterDB(db_path)
    db.connect()
    
    try:
        storage = ObjectStorage(dfm_dir)
        ignore_file = dfm_dir / ".dfmignore"
        ignore_rules = IgnoreRules(ignore_file)
        
        # Determine working directory
        working_dir = repo_path / "working"
        if not working_dir.exists():
            working_dir = repo_path
        
        # Create extended ignore rules (exclude meshes/)
        class ExtendedIgnoreRules(IgnoreRules):
            def should_ignore(self, path: Path, base_path: Path) -> bool:
                if super().should_ignore(path, base_path):
                    return True
                try:
                    rel_path = path.relative_to(base_path) if path.is_absolute() else path
                    if str(rel_path).startswith("meshes/"):
                        return True
                except ValueError:
                    pass
                return False
        
        extended_ignore = ExtendedIgnoreRules(ignore_file)
        
        # Step 1: Scan and create blobs for files
        from ..models.blob import Blob
        
        files = scan_directory(working_dir, extended_ignore, working_dir)
        tree_entries = []
        
        for file_path in files:
            try:
                rel_path = file_path.relative_to(working_dir)
                blob = Blob.from_file(file_path, dfm_dir, db, storage)
                
                from ..models.tree import TreeEntry
                entry = TreeEntry(
                    path=str(rel_path),
                    type="blob",
                    hash=blob.hash,
                    size=blob.size
                )
                tree_entries.append(entry)
            except Exception as e:
                print(f"Warning: Skipping file {file_path}: {e}")
                continue
        
        # Step 2: Scan meshes
        from ..models.mesh import Mesh
        
        meshes_dir = working_dir / "meshes"
        mesh_hashes = []
        
        if meshes_dir.exists() and meshes_dir.is_dir():
            for mesh_dir in meshes_dir.iterdir():
                if not mesh_dir.is_dir():
                    continue
                
                mesh_json_path = mesh_dir / "mesh.json"
                if not mesh_json_path.exists():
                    continue
                
                try:
                    material_json_path = mesh_dir / "material.json"
                    if not material_json_path.exists():
                        material_json_path.write_text("{}")
                    
                    mesh = Mesh.from_directory(mesh_dir, dfm_dir, db, storage)
                    if mesh:
                        mesh_hashes.append(mesh.hash)
                except Exception as e:
                    print(f"Warning: Skipping mesh {mesh_dir}: {e}")
                    continue
        
        # Step 3: Create tree
        tree = Tree(hash="", entries=tree_entries)
        tree.hash = tree.compute_hash()
        tree.save_to_storage(db, storage)
        
        # Step 4: Create stash entry
        timestamp = int(time.time())
        stash_message = message or f"Auto-stash before switch to {branch}"
        
        # Compute stash hash
        stash_data = f"{tree.hash}{timestamp}{stash_message}{branch}"
        from ..core.hashing import compute_hash
        stash_hash = compute_hash(stash_data.encode('utf-8'))
        
        # Save to database
        db.add_stash(stash_hash, timestamp, stash_message, tree.hash, branch)
        
        return stash_hash
        
    finally:
        db.close()


def list_stashes(repo_path: Path) -> List[Dict[str, Any]]:
    """
    List all stashes.
    
    Args:
        repo_path: Path to repository root
        
    Returns:
        List of stash information dictionaries, sorted by timestamp (newest first)
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return []
    
    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        stashes = db.list_stashes()
        
        result = []
        for stash in stashes:
            result.append({
                "hash": stash['hash'],
                "timestamp": stash['timestamp'],
                "message": stash.get('message', ''),
                "branch": stash.get('branch', ''),
                "tree_hash": stash['tree_hash']
            })
        
        return result


def apply_stash(repo_path: Path, stash_hash: str, force: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Apply (restore) a stash.
    
    Args:
        repo_path: Path to repository root
        stash_hash: Stash hash
        force: If True, discard uncommitted changes before applying
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
        error_message contains "uncommitted_changes" if there are uncommitted changes
        
    Raises:
        ValueError: If stash doesn't exist
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")
    
    # Check for uncommitted changes
    if not force and has_uncommitted_changes(repo_path):
        # Create a new stash of current state before applying
        create_stash(repo_path, "Auto-stash before applying stash")
        # Continue with application
    
    # Load stash
    db_path = dfm_dir / "forester.db"
    db = ForesterDB(db_path)
    db.connect()
    
    try:
        storage = ObjectStorage(dfm_dir)
        
        stash_data = db.get_stash(stash_hash)
        if not stash_data:
            raise ValueError(f"Stash {stash_hash} not found")
        
        # Load tree
        tree = Tree.from_storage(stash_data['tree_hash'], db, storage)
        if not tree:
            raise ValueError(f"Tree for stash {stash_hash} not found")
        
        # Determine working directory
        working_dir = repo_path / "working"
        if not working_dir.exists():
            working_dir = repo_path
        
        # Clear working directory
        from .checkout import clear_working_directory
        clear_working_directory(working_dir, dfm_dir)
        
        # Restore files from tree
        restore_files_from_tree(tree, working_dir, storage, db)
        
        # Note: Meshes are not restored from stash currently
        # This is a limitation - stash would need to store mesh_hashes
        # For now, only files are restored
        
        return (True, None)
        
    finally:
        db.close()


def delete_stash(repo_path: Path, stash_hash: str) -> bool:
    """
    Delete a stash.
    
    Args:
        repo_path: Path to repository root
        stash_hash: Stash hash
        
    Returns:
        True if successful
        
    Raises:
        ValueError: If stash doesn't exist
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")
    
    db_path = dfm_dir / "forester.db"
    db = ForesterDB(db_path)
    db.connect()
    
    try:
        # Check if stash exists
        stash_data = db.get_stash(stash_hash)
        if not stash_data:
            raise ValueError(f"Stash {stash_hash} not found")
        
        # Get tree hash
        tree_hash = stash_data['tree_hash']
        
        # Delete stash from database
        db.delete_stash(stash_hash)
        
        # Check if tree is used by other stashes
        other_stashes = db.list_stashes()
        tree_used = any(s['tree_hash'] == tree_hash for s in other_stashes)
        
        # If tree is not used, we could delete it, but for safety we'll keep it
        # (Similar to how git keeps objects even after stash deletion)
        
        return True
        
    finally:
        db.close()

