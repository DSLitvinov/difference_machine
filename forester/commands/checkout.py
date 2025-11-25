"""
Checkout command for Forester.
Switches branches or commits and restores working directory.
"""

from pathlib import Path
from typing import Optional, Tuple
from ..core.database import ForesterDB
from ..core.ignore import IgnoreRules
from ..core.metadata import Metadata
from ..core.storage import ObjectStorage
from ..core.refs import get_branch_ref, get_current_branch, set_branch_ref, set_head
from ..models.commit import Commit
from ..models.tree import Tree
from ..models.mesh import Mesh
from ..utils.filesystem import remove_directory, copy_file, ensure_directory
from .commit import has_uncommitted_changes


def checkout(repo_path: Path, target: str, force: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Checkout a branch or commit.
    
    Args:
        repo_path: Path to repository root
        target: Branch name or commit hash
        force: If True, discard uncommitted changes without warning
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
        error_message contains "uncommitted_changes" if there are uncommitted changes
        
    Raises:
        ValueError: If target doesn't exist
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")
    
    # Check for uncommitted changes
    if not force and has_uncommitted_changes(repo_path):
        return (False, "uncommitted_changes")
    
    # Determine if target is a branch or commit hash
    branch_ref = get_branch_ref(repo_path, target)
    if branch_ref is not None:
        # Target is a branch
        commit_hash = branch_ref
        is_branch = True
    else:
        # Check if target is a commit hash
        db_path = dfm_dir / "forester.db"
        with ForesterDB(db_path) as db:
            commit_data = db.get_commit(target)
            if commit_data:
                commit_hash = target
                is_branch = False
            else:
                raise ValueError(f"Target '{target}' is neither a branch nor a commit")
    
    # Load commit
    db_path = dfm_dir / "forester.db"
    db = ForesterDB(db_path)
    db.connect()
    
    try:
        storage = ObjectStorage(dfm_dir)
        commit = Commit.from_storage(commit_hash, db, storage)
        
        if not commit:
            raise ValueError(f"Commit {commit_hash} not found")
        
        # Get tree from commit
        tree = commit.get_tree(db, storage)
        if not tree:
            raise ValueError(f"Tree for commit {commit_hash} not found")
        
        # Determine working directory
        working_dir = repo_path / "working"
        if not working_dir.exists():
            working_dir = repo_path  # Fallback to repo root
        
        # Step 1: Clear working directory (completely, including meshes/)
        clear_working_directory(working_dir, dfm_dir)
        
        # Step 2: Restore files from tree
        restore_files_from_tree(tree, working_dir, storage, db)
        
        # Step 3: Restore meshes from commit
        restore_meshes_from_commit(commit, working_dir, storage, dfm_dir)
        
        # Step 4: Update HEAD and metadata
        if is_branch:
            # Update current branch
            metadata_path = dfm_dir / "metadata.json"
            metadata = Metadata(metadata_path)
            metadata.load()
            metadata.current_branch = target
            metadata.head = commit_hash
            metadata.save()
            
            # Update HEAD file
            set_head(repo_path, target)
        else:
            # Detached HEAD state (pointing to commit)
            metadata_path = dfm_dir / "metadata.json"
            metadata = Metadata(metadata_path)
            metadata.load()
            metadata.head = commit_hash
            metadata.save()
            
            # Update HEAD file to point to commit
            set_head(repo_path, commit_hash)
        
        return (True, None)
        
    finally:
        db.close()


def clear_working_directory(working_dir: Path, dfm_dir: Path) -> None:
    """
    Clear working directory completely, excluding .DFM.
    
    Args:
        working_dir: Working directory path
        dfm_dir: .DFM directory path
    """
    if not working_dir.exists():
        return
    
    # Remove all items except .DFM
    for item in working_dir.iterdir():
        if item.name == ".DFM":
            continue
        
        if item.is_dir():
            remove_directory(item)
        else:
            item.unlink()


def restore_files_from_tree(tree: Tree, working_dir: Path, storage: ObjectStorage,
                            db: ForesterDB) -> None:
    """
    Restore files from tree to working directory.
    
    Args:
        tree: Tree object
        working_dir: Working directory path
        storage: Object storage
        db: Database connection
    """
    from ..models.blob import Blob
    
    for entry in tree.entries:
        if entry.type != "blob":
            continue
        
        # Get destination path
        dest_path = working_dir / entry.path
        
        # Ensure parent directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load blob
        blob = Blob.from_storage(entry.hash, db, storage)
        if not blob:
            continue
        
        # Copy blob data to destination
        blob_data = blob.load_data(storage)
        with open(dest_path, 'wb') as f:
            f.write(blob_data)


def restore_meshes_from_commit(commit: Commit, working_dir: Path, 
                               storage: ObjectStorage, base_dir: Path) -> None:
    """
    Restore meshes from commit to working directory.
    
    Args:
        commit: Commit object
        working_dir: Working directory path
        storage: Object storage
        base_dir: Base directory (.DFM/)
    """
    if not commit.mesh_hashes:
        return
    
    # Create meshes directory
    meshes_dir = working_dir / "meshes"
    meshes_dir.mkdir(exist_ok=True)
    
    db_path = base_dir / "forester.db"
    with ForesterDB(db_path) as db:
        for mesh_hash in commit.mesh_hashes:
            try:
                # Load mesh
                mesh = Mesh.from_storage(mesh_hash, db, storage)
                if not mesh:
                    continue
                
                # Get mesh name from database (or use hash as fallback)
                mesh_info = db.get_mesh(mesh_hash)
                if not mesh_info:
                    continue
                
                # Extract mesh name from path (e.g., "objects/meshes/aa/bb/.../mesh_name")
                # For now, we'll use a simple naming scheme
                mesh_name = f"mesh_{mesh_hash[:8]}"
                
                # Create mesh directory
                mesh_dir = meshes_dir / mesh_name
                mesh_dir.mkdir(exist_ok=True)
                
                # Save mesh.json
                import json
                mesh_json_path = mesh_dir / "mesh.json"
                with open(mesh_json_path, 'w', encoding='utf-8') as f:
                    json.dump(mesh.mesh_json, f, indent=2, ensure_ascii=False)
                
                # Save material.json
                material_json_path = mesh_dir / "material.json"
                with open(material_json_path, 'w', encoding='utf-8') as f:
                    json.dump(mesh.material_json, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                # Skip meshes that can't be restored
                print(f"Warning: Could not restore mesh {mesh_hash[:8]}...: {e}")
                continue


def checkout_branch(repo_path: Path, branch_name: str, force: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Checkout a branch (convenience wrapper).
    
    Args:
        repo_path: Path to repository root
        branch_name: Branch name
        force: If True, discard uncommitted changes
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    return checkout(repo_path, branch_name, force)


def checkout_commit(repo_path: Path, commit_hash: str, force: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Checkout a specific commit (detached HEAD).
    
    Args:
        repo_path: Path to repository root
        commit_hash: Commit hash
        force: If True, discard uncommitted changes
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    return checkout(repo_path, commit_hash, force)

