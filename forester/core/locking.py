"""
File locking module for Forester.
Prevents concurrent modifications of files.
"""

import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from .database import ForesterDB


class FileLock:
    """
    Represents a file lock.
    """
    
    def __init__(self, file_path: str, lock_type: str, locked_by: str,
                 branch: Optional[str] = None, expires_at: Optional[int] = None):
        self.file_path = file_path
        self.lock_type = lock_type
        self.locked_by = locked_by
        self.branch = branch
        self.expires_at = expires_at
    
    @property
    def is_expired(self) -> bool:
        """Check if lock is expired."""
        if self.expires_at is None:
            return False
        return int(time.time()) >= self.expires_at


def lock_file(repo_path: Path, file_path: str, locked_by: str,
              lock_type: str = "exclusive", branch: Optional[str] = None,
              expires_after_seconds: Optional[int] = None) -> bool:
    """
    Lock a file to prevent concurrent modifications.
    
    Args:
        repo_path: Path to repository root
        file_path: Path to file (relative to repo root)
        locked_by: Username/identifier
        lock_type: Type of lock ('exclusive', 'shared')
        branch: Branch name (optional)
        expires_after_seconds: Lock expiration time (None = never expires)
        
    Returns:
        True if lock acquired, False if already locked
        
    Raises:
        ValueError: If repository not initialized
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")
    
    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        return db.lock_file(file_path, lock_type, locked_by, branch, expires_after_seconds)


def unlock_file(repo_path: Path, file_path: str, locked_by: str,
                branch: Optional[str] = None) -> bool:
    """
    Unlock a file.
    
    Args:
        repo_path: Path to repository root
        file_path: Path to file
        locked_by: Username/identifier (must match lock owner)
        branch: Branch name (optional)
        
    Returns:
        True if unlocked, False if not locked or not owned
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return False
    
    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        return db.unlock_file(file_path, locked_by, branch)


def is_file_locked(repo_path: Path, file_path: str,
                   branch: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Check if file is locked.
    
    Args:
        repo_path: Path to repository root
        file_path: Path to file
        branch: Branch name (optional)
        
    Returns:
        Lock information dict or None if not locked
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return None
    
    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        return db.is_file_locked(file_path, branch)


def list_locks(repo_path: Path, branch: Optional[str] = None,
               locked_by: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all active locks.
    
    Args:
        repo_path: Path to repository root
        branch: Filter by branch (optional)
        locked_by: Filter by user (optional)
        
    Returns:
        List of lock dictionaries
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return []
    
    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        # Clean up expired locks first
        db.cleanup_expired_locks()
        return db.list_locks(branch, locked_by)


def check_files_locked(repo_path: Path, file_paths: List[str],
                       branch: Optional[str] = None,
                       locked_by: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Check which files from list are locked.
    
    Args:
        repo_path: Path to repository root
        file_paths: List of file paths to check
        branch: Branch name (optional)
        locked_by: If provided, only return locks not owned by this user
        
    Returns:
        List of locked files with lock information
    """
    locked_files = []
    
    for file_path in file_paths:
        lock_info = is_file_locked(repo_path, file_path, branch)
        if lock_info:
            # If locked_by is provided, skip locks owned by that user
            if locked_by and lock_info.get('locked_by') == locked_by:
                continue
            locked_files.append({
                'file_path': file_path,
                **lock_info
            })
    
    return locked_files

