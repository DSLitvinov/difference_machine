"""
Garbage collection command for Forester.
Removes unused objects from storage that are not referenced by any commits.
"""

import logging
from pathlib import Path
from typing import Set, Tuple, Optional, Dict
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage
from .delete_commit import get_all_commits_used_by_branches

logger = logging.getLogger(__name__)


def _safe_delete_file(file_path: Path) -> None:
    """
    Safely delete a file and its empty parent directories.
    
    Args:
        file_path: Path to file to delete
    """
    if not file_path.exists():
        return
    
    try:
        file_path.unlink()
        
        # Try to remove empty parent directories
        parent_dir = file_path.parent
        if parent_dir.exists():
            try:
                # Check if directory is empty
                if not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                    # Try to remove grandparent directory
                    grandparent_dir = parent_dir.parent
                    if grandparent_dir.exists():
                        try:
                            if not any(grandparent_dir.iterdir()):
                                grandparent_dir.rmdir()
                        except (OSError, FileNotFoundError):
                            pass  # Directory not empty or doesn't exist
            except (OSError, FileNotFoundError):
                pass  # Directory not empty or doesn't exist
    except (OSError, FileNotFoundError):
        pass  # File already deleted or doesn't exist


def _safe_delete_directory(dir_path: Path) -> None:
    """
    Safely delete a directory and its empty parent directories.
    
    Args:
        dir_path: Path to directory to delete
    """
    if not dir_path.exists():
        return
    
    try:
        import shutil
        shutil.rmtree(dir_path)
        
        # Try to remove empty parent directories
        parent_dir = dir_path.parent
        if parent_dir.exists():
            try:
                if not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                    # Try to remove grandparent directory
                    grandparent_dir = parent_dir.parent
                    if grandparent_dir.exists():
                        try:
                            if not any(grandparent_dir.iterdir()):
                                grandparent_dir.rmdir()
                        except (OSError, FileNotFoundError):
                            pass
            except (OSError, FileNotFoundError):
                pass
    except (OSError, FileNotFoundError):
        pass


def _extract_hash_from_path(file_path: Path, base_dir: Path, obj_type: str) -> Optional[str]:
    """Extract hash from file path."""
    try:
        obj_dir = base_dir / "objects" / obj_type
        if not obj_dir.exists():
            return None
        
        try:
            rel_path = file_path.relative_to(obj_dir)
        except ValueError:
            # File is not relative to obj_dir, skip it
            return None
        
        parts = rel_path.parts
        
        if len(parts) >= 3:
            # Path format: aa/bb/ccddee...
            return parts[0] + parts[1] + parts[2]
        elif len(parts) == 1:
            # Flat structure (shouldn't happen, but handle it)
            return parts[0]
    except (ValueError, IndexError, OSError) as e:
        logger.debug(f"Error extracting hash from path {file_path}: {e}")
        return None
    
    return None


def garbage_collect(repo_path: Path, dry_run: bool = False) -> Tuple[bool, Optional[str], Dict[str, int]]:
    """
    Remove unused objects from storage.
    
    This function finds all objects (commits, trees, blobs, meshes) that are
    not referenced by any commits in branches and removes them from storage.
    
    Args:
        repo_path: Path to repository root
        dry_run: If True, only report what would be deleted without actually deleting
        
    Returns:
        Tuple of (success, error_message, stats_dict)
        stats_dict contains counts of deleted objects by type
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return False, "Repository not initialized", {}
    
    db_path = dfm_dir / "forester.db"
    storage = ObjectStorage(dfm_dir)
    
    stats = {
        'commits_deleted': 0,
        'trees_deleted': 0,
        'blobs_deleted': 0,
        'meshes_deleted': 0,
        'commits_kept': 0,
        'trees_kept': 0,
        'blobs_kept': 0,
        'meshes_kept': 0,
    }
    
    try:
        with ForesterDB(db_path) as db:
            # Step 1: Get all commits used by branches (including parent chains)
            logger.info("Finding all commits used by branches...")
            used_commits = get_all_commits_used_by_branches(repo_path, db)
            logger.info(f"Found {len(used_commits)} commits in use")
            
            # Step 2: Collect all objects used by these commits
            logger.info("Collecting all objects used by commits...")
            used_trees: Set[str] = set()
            used_blobs: Set[str] = set()
            used_meshes: Set[str] = set()
            
            for commit_hash in used_commits:
                commit_info = db.get_commit(commit_hash)
                if not commit_info:
                    continue
                
                # Get tree_hash
                tree_hash = commit_info.get('tree_hash')
                if tree_hash:
                    used_trees.add(tree_hash)
                    # Get all blobs in this tree
                    blob_hashes = db.get_all_blobs_in_tree(tree_hash)
                    used_blobs.update(blob_hashes)
                
                # Get mesh_hashes from commit data
                try:
                    commit_data = storage.load_commit(commit_hash)
                    mesh_hashes = commit_data.get('mesh_hashes', [])
                    if mesh_hashes:
                        used_meshes.update(mesh_hashes)
                except Exception:
                    # Try to get from DB if commit file doesn't exist
                    if commit_info.get('mesh_hashes'):
                        import json
                        try:
                            mesh_hashes = json.loads(commit_info['mesh_hashes']) if isinstance(commit_info.get('mesh_hashes'), str) else commit_info.get('mesh_hashes', [])
                            used_meshes.update(mesh_hashes)
                        except Exception:
                            pass
            
            logger.info(f"Found {len(used_trees)} trees, {len(used_blobs)} blobs, {len(used_meshes)} meshes in use")
            
            # Step 3: Also preserve stash objects
            logger.info("Preserving stash objects...")
            stash_commits = set()
            try:
                stashes = db.get_all_stashes()
                for stash in stashes:
                    stash_hash = stash.get('hash')
                    if stash_hash:
                        stash_commits.add(stash_hash)
                        # Get tree from stash
                        stash_tree = stash.get('tree_hash')
                        if stash_tree:
                            used_trees.add(stash_tree)
                            blob_hashes = db.get_all_blobs_in_tree(stash_tree)
                            used_blobs.update(blob_hashes)
            except Exception as e:
                logger.warning(f"Error getting stashes: {e}")
            
            # Step 4: Scan storage and delete unused objects
            logger.info("Scanning storage for unused objects...")
            
            # Delete unused commits
            commits_dir = dfm_dir / "objects" / "commits"
            if commits_dir.exists():
                # Collect files first to avoid issues with rglob during deletion
                commit_files_to_check = []
                for commit_file in commits_dir.rglob("*"):
                    if commit_file.is_file() and commit_file.exists():
                        commit_files_to_check.append(commit_file)
                
                for commit_file in commit_files_to_check:
                    # Double-check file still exists (might have been deleted)
                    if not commit_file.exists():
                        continue
                    
                    commit_hash = _extract_hash_from_path(commit_file, dfm_dir, "commits")
                    if not commit_hash:
                        continue
                    
                    if commit_hash in used_commits or commit_hash in stash_commits:
                        stats['commits_kept'] += 1
                    else:
                        stats['commits_deleted'] += 1
                        if not dry_run:
                            try:
                                _safe_delete_file(commit_file)
                                logger.debug(f"Deleted unused commit: {commit_hash[:16]}...")
                            except Exception as e:
                                logger.warning(f"Failed to delete commit {commit_hash[:16]}...: {e}")
            
            # Delete unused trees
            trees_dir = dfm_dir / "objects" / "trees"
            if trees_dir.exists():
                # Collect files first
                tree_files_to_check = []
                for tree_file in trees_dir.rglob("*"):
                    if tree_file.is_file() and tree_file.exists():
                        tree_files_to_check.append(tree_file)
                
                for tree_file in tree_files_to_check:
                    if not tree_file.exists():
                        continue
                    
                    tree_hash = _extract_hash_from_path(tree_file, dfm_dir, "trees")
                    if not tree_hash:
                        continue
                    
                    if tree_hash in used_trees:
                        stats['trees_kept'] += 1
                    else:
                        stats['trees_deleted'] += 1
                        if not dry_run:
                            try:
                                _safe_delete_file(tree_file)
                                logger.debug(f"Deleted unused tree: {tree_hash[:16]}...")
                            except Exception as e:
                                logger.warning(f"Failed to delete tree {tree_hash[:16]}...: {e}")
            
            # Delete unused blobs
            blobs_dir = dfm_dir / "objects" / "blobs"
            if blobs_dir.exists():
                # Collect files first
                blob_files_to_check = []
                for blob_file in blobs_dir.rglob("*"):
                    if blob_file.is_file() and blob_file.exists():
                        blob_files_to_check.append(blob_file)
                
                for blob_file in blob_files_to_check:
                    if not blob_file.exists():
                        continue
                    
                    blob_hash = _extract_hash_from_path(blob_file, dfm_dir, "blobs")
                    if not blob_hash:
                        continue
                    
                    if blob_hash in used_blobs:
                        stats['blobs_kept'] += 1
                    else:
                        stats['blobs_deleted'] += 1
                        if not dry_run:
                            try:
                                _safe_delete_file(blob_file)
                                logger.debug(f"Deleted unused blob: {blob_hash[:16]}...")
                            except Exception as e:
                                logger.warning(f"Failed to delete blob {blob_hash[:16]}...: {e}")
            
            # Delete unused meshes
            meshes_dir = dfm_dir / "objects" / "meshes"
            if meshes_dir.exists():
                # Collect directories first
                mesh_dirs_to_check = []
                for mesh_dir_path in meshes_dir.rglob("*"):
                    if mesh_dir_path.is_dir() and mesh_dir_path.exists():
                        mesh_dirs_to_check.append(mesh_dir_path)
                
                for mesh_dir_path in mesh_dirs_to_check:
                    if not mesh_dir_path.exists():
                        continue
                    
                    mesh_hash = _extract_hash_from_path(mesh_dir_path, dfm_dir, "meshes")
                    if not mesh_hash:
                        continue
                    
                    if mesh_hash in used_meshes:
                        stats['meshes_kept'] += 1
                    else:
                        stats['meshes_deleted'] += 1
                        if not dry_run:
                            try:
                                _safe_delete_directory(mesh_dir_path)
                                logger.debug(f"Deleted unused mesh: {mesh_hash[:16]}...")
                            except Exception as e:
                                logger.warning(f"Failed to delete mesh {mesh_hash[:16]}...: {e}")
            
            action = "Would delete" if dry_run else "Deleted"
            logger.info(f"{action} {stats['commits_deleted']} commits, {stats['trees_deleted']} trees, "
                       f"{stats['blobs_deleted']} blobs, {stats['meshes_deleted']} meshes")
            
            # Step 5: Clean up temporary directories (preview_temp and compare_temp)
            logger.info("Cleaning up temporary directories...")
            temp_dirs_to_clean = [
                dfm_dir / "preview_temp",
                dfm_dir / "compare_temp"
            ]
            
            for temp_dir in temp_dirs_to_clean:
                if temp_dir.exists() and temp_dir.is_dir():
                    try:
                        if not dry_run:
                            import shutil
                            shutil.rmtree(temp_dir)
                            logger.debug(f"Cleaned up temporary directory: {temp_dir.name}")
                        else:
                            # Count files in directory for dry run
                            file_count = sum(1 for _ in temp_dir.rglob("*") if _.is_file())
                            logger.debug(f"Would clean up temporary directory: {temp_dir.name} ({file_count} files)")
                    except (OSError, PermissionError) as e:
                        logger.warning(f"Failed to clean up temporary directory {temp_dir.name}: {e}")
            
            return True, None, stats
            
    except Exception as e:
        error_msg = f"Failed to garbage collect: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, stats

