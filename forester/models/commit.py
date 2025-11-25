"""
Commit model for Forester.
Represents a commit in the repository.
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from ..core.hashing import compute_hash
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage
from .tree import Tree


class Commit:
    """
    Represents a commit in Forester repository.
    """
    
    def __init__(self, hash: str, parent_hash: Optional[str], tree_hash: str,
                 branch: str, timestamp: int, message: str, author: str,
                 mesh_hashes: Optional[List[str]] = None,
                 commit_type: str = "project",
                 selected_mesh_names: Optional[List[str]] = None,
                 export_options: Optional[Dict[str, bool]] = None):
        """
        Initialize commit.
        
        Args:
            hash: SHA-256 hash of the commit
            parent_hash: Hash of parent commit (None for first commit)
            tree_hash: Hash of the tree object
            branch: Branch name
            timestamp: Commit timestamp
            message: Commit message
            author: Author name
            mesh_hashes: List of mesh hashes (optional)
            commit_type: Type of commit ("project" or "mesh_only")
            selected_mesh_names: List of selected mesh names (for mesh_only commits)
            export_options: Export options dict (for mesh_only commits)
        """
        self.hash = hash
        self.parent_hash = parent_hash
        self.tree_hash = tree_hash
        self.branch = branch
        self.timestamp = timestamp
        self.message = message
        self.author = author
        self.mesh_hashes = mesh_hashes or []
        self.commit_type = commit_type
        self.selected_mesh_names = selected_mesh_names or []
        self.export_options = export_options or {}
    
    def compute_hash(self) -> str:
        """
        Compute hash of the commit.
        
        Hash is computed from: commit_type + parent_hash + tree_hash + timestamp + message + mesh_hashes + export_options
        
        Returns:
            SHA-256 hash string
        """
        parent_str = self.parent_hash or ""
        mesh_str = json.dumps(sorted(self.mesh_hashes), sort_keys=True) if self.mesh_hashes else ""
        mesh_names_str = json.dumps(sorted(self.selected_mesh_names), sort_keys=True) if self.selected_mesh_names else ""
        export_opts_str = json.dumps(self.export_options, sort_keys=True) if self.export_options else ""
        
        commit_data = f"{self.commit_type}{parent_str}{self.tree_hash}{self.timestamp}{self.message}{mesh_str}{mesh_names_str}{export_opts_str}"
        return compute_hash(commit_data.encode('utf-8'))
    
    def to_dict(self) -> dict:
        """
        Convert commit to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "hash": self.hash,
            "parent_hash": self.parent_hash,
            "tree_hash": self.tree_hash,
            "branch": self.branch,
            "timestamp": self.timestamp,
            "message": self.message,
            "author": self.author,
            "mesh_hashes": self.mesh_hashes,
            "commit_type": self.commit_type,
            "selected_mesh_names": self.selected_mesh_names,
            "export_options": self.export_options
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Commit':
        """
        Create commit from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Commit instance
        """
        return cls(
            hash=data.get('hash', ''),
            parent_hash=data.get('parent_hash'),
            tree_hash=data['tree_hash'],
            branch=data['branch'],
            timestamp=data['timestamp'],
            message=data.get('message', ''),
            author=data.get('author', ''),
            mesh_hashes=data.get('mesh_hashes', []),
            commit_type=data.get('commit_type', 'project'),
            selected_mesh_names=data.get('selected_mesh_names', []),
            export_options=data.get('export_options', {})
        )
    
    def save_to_storage(self, db: ForesterDB, storage: ObjectStorage) -> None:
        """
        Save commit to storage and database.
        
        Args:
            db: Database connection
            storage: Object storage
        """
        # Compute hash if not set
        if not self.hash:
            self.hash = self.compute_hash()
        
        # Save to storage
        commit_data = self.to_dict()
        storage.save_commit(commit_data, self.hash)
        
        # Save to database
        db.add_commit(
            commit_hash=self.hash,
            branch=self.branch,
            parent_hash=self.parent_hash,
            timestamp=self.timestamp,
            message=self.message,
            tree_hash=self.tree_hash,
            author=self.author,
            commit_type=self.commit_type,
            selected_mesh_names=self.selected_mesh_names,
            export_options=self.export_options
        )
    
    @classmethod
    def from_storage(cls, commit_hash: str, db: ForesterDB,
                     storage: ObjectStorage) -> Optional['Commit']:
        """
        Load commit from storage.
        
        Args:
            commit_hash: SHA-256 hash of the commit
            db: Database connection
            storage: Object storage
            
        Returns:
            Commit instance or None if not found
        """
        # Try to load from database first
        commit_info = db.get_commit(commit_hash)
        if commit_info:
            # Load full data from storage if available
            try:
                commit_data = storage.load_commit(commit_hash)
                mesh_hashes = commit_data.get('mesh_hashes', [])
                commit_type = commit_data.get('commit_type', 'project')
                selected_mesh_names = commit_data.get('selected_mesh_names', [])
                export_options = commit_data.get('export_options', {})
            except FileNotFoundError:
                mesh_hashes = []
                commit_type = commit_info.get('commit_type', 'project')
                selected_mesh_names = []
                export_options = {}
            
            return cls(
                hash=commit_info['hash'],
                parent_hash=commit_info.get('parent_hash'),
                tree_hash=commit_info['tree_hash'],
                branch=commit_info['branch'],
                timestamp=commit_info['timestamp'],
                message=commit_info.get('message', ''),
                author=commit_info.get('author', ''),
                mesh_hashes=mesh_hashes,
                commit_type=commit_type,
                selected_mesh_names=selected_mesh_names,
                export_options=export_options
            )
        
        # Try to load from storage
        try:
            commit_data = storage.load_commit(commit_hash)
            return cls.from_dict(commit_data)
        except FileNotFoundError:
            return None
    
    @classmethod
    def create(cls, tree: Tree, branch: str, message: str, author: str,
               parent_hash: Optional[str] = None, mesh_hashes: Optional[List[str]] = None,
               commit_type: str = "project", selected_mesh_names: Optional[List[str]] = None,
               export_options: Optional[Dict[str, bool]] = None) -> 'Commit':
        """
        Create a new commit.
        
        Args:
            tree: Tree object
            branch: Branch name
            message: Commit message
            author: Author name
            parent_hash: Parent commit hash (optional)
            mesh_hashes: List of mesh hashes (optional)
            commit_type: Type of commit ("project" or "mesh_only")
            selected_mesh_names: List of selected mesh names (for mesh_only)
            export_options: Export options dict (for mesh_only)
            
        Returns:
            Commit instance
        """
        timestamp = int(time.time())
        
        commit = cls(
            hash="",  # Will be computed
            parent_hash=parent_hash,
            tree_hash=tree.hash,
            branch=branch,
            timestamp=timestamp,
            message=message,
            author=author,
            mesh_hashes=mesh_hashes or [],
            commit_type=commit_type,
            selected_mesh_names=selected_mesh_names or [],
            export_options=export_options or {}
        )
        
        commit.hash = commit.compute_hash()
        
        return commit
    
    def get_tree(self, db: ForesterDB, storage: ObjectStorage) -> Optional[Tree]:
        """
        Get tree object for this commit.
        
        Args:
            db: Database connection
            storage: Object storage
            
        Returns:
            Tree instance or None if not found
        """
        return Tree.from_storage(self.tree_hash, db, storage)


