"""
Core modules for Forester.
"""

from .hashing import compute_hash, compute_file_hash, hash_to_path
from .database import ForesterDB
from .ignore import IgnoreRules
from .storage import ObjectStorage
from .metadata import Metadata
from .locking import FileLock, lock_file, unlock_file, is_file_locked, list_locks, check_files_locked

__all__ = [
    "compute_hash",
    "compute_file_hash", 
    "hash_to_path",
    "ForesterDB",
    "IgnoreRules",
    "ObjectStorage",
    "Metadata",
    "FileLock",
    "lock_file",
    "unlock_file",
    "is_file_locked",
    "list_locks",
    "check_files_locked",
]

