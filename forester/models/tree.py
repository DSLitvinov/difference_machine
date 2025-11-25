"""
Tree model for Forester.
Represents a directory structure in the repository.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from ..core.hashing import compute_hash
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage


@dataclass
class TreeEntry:
    """
    Represents a single entry in a tree (file or subdirectory).
    """
    path: str
    type: str  # "blob" or "tree"
    hash: str
    size: int = 0
    
    def to_dict(self) -> dict:
        """Convert entry to dictionary."""
        return {
            "path": self.path,
            "type": self.type,
            "hash": self.hash,
            "size": self.size
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TreeEntry':
        """Create entry from dictionary."""
        return cls(
            path=data['path'],
            type=data['type'],
            hash=data['hash'],
            size=data.get('size', 0)
        )


class Tree:
    """
    Represents a tree (directory structure) in Forester repository.
    """
    
    def __init__(self, hash: str, entries: List[TreeEntry]):
        """
        Initialize tree.
        
        Args:
            hash: SHA-256 hash of the tree
            entries: List of tree entries
        """
        self.hash = hash
        self.entries = entries
    
    def add_entry(self, entry: TreeEntry) -> None:
        """
        Add entry to tree.
        
        Args:
            entry: Tree entry to add
        """
        self.entries.append(entry)
    
    def compute_hash(self) -> str:
        """
        Compute hash of the tree based on its entries.
        
        Returns:
            SHA-256 hash string
        """
        # Sort entries by path for consistent hashing
        sorted_entries = sorted(self.entries, key=lambda e: e.path)
        entries_data = [entry.to_dict() for entry in sorted_entries]
        entries_json = json.dumps(entries_data, sort_keys=True)
        return compute_hash(entries_json.encode('utf-8'))
    
    def to_dict(self) -> dict:
        """
        Convert tree to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "hash": self.hash,
            "entries": [entry.to_dict() for entry in self.entries]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Tree':
        """
        Create tree from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Tree instance
        """
        entries = [TreeEntry.from_dict(e) for e in data.get('entries', [])]
        return cls(
            hash=data.get('hash', ''),
            entries=entries
        )
    
    def save_to_storage(self, db: ForesterDB, storage: ObjectStorage) -> None:
        """
        Save tree to storage and database.
        
        Args:
            db: Database connection
            storage: Object storage
        """
        # Compute hash if not set
        if not self.hash:
            self.hash = self.compute_hash()
        
        # Save to storage
        tree_data = self.to_dict()
        storage.save_tree(tree_data, self.hash)
        
        # Save to database
        entries_list = [entry.to_dict() for entry in self.entries]
        db.add_tree(self.hash, entries_list)
    
    @classmethod
    def from_storage(cls, tree_hash: str, db: ForesterDB, 
                     storage: ObjectStorage) -> Optional['Tree']:
        """
        Load tree from storage.
        
        Args:
            tree_hash: SHA-256 hash of the tree
            db: Database connection
            storage: Object storage
            
        Returns:
            Tree instance or None if not found
        """
        # Try to load from database first
        entries_list = db.get_tree(tree_hash)
        if entries_list is None:
            # Try to load from storage
            try:
                tree_data = storage.load_tree(tree_hash)
                entries_list = tree_data.get('entries', [])
            except FileNotFoundError:
                return None
        
        entries = [TreeEntry.from_dict(e) for e in entries_list]
        return cls(hash=tree_hash, entries=entries)
    
    @classmethod
    def from_directory(cls, directory: Path, base_dir: Path, ignore_rules,
                       db: ForesterDB, storage: ObjectStorage) -> 'Tree':
        """
        Create tree from directory structure.
        
        Args:
            directory: Directory to scan
            base_dir: Base directory of repository
            ignore_rules: IgnoreRules instance
            db: Database connection
            storage: Object storage
            
        Returns:
            Tree instance
        """
        from ..utils.filesystem import scan_directory
        from ..models.blob import Blob
        
        entries: List[TreeEntry] = []
        
        # Scan directory for files
        files = scan_directory(directory, ignore_rules, base_dir)
        
        for file_path in files:
            # Get relative path
            try:
                rel_path = file_path.relative_to(base_dir)
            except ValueError:
                continue
            
            # Create blob from file
            blob = Blob.from_file(file_path, base_dir, db, storage)
            
            # Add entry
            entry = TreeEntry(
                path=str(rel_path),
                type="blob",
                hash=blob.hash,
                size=blob.size
            )
            entries.append(entry)
        
        # Create tree
        tree = cls(hash="", entries=entries)
        tree.hash = tree.compute_hash()
        
        return tree

