"""
Checkout command for Forester.
Switches branches or commits and restores working directory.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, List
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage
from ..core.refs import (
    get_branch_ref,
    get_current_head_commit
)
from ..models.commit import Commit
from ..models.tree import Tree
from ..models.mesh import Mesh
from ..utils.filesystem import remove_directory
from .commit import has_uncommitted_changes

logger = logging.getLogger(__name__)


def checkout(repo_path: Path, target: str, force: bool = False,
             file_patterns: Optional[List[str]] = None,
             mesh_names: Optional[List[str]] = None,
             skip_hooks: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Checkout a branch or commit.

    Args:
        repo_path: Path to repository root
        target: Branch name or commit hash
        force: If True, discard uncommitted changes without warning
        file_patterns: List of file path patterns to selectively checkout (e.g., ["textures/*", "*.json"])
                       If None, all files are checked out
        mesh_names: List of mesh names to selectively checkout (only for mesh_only commits)
                    If None, all meshes are checked out
        skip_hooks: If True, skip pre-checkout and post-checkout hooks

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
        error_message contains "uncommitted_changes" if there are uncommitted changes

    Raises:
        ValueError: If target doesn't exist or pre-checkout hook fails
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")

    # Run pre-checkout hook
    if not skip_hooks:
        from ..core.hooks import run_pre_checkout_hook
        try:
            run_pre_checkout_hook(repo_path, target, skip_hooks=False)
        except ValueError as e:
            return (False, f"Pre-checkout hook failed: {str(e)}")

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

    with ForesterDB(db_path) as db:
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

        # Check commit type
        if commit.commit_type == "mesh_only":
            # Mesh-only checkout: restore only selected meshes, don't touch other files
            restore_meshes_from_mesh_only_commit(commit, working_dir, storage, db, dfm_dir, mesh_names)
        else:
            # Project checkout: restore files from commit
            # Step 1: Remove tracked files from current HEAD (if exists) to preserve untracked files
            current_head = get_current_head_commit(repo_path)
            if current_head and current_head != commit_hash:
                # Get current HEAD tree to know which files to remove
                current_commit = Commit.from_storage(current_head, db, storage)
                if current_commit:
                    current_tree = current_commit.get_tree(db, storage)
                    if current_tree:
                        remove_tracked_files_from_tree(current_tree, working_dir, dfm_dir)
            else:
                # No current HEAD or same commit, just remove files from new commit tree
                remove_tracked_files_from_tree(tree, working_dir, dfm_dir)

            # Step 2: Restore files from tree (with selective checkout)
            restore_files_from_tree(tree, working_dir, storage, db, file_patterns)

            # Step 3: Restore meshes from commit
            restore_meshes_from_commit(commit, working_dir, storage, dfm_dir)

        # Step 4: Update database
        if is_branch:
            # Update current branch and HEAD
            db.set_branch_and_head(target, commit_hash)
        else:
            # Detached HEAD state (pointing to commit)
            db.set_head(commit_hash)

        # Step 5: Run post-checkout hook
        if not skip_hooks:
            from ..core.hooks import run_post_checkout_hook
            run_post_checkout_hook(repo_path, target, skip_hooks=False)

    return (True, None)


def clear_working_directory(working_dir: Path, dfm_dir: Path) -> None:
    """
    Clear working directory completely, excluding .DFM.

    WARNING: This function deletes ALL files in working directory except .DFM.
    Use remove_tracked_files_from_tree() instead to preserve untracked files.

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


def remove_tracked_files_from_tree(tree: Tree, working_dir: Path, dfm_dir: Path) -> None:
    """
    Remove only files that are tracked in the commit tree.
    This preserves untracked files (like textures) that are not in the commit.

    Args:
        tree: Tree object from commit
        working_dir: Working directory path
        dfm_dir: .DFM directory path
    """
    if not working_dir.exists():
        return

    # Remove tracked files and directories that are now empty
    for entry in tree.entries:
        if entry.type != "blob":
            continue

        dest_path = working_dir / entry.path
        if dest_path.exists():
            try:
                dest_path.unlink()
                # Try to remove empty parent directories
                parent = dest_path.parent
                while parent != working_dir and parent != dfm_dir:
                    try:
                        if parent.exists() and not any(parent.iterdir()):
                            parent.rmdir()
                            parent = parent.parent
                        else:
                            break
                    except OSError:
                        break
            except OSError:
                pass  # File might already be deleted or in use


def restore_files_from_tree(tree: Tree, working_dir: Path, storage: ObjectStorage,
                            db: ForesterDB, file_patterns: Optional[List[str]] = None) -> None:
    """
    Restore files from tree to working directory.

    Args:
        tree: Tree object
        working_dir: Working directory path
        storage: Object storage
        db: Database connection
        file_patterns: Optional list of file path patterns to selectively restore
    """
    from ..models.blob import Blob
    from ..utils.pattern_matching import match_patterns

    for entry in tree.entries:
        if entry.type != "blob":
            continue

        # Selective checkout: check if file matches patterns
        if file_patterns is not None and not match_patterns(entry.path, file_patterns):
            continue

        # Get destination path
        dest_path = working_dir / entry.path

        # Ensure parent directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Load blob
        try:
            blob = Blob.from_storage(entry.hash, db, storage)
            if not blob:
                logger.warning(
                    f"Blob {entry.hash[:16]}... not found in database, "
                    f"skipping {entry.path}"
                )
                continue

            # Load blob data
            blob_data = blob.load_data(storage)

            # Copy blob data to destination
            with open(dest_path, 'wb') as f:
                f.write(blob_data)
        except FileNotFoundError as e:
            logger.warning(f"{e}, skipping {entry.path}")
            continue
        except Exception as e:
            logger.error(
                f"Failed to restore {entry.path}: {e}",
                exc_info=True
            )
            continue


def restore_meshes_from_mesh_only_commit(commit: Commit, working_dir: Path,
                                         storage: ObjectStorage, db: ForesterDB,
                                         base_dir: Path, mesh_names: Optional[List[str]] = None) -> None:
    """
    Restore meshes from mesh-only commit.
    Only restores selected meshes, doesn't touch other files.

    Args:
        commit: Commit object (mesh_only type)
        working_dir: Working directory path
        storage: Object storage
        db: Database connection
        base_dir: Base directory (.DFM/)
        mesh_names: Optional list of mesh names to selectively restore
                    If None, all meshes are restored
    """
    if not commit.mesh_hashes or not commit.selected_mesh_names:
        return

    # Create meshes directory if needed
    meshes_dir = working_dir / "meshes"
    meshes_dir.mkdir(exist_ok=True)

    # Restore each mesh
    for i, mesh_hash in enumerate(commit.mesh_hashes):
        if i >= len(commit.selected_mesh_names):
            break

        mesh_name = commit.selected_mesh_names[i]

        # Selective checkout: check if mesh name matches filter
        if mesh_names is not None and mesh_name not in mesh_names:
            continue

        try:
            # Load mesh
            from ..models.mesh import Mesh
            mesh = Mesh.from_storage(mesh_hash, db, storage)
            if not mesh:
                logger.warning(
                    f"Mesh {mesh_hash[:16]}... not found in database, "
                    f"skipping {mesh_name}"
                )
                continue

            # Use mesh_hash for directory name (as stored in tree)
            mesh_dir_name = mesh_hash[:16]
            mesh_dir = meshes_dir / mesh_dir_name
            mesh_dir.mkdir(exist_ok=True)

            # Copy mesh.blend file
            import shutil
            mesh_info = db.get_mesh(mesh_hash)
            if mesh_info:
                storage_path = Path(mesh_info['path'])
                blend_source = storage_path / "mesh.blend"
                if blend_source.exists():
                    shutil.copy2(blend_source, mesh_dir / "mesh.blend")
                else:
                    logger.warning(f"mesh.blend not found for {mesh_name}, skipping")
                    continue
            else:
                logger.warning(f"Mesh info not found for {mesh_name}, skipping")
                continue

            # Copy textures from storage to working directory
            import shutil
            import os
            import json
            
            # Get material_json and normalize paths
            material_json = mesh.material_json.copy() if isinstance(mesh.material_json, dict) else {}
            
            if material_json and 'textures' in material_json:
                working_textures_dir = mesh_dir / "textures"
                working_textures_dir.mkdir(exist_ok=True)
                
                # Get storage path for textures
                storage_textures_dir = storage_path / "textures"
                
                for texture_info in material_json['textures']:
                    commit_path = texture_info.get('commit_path')
                    if commit_path:
                        # Normalize path - handle both Windows and Unix separators
                        # Remove 'textures/' prefix if present
                        normalized_path = str(commit_path).replace('\\', '/')
                        if normalized_path.startswith('textures/'):
                            normalized_path = normalized_path.replace('textures/', '', 1)
                        
                        # Try to copy texture from storage
                        texture_filename = os.path.basename(normalized_path)
                        storage_texture_path = storage_textures_dir / texture_filename
                        working_texture_path = working_textures_dir / texture_filename
                        
                        if storage_texture_path.exists() and storage_texture_path.is_file():
                            try:
                                shutil.copy2(storage_texture_path, working_texture_path)
                                logger.debug(f"Copied texture: {texture_filename} to {working_texture_path}")
                                # Update commit_path to point to working directory
                                texture_info['commit_path'] = f"textures/{texture_filename}"
                            except Exception as e:
                                logger.warning(f"Failed to copy texture {texture_filename}: {e}", exc_info=True)
                        else:
                            logger.warning(f"Texture not found in storage: {storage_texture_path}")
            
            # Save mesh_metadata.json (for diff and textures)
            metadata_path = mesh_dir / "mesh_metadata.json"
            metadata = {
                'mesh_json': mesh.mesh_json,
                'material_json': material_json,  # Use updated material_json with normalized paths
                'object_name': mesh_name,
            }
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

        except FileNotFoundError as e:
            logger.warning(f"{e}, skipping mesh {mesh_name}")
            continue
        except Exception as e:
            logger.error(
                f"Could not restore mesh {mesh_name}: {e}",
                exc_info=True
            )
            continue


def restore_meshes_from_commit(commit: Commit, working_dir: Path,
                               storage: ObjectStorage, base_dir: Path) -> None:
    """
    Restore meshes from project commit to working directory.

    Args:
        commit: Commit object (project type)
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
                    logger.warning(
                        f"Mesh {mesh_hash[:16]}... not found in database, skipping"
                    )
                    continue

                # Get mesh name from database (or use hash as fallback)
                mesh_info = db.get_mesh(mesh_hash)
                if not mesh_info:
                    logger.warning(
                        f"Mesh info {mesh_hash[:16]}... not found in database, "
                        f"skipping"
                    )
                    continue

                # Extract mesh name from path (e.g., "objects/meshes/aa/bb/.../mesh_name")
                # For now, we'll use a simple naming scheme
                mesh_name = f"mesh_{mesh_hash[:8]}"

                # Create mesh directory
                mesh_dir = meshes_dir / mesh_name
                mesh_dir.mkdir(exist_ok=True)

                # Copy textures from storage to working directory
                import shutil
                import os
                import json
                
                # Get storage path
                storage_path = Path(mesh_info['path'])
                storage_textures_dir = storage_path / "textures"
                
                # Get material_json and normalize paths
                material_json = mesh.material_json.copy() if isinstance(mesh.material_json, dict) else {}
                
                if material_json and 'textures' in material_json:
                    working_textures_dir = mesh_dir / "textures"
                    working_textures_dir.mkdir(exist_ok=True)
                    
                    for texture_info in material_json['textures']:
                        commit_path = texture_info.get('commit_path')
                        if commit_path:
                            # Normalize path - handle both Windows and Unix separators
                            # Remove 'textures/' prefix if present
                            normalized_path = str(commit_path).replace('\\', '/')
                            if normalized_path.startswith('textures/'):
                                normalized_path = normalized_path.replace('textures/', '', 1)
                            
                            # Try to copy texture from storage
                            texture_filename = os.path.basename(normalized_path)
                            storage_texture_path = storage_textures_dir / texture_filename
                            working_texture_path = working_textures_dir / texture_filename
                            
                            if storage_texture_path.exists() and storage_texture_path.is_file():
                                try:
                                    shutil.copy2(storage_texture_path, working_texture_path)
                                    logger.debug(f"Copied texture: {texture_filename} to {working_texture_path}")
                                    # Update commit_path to point to working directory
                                    texture_info['commit_path'] = f"textures/{texture_filename}"
                                except Exception as e:
                                    logger.warning(f"Failed to copy texture {texture_filename}: {e}", exc_info=True)
                            else:
                                logger.warning(f"Texture not found in storage: {storage_texture_path}")

                # Save mesh.json
                mesh_json_path = mesh_dir / "mesh.json"
                with open(mesh_json_path, 'w', encoding='utf-8') as f:
                    json.dump(mesh.mesh_json, f, indent=2, ensure_ascii=False)

                # Save material.json with updated paths
                material_json_path = mesh_dir / "material.json"
                with open(material_json_path, 'w', encoding='utf-8') as f:
                    json.dump(material_json, f, indent=2, ensure_ascii=False)

            except FileNotFoundError as e:
                # Skip meshes that can't be restored
                logger.warning(f"{e}, skipping mesh {mesh_hash[:8]}...")
                continue
            except Exception as e:
                # Skip meshes that can't be restored
                logger.error(
                    f"Could not restore mesh {mesh_hash[:8]}...: {e}",
                    exc_info=True
                )
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
