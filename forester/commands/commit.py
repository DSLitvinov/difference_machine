"""
Commit command for Forester.
Creates a new commit from current working directory state.
"""

import logging
from pathlib import Path
from typing import Optional, List
from ..core.database import ForesterDB
from ..core.ignore import IgnoreRules
from ..core.storage import ObjectStorage
from ..core.refs import get_current_branch, get_current_head_commit, set_branch_ref
from ..models.tree import Tree
from ..models.commit import Commit
from ..models.mesh import Mesh
from ..utils.filesystem import scan_directory
from .locking import check_commit_conflicts

logger = logging.getLogger(__name__)


def create_commit(repo_path: Path, message: str, author: str = "Unknown",
                  check_locks: bool = True, screenshot_hash: Optional[str] = None) -> Optional[str]:
    """
    Create a new commit from current working directory.

    Args:
        repo_path: Path to repository root
        message: Commit message
        author: Author name
        check_locks: If True, check for file locks before committing
        screenshot_hash: Optional screenshot blob hash

    Returns:
        Commit hash if successful, None otherwise

    Raises:
        ValueError: If repository is not initialized, no changes detected, or files are locked
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")

    # Get current branch
    branch = get_current_branch(repo_path)
    if not branch:
        raise ValueError("No current branch set")

    # Get parent commit
    parent_hash = get_current_head_commit(repo_path)

    # Initialize components
    db_path = dfm_dir / "forester.db"

    with ForesterDB(db_path) as db:
        storage = ObjectStorage(dfm_dir)
        ignore_file = dfm_dir / ".dfmignore"
        ignore_rules = IgnoreRules(ignore_file)

        # Step 1: Scan working directory (excluding meshes/)
        working_dir = repo_path / "working"
        if not working_dir.exists():
            working_dir = repo_path  # Fallback to repo root

        # Use extended ignore rules that also exclude meshes/
        from ..core.ignore_extended import ExtendedIgnoreRules
        extended_ignore = ExtendedIgnoreRules(ignore_file)

        # Scan files (excluding meshes/)
        files = scan_directory(working_dir, extended_ignore, working_dir)

        # Step 2: Process files and create blobs
        from ..models.blob import Blob

        tree_entries = []
        for file_path in files:
            try:
                # Get relative path
                rel_path = file_path.relative_to(working_dir)

                # Create blob from file
                blob = Blob.from_file(file_path, dfm_dir, db, storage)

                # Add to tree entries
                from ..models.tree import TreeEntry
                entry = TreeEntry(
                    path=str(rel_path),
                    type="blob",
                    hash=blob.hash,
                    size=blob.size
                )
                tree_entries.append(entry)
            except (OSError, ValueError, PermissionError) as e:
                # Skip files that can't be processed
                logger.warning(f"Skipping file {file_path}: {e}")
                continue
            except Exception as e:
                # Unexpected error - log and continue
                logger.error(f"Unexpected error processing file {file_path}: {e}", exc_info=True)
                continue

        # Step 3: Scan meshes directory
        meshes_dir = working_dir / "meshes"
        mesh_hashes = []

        if meshes_dir.exists() and meshes_dir.is_dir():
            # Find all mesh directories
            for mesh_dir in meshes_dir.iterdir():
                if not mesh_dir.is_dir():
                    continue

                # Check if it's a valid mesh directory (has mesh.json)
                mesh_json_path = mesh_dir / "mesh.json"
                if not mesh_json_path.exists():
                    continue

                try:
                    # Create mesh from directory
                    material_json_path = mesh_dir / "material.json"
                    if not material_json_path.exists():
                        # Create empty material.json if it doesn't exist
                        material_json_path.write_text("{}")

                    mesh = Mesh.from_directory(mesh_dir, dfm_dir, db, storage)
                    if mesh:
                        mesh_hashes.append(mesh.hash)
                except (OSError, ValueError, PermissionError) as e:
                    # Skip meshes that can't be processed
                    logger.warning(f"Skipping mesh {mesh_dir}: {e}")
                    continue
                except Exception as e:
                    # Unexpected error - log and continue
                    logger.error(f"Unexpected error processing mesh {mesh_dir}: {e}", exc_info=True)
                    continue

        # Step 4: Create tree object
        from ..models.tree import Tree
        tree = Tree(hash="", entries=tree_entries)
        tree.hash = tree.compute_hash()

        # Check if tree already exists (no changes)
        if db.tree_exists(tree.hash):
            # Check if this would be the same as parent commit
            if parent_hash:
                parent_commit = Commit.from_storage(parent_hash, db, storage)
                if parent_commit and parent_commit.tree_hash == tree.hash:
                    # No changes detected
                    return None

        # Save tree
        tree.save_to_storage(db, storage)

        # Collect file paths for lock checking
        file_paths_to_check = [entry.path for entry in tree_entries]

        # Check for file locks before committing
        if check_locks and file_paths_to_check:
            locked_files = check_commit_conflicts(
                repo_path, file_paths_to_check, author, branch
            )
            if locked_files:
                locked_paths = [f['file_path'] for f in locked_files]
                locked_by = locked_files[0].get('locked_by', 'unknown')
                max_files_to_display = 5
                displayed_paths = locked_paths[:max_files_to_display]
                error_msg = (
                    f"Files are locked by '{locked_by}': "
                    f"{', '.join(displayed_paths)}"
                )
                if len(locked_paths) > max_files_to_display:
                    error_msg += (
                        f" and {len(locked_paths) - max_files_to_display} more"
                    )
                raise ValueError(error_msg)

        # Step 5: Create commit object
        commit = Commit.create(
            tree=tree,
            branch=branch,
            message=message,
            author=author,
            parent_hash=parent_hash,
            mesh_hashes=mesh_hashes,
            screenshot_hash=screenshot_hash
        )

        # Save commit
        commit.save_to_storage(db, storage)

        # Step 6: Update branch reference
        set_branch_ref(repo_path, branch, commit.hash)

        # Step 7: Update HEAD in database
        db.set_head(commit.hash)

        return commit.hash


def has_uncommitted_changes(repo_path: Path) -> bool:
    """
    Check if there are uncommitted changes in working directory.

    Args:
        repo_path: Path to repository root

    Returns:
        True if there are uncommitted changes
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return False

    # Get current commit
    current_commit_hash = get_current_head_commit(repo_path)
    if not current_commit_hash:
        # No commits yet, check if there are any files
        working_dir = repo_path / "working"
        if not working_dir.exists():
            working_dir = repo_path

        ignore_file = dfm_dir / ".dfmignore"
        ignore_rules = IgnoreRules(ignore_file)
        files = scan_directory(working_dir, ignore_rules, working_dir)
        return len(files) > 0

    # Compare current state with last commit
    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        storage = ObjectStorage(dfm_dir)

        # Load last commit
        commit = Commit.from_storage(current_commit_hash, db, storage)
        if not commit:
            return True

        # Get tree from commit
        tree = commit.get_tree(db, storage)
        if not tree:
            return True

        # Get current tree
        ignore_file = dfm_dir / ".dfmignore"
        ignore_rules = IgnoreRules(ignore_file)

        working_dir = repo_path / "working"
        if not working_dir.exists():
            working_dir = repo_path

        current_tree = Tree.from_directory(working_dir, working_dir, ignore_rules, db, storage)

        # Compare hashes
        return current_tree.hash != tree.hash


def get_commit_screenshot(repo_path: Path, commit_hash: str) -> Optional[bytes]:
    """
    Get screenshot image data for a commit.

    Args:
        repo_path: Path to repository root
        commit_hash: Hash of the commit

    Returns:
        PNG image data as bytes, or None if screenshot not found
    """
    from ..core.database import ForesterDB
    from ..core.storage import ObjectStorage
    from ..models.commit import Commit
    from ..models.blob import Blob

    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return None

    db_path = dfm_dir / "forester.db"
    if not db_path.exists():
        return None

    try:
        with ForesterDB(db_path) as db:
            storage = ObjectStorage(dfm_dir)
            commit = Commit.from_storage(commit_hash, db, storage)

            if not commit or not commit.screenshot_hash:
                return None

            blob = Blob.from_storage(commit.screenshot_hash, db, storage)
            if not blob:
                return None

            # Load blob data
            screenshot_data = blob.load_data(storage)
            return screenshot_data

    except Exception:
        return None


def get_commit_screenshot(repo_path: Path, commit_hash: str) -> Optional[bytes]:
    """
    Get screenshot image data for a commit.

    Args:
        repo_path: Path to repository root
        commit_hash: Hash of the commit

    Returns:
        PNG image data as bytes, or None if screenshot not found
    """
    from ..core.database import ForesterDB
    from ..core.storage import ObjectStorage
    from ..models.commit import Commit
    from ..models.blob import Blob

    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return None

    db_path = dfm_dir / "forester.db"
    if not db_path.exists():
        return None

    try:
        with ForesterDB(db_path) as db:
            storage = ObjectStorage(dfm_dir)
            commit = Commit.from_storage(commit_hash, db, storage)

            if not commit or not commit.screenshot_hash:
                return None

            blob = Blob.from_storage(commit.screenshot_hash, db, storage)
            if not blob:
                return None

            # Load blob data
            screenshot_data = blob.load_data(storage)
            return screenshot_data

    except Exception:
        return None




