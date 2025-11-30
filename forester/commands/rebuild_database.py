"""
Rebuild database command for Forester.
Reconstructs the database from file system storage.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage
from ..core.hashing import hash_to_path, compute_file_hash

logger = logging.getLogger(__name__)


def rebuild_database(repo_path: Path, backup: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Rebuild database from file system storage.

    This function scans all objects in the storage and reconstructs
    the database entries. Useful for recovering from database corruption.

    Args:
        repo_path: Path to repository root
        backup: If True, create backup of existing database before rebuilding

    Returns:
        Tuple of (success, error_message)
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return False, "Repository not initialized"

    db_path = dfm_dir / "forester.db"
    storage = ObjectStorage(dfm_dir)

    # Backup existing database if requested
    if backup and db_path.exists():
        backup_path = db_path.with_suffix('.db.backup')
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to backup database: {e}")

    try:
        # Create new database
        with ForesterDB(db_path) as db:
            # Reinitialize schema (this will create empty tables)
            db.initialize_schema()

            # Step 1: Rebuild commits from storage
            logger.info("Rebuilding commits...")
            commits_rebuilt = _rebuild_commits(dfm_dir, db, storage)
            logger.info(f"Rebuilt {commits_rebuilt} commits")

            # Step 2: Rebuild trees from storage
            logger.info("Rebuilding trees...")
            trees_rebuilt = _rebuild_trees(dfm_dir, db, storage)
            logger.info(f"Rebuilt {trees_rebuilt} trees")

            # Step 3: Rebuild blobs from storage
            logger.info("Rebuilding blobs...")
            blobs_rebuilt = _rebuild_blobs(dfm_dir, db, storage)
            logger.info(f"Rebuilt {blobs_rebuilt} blobs")

            # Step 4: Rebuild meshes from storage
            logger.info("Rebuilding meshes...")
            meshes_rebuilt = _rebuild_meshes(dfm_dir, db, storage)
            logger.info(f"Rebuilt {meshes_rebuilt} meshes")

            # Step 5: Rebuild branch references and repository state
            logger.info("Rebuilding branch references...")
            branches_rebuilt = _rebuild_branch_refs(repo_path, db)
            logger.info(f"Rebuilt {branches_rebuilt} branch references")

            # Step 6: Rebuild repository state (current branch and HEAD)
            _rebuild_repository_state(repo_path, db)

            logger.info("Database rebuild completed successfully")
            return True, None

    except Exception as e:
        error_msg = f"Failed to rebuild database: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def _extract_hash_from_path(file_path: Path, base_dir: Path, obj_type: str) -> Optional[str]:
    """
    Extract hash from file path.

    Path format: objects/{obj_type}/aa/bb/ccddee...
    Returns: aabbccddee... (full hash)
    """
    try:
        obj_dir = base_dir / "objects" / obj_type
        rel_path = file_path.relative_to(obj_dir)
        parts = rel_path.parts

        if len(parts) >= 3:
            # Combine: aa + bb + ccddee...
            return parts[0] + parts[1] + parts[2]
        elif len(parts) == 1:
            # Flat structure (shouldn't happen, but handle it)
            return parts[0]
    except (ValueError, IndexError):
        pass

    return None


def _rebuild_commits(dfm_dir: Path, db: ForesterDB, storage: ObjectStorage) -> int:
    """Rebuild commits table from storage."""
    commits_dir = dfm_dir / "objects" / "commits"
    if not commits_dir.exists():
        return 0

    count = 0

    # Scan all commit files recursively
    for commit_file in commits_dir.rglob("*"):
        if not commit_file.is_file():
            continue

        # Extract hash from path
        hash_str = _extract_hash_from_path(commit_file, dfm_dir, "commits")
        if not hash_str:
            continue

        # Load commit data
        try:
            commit_data = storage.load_commit(hash_str)
        except Exception as e:
            logger.warning(f"Failed to load commit {hash_str[:16]}...: {e}")
            continue

        # Extract commit information
        commit_hash = commit_data.get('hash', hash_str)
        branch = commit_data.get('branch', 'main')  # Default to 'main' if not found
        parent_hash = commit_data.get('parent_hash')
        timestamp = commit_data.get('timestamp', 0)
        message = commit_data.get('message', '')
        tree_hash = commit_data.get('tree_hash', '')
        author = commit_data.get('author', 'Unknown')
        commit_type = commit_data.get('commit_type', 'project')
        selected_mesh_names = commit_data.get('selected_mesh_names', [])
        export_options = commit_data.get('export_options', {})

        # Add to database
        try:
            db.add_commit(
                commit_hash=commit_hash,
                branch=branch,
                parent_hash=parent_hash,
                timestamp=timestamp,
                message=message,
                tree_hash=tree_hash,
                author=author,
                commit_type=commit_type,
                selected_mesh_names=selected_mesh_names,
                export_options=export_options
            )
            count += 1
        except Exception as e:
            logger.warning(f"Failed to add commit {commit_hash[:16]}... to database: {e}")
            continue

    return count


def _rebuild_trees(dfm_dir: Path, db: ForesterDB, storage: ObjectStorage) -> int:
    """Rebuild trees table from storage."""
    trees_dir = dfm_dir / "objects" / "trees"
    if not trees_dir.exists():
        return 0

    count = 0

    # Scan all tree files recursively
    for tree_file in trees_dir.rglob("*"):
        if not tree_file.is_file():
            continue

        hash_str = _extract_hash_from_path(tree_file, dfm_dir, "trees")
        if not hash_str:
            continue

        # Load tree data
        try:
            tree_data = storage.load_tree(hash_str)
        except Exception as e:
            logger.warning(f"Failed to load tree {hash_str[:16]}...: {e}")
            continue

        # Add to database
        try:
            entries = tree_data.get('entries', [])
            db.add_tree(hash_str, entries)
            count += 1
        except Exception as e:
            logger.warning(f"Failed to add tree {hash_str[:16]}... to database: {e}")
            continue

    return count


def _rebuild_blobs(dfm_dir: Path, db: ForesterDB, storage: ObjectStorage) -> int:
    """Rebuild blobs table from storage."""
    blobs_dir = dfm_dir / "objects" / "blobs"
    if not blobs_dir.exists():
        return 0

    count = 0

    # Scan all blob files recursively
    for blob_file in blobs_dir.rglob("*"):
        if not blob_file.is_file():
            continue

        hash_str = _extract_hash_from_path(blob_file, dfm_dir, "blobs")
        if not hash_str:
            continue

        # Get file size
        try:
            size = blob_file.stat().st_size
        except Exception as e:
            logger.warning(f"Failed to get size for blob {hash_str[:16]}...: {e}")
            continue

        # Try to find path from trees
        # We'll scan all trees to find which one references this blob
        path = None
        try:
            # Get all trees from database
            trees_dir = dfm_dir / "objects" / "trees"
            if trees_dir.exists():
                for tree_file in trees_dir.rglob("*"):
                    if tree_file.is_file():
                        try:
                            tree_hash = _extract_hash_from_path(tree_file, dfm_dir, "trees")
                            if not tree_hash:
                                continue
                            tree_data = storage.load_tree(tree_hash)
                            for entry in tree_data.get('entries', []):
                                if entry.get('type') == 'blob' and entry.get('hash') == hash_str:
                                    path = entry.get('path', '')
                                    break
                            if path:
                                break
                        except Exception:
                            continue
        except Exception:
            pass  # Path not critical, can be None

        # Add to database
        try:
            import time
            created_at = int(blob_file.stat().st_mtime)
            db.add_blob(hash_str, path or '', size, created_at)
            count += 1
        except Exception as e:
            logger.warning(f"Failed to add blob {hash_str[:16]}... to database: {e}")
            continue

    return count


def _rebuild_meshes(dfm_dir: Path, db: ForesterDB, storage: ObjectStorage) -> int:
    """Rebuild meshes table from storage."""
    meshes_dir = dfm_dir / "objects" / "meshes"
    if not meshes_dir.exists():
        return 0

    count = 0

    # Scan all mesh directories
    for mesh_dir in meshes_dir.rglob("*"):
        if not mesh_dir.is_dir():
            continue

        # Check if it's a valid mesh directory (has mesh.json)
        mesh_json_path = mesh_dir / "mesh.json"
        if not mesh_json_path.exists():
            continue

        hash_str = _extract_hash_from_path(mesh_dir, dfm_dir, "meshes")
        if not hash_str:
            continue

        # Get paths
        material_json_path = mesh_dir / "material.json"
        mesh_json_path_str = str(mesh_json_path.relative_to(dfm_dir))
        material_json_path_str = str(material_json_path.relative_to(dfm_dir)) if material_json_path.exists() else None

        # Try to find path from commits or trees
        path = None
        try:
            # Check commits for mesh references
            commits_dir = dfm_dir / "objects" / "commits"
            if commits_dir.exists():
                for commit_file in commits_dir.rglob("*"):
                    if commit_file.is_file():
                        try:
                            commit_hash = _extract_hash_from_path(commit_file, dfm_dir, "commits")
                            if not commit_hash:
                                continue
                            commit_data = storage.load_commit(commit_hash)
                            mesh_hashes = commit_data.get('mesh_hashes', [])
                            if hash_str in mesh_hashes:
                                # Try to get path from selected_mesh_names
                                selected_names = commit_data.get('selected_mesh_names', [])
                                if selected_names:
                                    if isinstance(selected_names, list) and selected_names:
                                        path = selected_names[0]
                                    elif isinstance(selected_names, str):
                                        path = selected_names
                                break
                        except Exception:
                            continue
        except Exception:
            pass

        # Add to database
        try:
            import time
            created_at = int(mesh_dir.stat().st_mtime)
            db.add_mesh(
                hash_str,
                path or '',
                mesh_json_path_str,
                material_json_path_str,
                created_at
            )
            count += 1
        except Exception as e:
            logger.warning(f"Failed to add mesh {hash_str[:16]}... to database: {e}")
            continue

    return count


def _rebuild_branch_refs(repo_path: Path, db: ForesterDB) -> int:
    """Rebuild branch references from refs/branches/ directory."""
    branches_dir = repo_path / ".DFM" / "refs" / "branches"
    if not branches_dir.exists():
        return 0

    count = 0

    # Branch refs are already in files, just verify they're correct
    for ref_file in branches_dir.iterdir():
        if not ref_file.is_file():
            continue

        branch_name = ref_file.name
        try:
            with open(ref_file, 'r', encoding='utf-8') as f:
                commit_hash = f.read().strip()

            if commit_hash:
                # Verify commit exists in database
                commit_info = db.get_commit(commit_hash)
                if not commit_info:
                    logger.warning(f"Branch '{branch_name}' references non-existent commit {commit_hash[:16]}...")
                else:
                    count += 1
        except Exception as e:
            logger.warning(f"Error processing branch ref {ref_file}: {e}")
            continue

    return count


def _rebuild_repository_state(repo_path: Path, db: ForesterDB) -> None:
    """Rebuild repository state (current branch and HEAD) from branch refs."""
    branches_dir = repo_path / ".DFM" / "refs" / "branches"
    if not branches_dir.exists():
        # No branches, set default
        db.set_branch_and_head("main", None)
        return

    # Try to find current branch
    # Strategy: Use the first branch found, or 'main' if it exists
    current_branch = None
    head_commit = None

    # Check if 'main' branch exists
    main_ref = branches_dir / "main"
    if main_ref.exists():
        current_branch = "main"
        try:
            with open(main_ref, 'r', encoding='utf-8') as f:
                head_commit = f.read().strip() or None
        except Exception:
            pass
    else:
        # Use first branch found
        for ref_file in branches_dir.iterdir():
            if ref_file.is_file():
                current_branch = ref_file.name
                try:
                    with open(ref_file, 'r', encoding='utf-8') as f:
                        head_commit = f.read().strip() or None
                except Exception:
                    pass
                break

    if not current_branch:
        current_branch = "main"

    db.set_branch_and_head(current_branch, head_commit)
    logger.info(f"Repository state: current_branch={current_branch}, head={head_commit[:16] if head_commit else None}...")

