"""
File locking commands for Forester.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from ..core.locking import (
    lock_file,
    unlock_file,
    is_file_locked,
    list_locks,
    check_files_locked
)
from ..core.refs import get_current_branch


def lock_files(repo_path: Path, file_paths: List[str], locked_by: str,
               lock_type: str = "exclusive", branch: Optional[str] = None,
               expires_after_seconds: Optional[int] = None) -> Dict[str, bool]:
    """
    Lock multiple files.
    
    Args:
        repo_path: Path to repository root
        file_paths: List of file paths to lock
        locked_by: Username/identifier
        lock_type: Type of lock ('exclusive', 'shared')
        branch: Branch name (optional, uses current branch if None)
        expires_after_seconds: Lock expiration time (None = never expires)
        
    Returns:
        Dictionary mapping file_path -> success (True/False)
    """
    if branch is None:
        branch = get_current_branch(repo_path)
    
    results = {}
    for file_path in file_paths:
        success = lock_file(
            repo_path, file_path, locked_by, lock_type, branch, expires_after_seconds
        )
        results[file_path] = success
    
    return results


def unlock_files(repo_path: Path, file_paths: List[str], locked_by: str,
                 branch: Optional[str] = None) -> Dict[str, bool]:
    """
    Unlock multiple files.
    
    Args:
        repo_path: Path to repository root
        file_paths: List of file paths to unlock
        locked_by: Username/identifier
        branch: Branch name (optional)
        
    Returns:
        Dictionary mapping file_path -> success (True/False)
    """
    if branch is None:
        branch = get_current_branch(repo_path)
    
    results = {}
    for file_path in file_paths:
        success = unlock_file(repo_path, file_path, locked_by, branch)
        results[file_path] = success
    
    return results


def check_commit_conflicts(repo_path: Path, file_paths: List[str],
                           locked_by: Optional[str] = None,
                           branch: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Check if any files to be committed are locked by other users.
    
    Args:
        repo_path: Path to repository root
        file_paths: List of file paths to check
        locked_by: Current user (locks by this user are ignored)
        branch: Branch name (optional)
        
    Returns:
        List of locked files with lock information
    """
    if branch is None:
        branch = get_current_branch(repo_path)
    
    return check_files_locked(repo_path, file_paths, branch, locked_by)

