"""
Hashing utilities for Forester.
Provides SHA-256 hashing functions.
"""

import hashlib
from pathlib import Path
from typing import Union


def compute_hash(data: bytes) -> str:
    """
    Compute SHA-256 hash of binary data.
    
    Args:
        data: Binary data to hash
        
    Returns:
        Hexadecimal hash string (64 characters)
    """
    return hashlib.sha256(data).hexdigest()


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hexadecimal hash string (64 characters)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    sha256 = hashlib.sha256()
    
    # Read file in chunks to handle large files efficiently
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):  # 8KB chunks
            sha256.update(chunk)
    
    return sha256.hexdigest()


def hash_to_path(hash_str: str, base_dir: Path, obj_type: str = "blobs") -> Path:
    """
    Convert hash string to storage path.
    
    Path format: objects/{obj_type}/aa/bb/ccddee...
    Uses first 2 characters for first level, next 2 for second level.
    
    Args:
        hash_str: Hexadecimal hash string (64 characters)
        base_dir: Base directory (usually .DFM/)
        obj_type: Object type (blobs, trees, commits, meshes)
        
    Returns:
        Full path to the object file/directory
        
    Raises:
        ValueError: If hash string is invalid
    """
    if len(hash_str) < 4:
        raise ValueError(f"Hash string too short: {hash_str}")
    
    # Extract first 4 characters: aa/bb
    first_level = hash_str[0:2]
    second_level = hash_str[2:4]
    rest = hash_str[4:]
    
    # Build path: objects/{obj_type}/aa/bb/{rest}
    path = base_dir / "objects" / obj_type / first_level / second_level / rest
    
    return path

