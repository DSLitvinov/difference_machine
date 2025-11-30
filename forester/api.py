"""
Public Python API for Forester.
Provides high-level functions for automation and scripting.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from .commands import (
    init_repository,
    find_repository,
    is_repository,
    create_commit,
    has_uncommitted_changes,
    create_branch,
    list_branches,
    get_branch_commits,
    switch_branch,
    delete_branch,
    checkout,
    checkout_branch,
    checkout_commit,
    create_stash,
    list_stashes,
    apply_stash,
    delete_stash,
    get_commit_screenshot,
    delete_commit,
    rebuild_database,
    garbage_collect,
)
from .commands.locking import (
    lock_file,
    unlock_file,
    is_file_locked,
    list_locks,
    lock_files,
    unlock_files,
    check_commit_conflicts,
)
from .core.database import ForesterDB
from .core.storage import ObjectStorage
from .models.commit import Commit


# ========== Repository Management ==========

def init_repo(path: Path, force: bool = False) -> bool:
    """
    Initialize a new Forester repository.
    
    Args:
        path: Path to project directory
        force: Reinitialize even if repository exists
        
    Returns:
        True if successful
        
    Example:
        >>> from forester.api import init_repo
        >>> from pathlib import Path
        >>> init_repo(Path("/path/to/project"))
    """
    return init_repository(path, force)


def find_repo(path: Path) -> Optional[Path]:
    """
    Find repository root from given path.
    
    Args:
        path: Starting path
        
    Returns:
        Repository root path or None
        
    Example:
        >>> repo_path = find_repo(Path.cwd())
        >>> if repo_path:
        ...     print(f"Repository found at {repo_path}")
    """
    return find_repository(path)


# ========== Commits ==========

def commit(path: Path, message: str, author: str = "Unknown",
           check_locks: bool = True) -> Optional[str]:
    """
    Create a new commit.
    
    Args:
        path: Repository path
        message: Commit message
        author: Author name
        check_locks: Check for file locks before committing
        
    Returns:
        Commit hash or None if no changes
        
    Example:
        >>> commit_hash = commit(repo_path, "Added new mesh", "John Doe")
        >>> if commit_hash:
        ...     print(f"Committed: {commit_hash[:16]}")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return create_commit(repo_path, message, author, check_locks)


def has_changes(path: Path) -> bool:
    """
    Check if there are uncommitted changes.
    
    Args:
        path: Repository path
        
    Returns:
        True if there are uncommitted changes
        
    Example:
        >>> if has_changes(repo_path):
        ...     print("You have uncommitted changes")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return False
    
    return has_uncommitted_changes(repo_path)


def get_commit_info(path: Path, commit_hash: str) -> Optional[Dict[str, Any]]:
    """
    Get commit information.
    
    Args:
        path: Repository path
        commit_hash: Commit hash
        
    Returns:
        Commit information dictionary or None
        
    Example:
        >>> info = get_commit_info(repo_path, "abc123...")
        >>> if info:
        ...     print(f"Author: {info['author']}, Message: {info['message']}")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return None
    
    dfm_dir = repo_path / ".DFM"
    db_path = dfm_dir / "forester.db"
    
    if not db_path.exists():
        return None
    
    with ForesterDB(db_path) as db:
        commit_data = db.get_commit(commit_hash)
        if not commit_data:
            return None
        
        return {
            'hash': commit_data['hash'],
            'author': commit_data.get('author', 'Unknown'),
            'message': commit_data.get('message', ''),
            'timestamp': commit_data.get('timestamp', 0),
            'branch': commit_data.get('branch', 'main'),
            'commit_type': commit_data.get('commit_type', 'project'),
            'screenshot_hash': commit_data.get('screenshot_hash'),
        }


def get_screenshot(path: Path, commit_hash: str) -> Optional[bytes]:
    """
    Get screenshot image data for a commit.
    
    Args:
        path: Repository path
        commit_hash: Commit hash
        
    Returns:
        PNG image data as bytes or None
        
    Example:
        >>> screenshot_data = get_screenshot(repo_path, "abc123...")
        >>> if screenshot_data:
        ...     with open("screenshot.png", "wb") as f:
        ...         f.write(screenshot_data)
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return None
    
    return get_commit_screenshot(repo_path, commit_hash)


# ========== Branches ==========

def create_branch_repo(path: Path, branch_name: str, 
                       from_branch: Optional[str] = None) -> bool:
    """
    Create a new branch.
    
    Args:
        path: Repository path
        branch_name: Branch name
        from_branch: Source branch (None = current branch)
        
    Returns:
        True if successful
        
    Example:
        >>> create_branch_repo(repo_path, "feature/new-mesh")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return create_branch(repo_path, branch_name, from_branch)


def get_branches(path: Path) -> List[Dict[str, Any]]:
    """
    List all branches.
    
    Args:
        path: Repository path
        
    Returns:
        List of branch information dictionaries
        
    Example:
        >>> branches = get_branches(repo_path)
        >>> for branch in branches:
        ...     print(f"{branch['name']}: {branch['commit_count']} commits")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return []
    
    return list_branches(repo_path)


def switch_to_branch(path: Path, branch_name: str) -> bool:
    """
    Switch to a branch.
    
    Args:
        path: Repository path
        branch_name: Branch name
        
    Returns:
        True if successful
        
    Example:
        >>> switch_to_branch(repo_path, "feature/new-mesh")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return switch_branch(repo_path, branch_name)


# ========== Checkout ==========

def checkout_files(path: Path, target: str, force: bool = False,
                   file_patterns: Optional[List[str]] = None,
                   mesh_names: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """
    Checkout files from a commit or branch (with selective checkout).
    
    Args:
        path: Repository path
        target: Branch name or commit hash
        force: Discard uncommitted changes
        file_patterns: File path patterns to selectively checkout (e.g., ["textures/*"])
        mesh_names: Mesh names to selectively checkout (for mesh_only commits)
        
    Returns:
        Tuple of (success, error_message)
        
    Example:
        >>> # Checkout only texture files
        >>> success, error = checkout_files(repo_path, "main", 
        ...                                 file_patterns=["textures/*.png"])
        >>> 
        >>> # Checkout specific meshes
        >>> success, error = checkout_files(repo_path, "abc123...",
        ...                                 mesh_names=["Mesh1", "Mesh2"])
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return (False, "Not a Forester repository")
    
    return checkout(repo_path, target, force, file_patterns, mesh_names)


# ========== File Locking ==========

def lock_files_api(path: Path, file_paths: List[str], locked_by: str,
                   lock_type: str = "exclusive", branch: Optional[str] = None,
                   expires_after_seconds: Optional[int] = None) -> Dict[str, bool]:
    """
    Lock multiple files.
    
    Args:
        path: Repository path
        file_paths: List of file paths to lock
        locked_by: Username/identifier
        lock_type: Type of lock ('exclusive', 'shared')
        branch: Branch name (None = current branch)
        expires_after_seconds: Lock expiration time (None = never)
        
    Returns:
        Dictionary mapping file_path -> success
        
    Example:
        >>> results = lock_files_api(repo_path, 
        ...                          ["meshes/model1.json", "textures/tex1.png"],
        ...                          "john_doe",
        ...                          expires_after_seconds=3600)
        >>> for file_path, success in results.items():
        ...     print(f"{file_path}: {'locked' if success else 'failed'}")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return lock_files(repo_path, file_paths, locked_by, lock_type, branch, expires_after_seconds)


def unlock_files_api(path: Path, file_paths: List[str], locked_by: str,
                     branch: Optional[str] = None) -> Dict[str, bool]:
    """
    Unlock multiple files.
    
    Args:
        path: Repository path
        file_paths: List of file paths to unlock
        locked_by: Username/identifier
        branch: Branch name (None = current branch)
        
    Returns:
        Dictionary mapping file_path -> success
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return unlock_files(repo_path, file_paths, locked_by, branch)


def get_locks(path: Path, branch: Optional[str] = None,
              locked_by: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all active locks.
    
    Args:
        path: Repository path
        branch: Filter by branch (optional)
        locked_by: Filter by user (optional)
        
    Returns:
        List of lock dictionaries
        
    Example:
        >>> locks = get_locks(repo_path, branch="main")
        >>> for lock in locks:
        ...     print(f"{lock['file_path']} locked by {lock['locked_by']}")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return []
    
    return list_locks(repo_path, branch, locked_by)


# ========== Stash ==========

def stash_changes(path: Path, message: Optional[str] = None) -> Optional[str]:
    """
    Create a stash from current working directory.
    
    Args:
        path: Repository path
        message: Stash message
        
    Returns:
        Stash hash or None if no changes
        
    Example:
        >>> stash_hash = stash_changes(repo_path, "WIP: new feature")
        >>> if stash_hash:
        ...     print(f"Stashed: {stash_hash[:16]}")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return create_stash(repo_path, message)


def get_stashes(path: Path) -> List[Dict[str, Any]]:
    """
    List all stashes.
    
    Args:
        path: Repository path
        
    Returns:
        List of stash dictionaries
        
    Example:
        >>> stashes = get_stashes(repo_path)
        >>> for stash in stashes:
        ...     print(f"{stash['hash'][:16]}: {stash['message']}")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return []
    
    return list_stashes(repo_path)


def apply_stash_api(path: Path, stash_hash: str, force: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Apply a stash.
    
    Args:
        path: Repository path
        stash_hash: Stash hash
        force: Discard uncommitted changes
        
    Returns:
        Tuple of (success, error_message)
        
    Example:
        >>> success, error = apply_stash_api(repo_path, "abc123...")
        >>> if success:
        ...     print("Stash applied")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return (False, "Not a Forester repository")
    
    return apply_stash(repo_path, stash_hash, force)


# ========== Review Tools ==========

def comment_on_asset(path: Path, asset_hash: str, asset_type: str,
                     author: str, text: str, x: Optional[float] = None,
                     y: Optional[float] = None) -> int:
    """
    Add comment to asset (mesh, blob, commit).
    
    Args:
        path: Repository path
        asset_hash: Hash of the asset
        asset_type: Type ('mesh', 'blob', 'commit')
        author: Author name
        text: Comment text
        x: X coordinate for annotation (optional)
        y: Y coordinate for annotation (optional)
        
    Returns:
        Comment ID
        
    Example:
        >>> comment_id = comment_on_asset(repo_path, "abc123...", "mesh",
        ...                               "John Doe", "This mesh needs fixing")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return add_comment(repo_path, asset_hash, asset_type, author, text, x, y)


def get_asset_comments(path: Path, asset_hash: str, asset_type: str,
                       include_resolved: bool = False) -> List[Dict[str, Any]]:
    """
    Get comments for asset.
    
    Args:
        path: Repository path
        asset_hash: Hash of the asset
        asset_type: Type ('mesh', 'blob', 'commit')
        include_resolved: Include resolved comments
        
    Returns:
        List of comment dictionaries
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return []
    
    return get_comments(repo_path, asset_hash, asset_type, include_resolved)


def approve_asset(path: Path, asset_hash: str, asset_type: str,
                  approver: str, status: str = "approved",
                  comment: Optional[str] = None) -> bool:
    """
    Set approval status for asset.
    
    Args:
        path: Repository path
        asset_hash: Hash of the asset
        asset_type: Type ('mesh', 'blob', 'commit')
        approver: Approver name
        status: Status ('pending', 'approved', 'rejected')
        comment: Optional comment
        
    Returns:
        True if successful
        
    Example:
        >>> approve_asset(repo_path, "abc123...", "mesh", "John Doe",
        ...               "approved", "Looks good!")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return set_approval(repo_path, asset_hash, asset_type, approver, status, comment)


def get_asset_approvals(path: Path, asset_hash: str, asset_type: str) -> List[Dict[str, Any]]:
    """
    Get all approvals for asset.
    
    Args:
        path: Repository path
        asset_hash: Hash of the asset
        asset_type: Type ('mesh', 'blob', 'commit')
        
    Returns:
        List of approval dictionaries
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return []
    
    return get_all_approvals(repo_path, asset_hash, asset_type)


# ========== Repository Management (дополнения) ==========

def is_repo(path: Path) -> bool:
    """
    Check if path is a Forester repository.
    
    Args:
        path: Path to check
        
    Returns:
        True if path contains .DFM/ directory with forester.db
        
    Example:
        >>> if is_repo(Path("/path/to/project")):
        ...     print("This is a Forester repository")
    """
    return is_repository(path)


# ========== Branches (дополнения) ==========

def delete_branch_repo(path: Path, branch_name: str, force: bool = False) -> bool:
    """
    Delete a branch.
    
    Args:
        path: Repository path
        branch_name: Branch name to delete
        force: Force deletion even if it's the current branch
        
    Returns:
        True if successful
        
    Raises:
        ValueError: If branch doesn't exist or is current branch (unless force=True)
        
    Example:
        >>> delete_branch_repo(repo_path, "old-feature")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return delete_branch(repo_path, branch_name, force)


def get_branch_commits_api(path: Path, branch_name: str) -> List[Dict[str, Any]]:
    """
    Get all commits in a branch.
    
    Args:
        path: Repository path
        branch_name: Name of branch
        
    Returns:
        List of commit dictionaries, ordered from oldest to newest
        
    Example:
        >>> commits = get_branch_commits_api(repo_path, "main")
        >>> for commit in commits:
        ...     print(f"{commit['hash'][:16]}: {commit['message']}")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return []
    
    return get_branch_commits(repo_path, branch_name)


# ========== Commits (дополнения) ==========

def delete_commit_api(path: Path, commit_hash: str, force: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Delete a commit.
    
    Args:
        path: Repository path
        commit_hash: Commit hash to delete
        force: Force deletion even if commit is referenced by branches
        
    Returns:
        Tuple of (success, error_message)
        
    Example:
        >>> success, error = delete_commit_api(repo_path, "abc123...")
        >>> if success:
        ...     print("Commit deleted")
        >>> else:
        ...     print(f"Error: {error}")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return (False, "Not a Forester repository")
    
    return delete_commit(repo_path, commit_hash, force)


# ========== Stash (дополнения) ==========

def delete_stash_api(path: Path, stash_hash: str) -> bool:
    """
    Delete a stash.
    
    Args:
        path: Repository path
        stash_hash: Stash hash to delete
        
    Returns:
        True if successful
        
    Raises:
        ValueError: If stash doesn't exist
        
    Example:
        >>> delete_stash_api(repo_path, "abc123...")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return delete_stash(repo_path, stash_hash)


# ========== File Locking (дополнения) ==========

def lock_file_api(path: Path, file_path: str, locked_by: str,
                  lock_type: str = "exclusive", branch: Optional[str] = None,
                  expires_after_seconds: Optional[int] = None) -> bool:
    """
    Lock a single file.
    
    Args:
        path: Repository path
        file_path: Path to file to lock
        locked_by: Username/identifier
        lock_type: Type of lock ('exclusive', 'shared')
        branch: Branch name (None = current branch)
        expires_after_seconds: Lock expiration time (None = never)
        
    Returns:
        True if locked, False if already locked
        
    Example:
        >>> if lock_file_api(repo_path, "meshes/model.json", "john"):
        ...     print("File locked successfully")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        raise ValueError(f"Not a Forester repository: {path}")
    
    return lock_file(repo_path, file_path, locked_by, lock_type, branch, expires_after_seconds)


def unlock_file_api(path: Path, file_path: str, locked_by: str,
                    branch: Optional[str] = None) -> bool:
    """
    Unlock a single file.
    
    Args:
        path: Repository path
        file_path: Path to file to unlock
        locked_by: Username/identifier (must match lock owner)
        branch: Branch name (None = current branch)
        
    Returns:
        True if unlocked, False if not locked or not owned
        
    Example:
        >>> unlock_file_api(repo_path, "meshes/model.json", "john")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return False
    
    return unlock_file(repo_path, file_path, locked_by, branch)


def check_file_locked(path: Path, file_path: str,
                      branch: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Check if a single file is locked.
    
    Args:
        path: Repository path
        file_path: Path to file to check
        branch: Branch name (None = current branch)
        
    Returns:
        Lock information dict or None if not locked
        
    Example:
        >>> lock_info = check_file_locked(repo_path, "meshes/model.json")
        >>> if lock_info:
        ...     print(f"Locked by {lock_info['locked_by']}")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return None
    
    return is_file_locked(repo_path, file_path, branch)


def check_conflicts(path: Path, file_paths: List[str],
                    locked_by: Optional[str] = None,
                    branch: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Check if files are locked by other users (for commit conflicts).
    
    Args:
        path: Repository path
        file_paths: List of file paths to check
        locked_by: Current user (locks by this user are ignored)
        branch: Branch name (None = current branch)
        
    Returns:
        List of locked files with lock information
        
    Example:
        >>> conflicts = check_conflicts(repo_path, ["file1.json", "file2.json"], "john")
        >>> if conflicts:
        ...     print(f"{len(conflicts)} files are locked")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return []
    
    return check_commit_conflicts(repo_path, file_paths, locked_by, branch)


# ========== Review Tools (дополнения) ==========

def resolve_comment_api(path: Path, comment_id: int) -> bool:
    """
    Mark comment as resolved.
    
    Args:
        path: Repository path
        comment_id: Comment ID to resolve
        
    Returns:
        True if successful
        
    Example:
        >>> resolve_comment_api(repo_path, 123)
    """
    from .commands.review import resolve_comment
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return False
    
    return resolve_comment(repo_path, comment_id)


def delete_comment_api(path: Path, comment_id: int) -> bool:
    """
    Delete a comment.
    
    Args:
        path: Repository path
        comment_id: Comment ID to delete
        
    Returns:
        True if successful
        
    Example:
        >>> delete_comment_api(repo_path, 123)
    """
    from .commands.review import delete_comment
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return False
    
    return delete_comment(repo_path, comment_id)


def get_approval_status(path: Path, asset_hash: str, asset_type: str,
                        approver: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get approval status from a specific approver.
    
    Args:
        path: Repository path
        asset_hash: Hash of the asset
        asset_type: Type ('mesh', 'blob', 'commit')
        approver: Filter by approver (None = get latest)
        
    Returns:
        Approval dictionary or None
        
    Example:
        >>> approval = get_approval_status(repo_path, "abc123...", "mesh", "Reviewer1")
        >>> if approval:
        ...     print(f"Status: {approval['status']}")
    """
    from .commands.review import get_approval
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return None
    
    return get_approval(repo_path, asset_hash, asset_type, approver)


# ========== Maintenance & Utilities ==========

def rebuild_db(path: Path, backup: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Rebuild database from file system storage.
    
    Useful for recovering from database corruption.
    
    Args:
        path: Repository path
        backup: Create backup of existing database before rebuilding
        
    Returns:
        Tuple of (success, error_message)
        
    Example:
        >>> success, error = rebuild_db(repo_path, backup=True)
        >>> if success:
        ...     print("Database rebuilt successfully")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return (False, "Not a Forester repository")
    
    return rebuild_database(repo_path, backup)


def garbage_collect_api(path: Path, dry_run: bool = False) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Remove unused objects from storage.
    
    Scans for objects (blobs, trees, commits, meshes) that are not
    referenced by any commits and removes them.
    
    Args:
        path: Repository path
        dry_run: If True, only report what would be deleted without actually deleting
        
    Returns:
        Tuple of (success, error_message, statistics_dict)
        Statistics dictionary contains:
        {
            'commits_deleted': int,
            'trees_deleted': int,
            'blobs_deleted': int,
            'meshes_deleted': int,
            'commits_kept': int,
            'trees_kept': int,
            'blobs_kept': int,
            'meshes_kept': int
        }
        
    Example:
        >>> success, error, stats = garbage_collect_api(repo_path, dry_run=True)
        >>> if success:
        ...     print(f"Would delete {stats['blobs_deleted']} blobs")
        >>> 
        >>> # Actually perform garbage collection
        >>> success, error, stats = garbage_collect_api(repo_path, dry_run=False)
        >>> if success:
        ...     print(f"Deleted {stats['blobs_deleted']} blobs")
    """
    repo_path = find_repository(path) if not (path / ".DFM").exists() else path
    if not repo_path:
        return (False, "Not a Forester repository", {})
    
    return garbage_collect(repo_path, dry_run)

