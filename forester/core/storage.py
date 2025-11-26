"""
Object storage module for Forester.
Handles storage and retrieval of blobs, trees, commits, and meshes.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from .hashing import hash_to_path


class ObjectStorage:
    """
    Manages storage of objects in Forester repository.
    """
    
    def __init__(self, base_dir: Path):
        """
        Initialize object storage.
        
        Args:
            base_dir: Base directory (.DFM/)
        """
        self.base_dir = base_dir
        self.objects_dir = base_dir / "objects"
        
        # Ensure object directories exist
        for obj_type in ["blobs", "trees", "commits", "meshes"]:
            (self.objects_dir / obj_type).mkdir(parents=True, exist_ok=True)
    
    # ========== Blob operations ==========
    
    def save_blob(self, data: bytes, blob_hash: str) -> Path:
        """
        Save blob to storage.
        
        Args:
            data: Binary data to save
            blob_hash: SHA-256 hash of the data
            
        Returns:
            Path where blob was saved
        """
        blob_path = hash_to_path(blob_hash, self.base_dir, "blobs")
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(blob_path, 'wb') as f:
            f.write(data)
        
        return blob_path
    
    def load_blob(self, blob_hash: str) -> bytes:
        """
        Load blob from storage.
        
        Args:
            blob_hash: SHA-256 hash of the blob
            
        Returns:
            Binary data
            
        Raises:
            FileNotFoundError: If blob doesn't exist
        """
        blob_path = hash_to_path(blob_hash, self.base_dir, "blobs")
        
        if not blob_path.exists():
            raise FileNotFoundError(f"Blob not found: {blob_hash}")
        
        with open(blob_path, 'rb') as f:
            return f.read()
    
    def blob_exists(self, blob_hash: str) -> bool:
        """Check if blob exists in storage."""
        blob_path = hash_to_path(blob_hash, self.base_dir, "blobs")
        return blob_path.exists()
    
    def delete_blob(self, blob_hash: str) -> None:
        """Delete blob from storage."""
        blob_path = hash_to_path(blob_hash, self.base_dir, "blobs")
        if blob_path.exists():
            blob_path.unlink()
            # Try to remove empty parent directories
            try:
                blob_path.parent.rmdir()
                blob_path.parent.parent.rmdir()
            except OSError:
                pass  # Directory not empty or doesn't exist
    
    # ========== Tree operations ==========
    
    def save_tree(self, tree_data: Dict[str, Any], tree_hash: str) -> Path:
        """
        Save tree to storage.
        
        Args:
            tree_data: Tree data (dict with 'entries' key)
            tree_hash: SHA-256 hash of the tree
            
        Returns:
            Path where tree was saved
        """
        tree_path = hash_to_path(tree_hash, self.base_dir, "trees")
        tree_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(tree_path, 'w', encoding='utf-8') as f:
            json.dump(tree_data, f, indent=2, ensure_ascii=False)
        
        return tree_path
    
    def load_tree(self, tree_hash: str) -> Dict[str, Any]:
        """
        Load tree from storage.
        
        Args:
            tree_hash: SHA-256 hash of the tree
            
        Returns:
            Tree data dictionary
            
        Raises:
            FileNotFoundError: If tree doesn't exist
        """
        tree_path = hash_to_path(tree_hash, self.base_dir, "trees")
        
        if not tree_path.exists():
            raise FileNotFoundError(f"Tree not found: {tree_hash}")
        
        with open(tree_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def tree_exists(self, tree_hash: str) -> bool:
        """Check if tree exists in storage."""
        tree_path = hash_to_path(tree_hash, self.base_dir, "trees")
        return tree_path.exists()
    
    def delete_tree(self, tree_hash: str) -> None:
        """Delete tree from storage."""
        tree_path = hash_to_path(tree_hash, self.base_dir, "trees")
        if tree_path.exists():
            tree_path.unlink()
            # Try to remove empty parent directories
            try:
                tree_path.parent.rmdir()
                tree_path.parent.parent.rmdir()
            except OSError:
                pass
    
    # ========== Commit operations ==========
    
    def save_commit(self, commit_data: Dict[str, Any], commit_hash: str) -> Path:
        """
        Save commit to storage.
        
        Args:
            commit_data: Commit data dictionary
            commit_hash: SHA-256 hash of the commit
            
        Returns:
            Path where commit was saved
        """
        commit_path = hash_to_path(commit_hash, self.base_dir, "commits")
        commit_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(commit_path, 'w', encoding='utf-8') as f:
            json.dump(commit_data, f, indent=2, ensure_ascii=False)
        
        return commit_path
    
    def load_commit(self, commit_hash: str) -> Dict[str, Any]:
        """
        Load commit from storage.
        
        Args:
            commit_hash: SHA-256 hash of the commit
            
        Returns:
            Commit data dictionary
            
        Raises:
            FileNotFoundError: If commit doesn't exist
        """
        commit_path = hash_to_path(commit_hash, self.base_dir, "commits")
        
        if not commit_path.exists():
            raise FileNotFoundError(f"Commit not found: {commit_hash}")
        
        with open(commit_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def commit_exists(self, commit_hash: str) -> bool:
        """Check if commit exists in storage."""
        commit_path = hash_to_path(commit_hash, self.base_dir, "commits")
        return commit_path.exists()
    
    def delete_commit(self, commit_hash: str) -> None:
        """Delete commit from storage."""
        commit_path = hash_to_path(commit_hash, self.base_dir, "commits")
        if commit_path.exists():
            commit_path.unlink()
            # Try to remove empty parent directories
            try:
                commit_path.parent.rmdir()
                commit_path.parent.parent.rmdir()
            except OSError:
                pass
    
    # ========== Mesh operations ==========
    
    def save_mesh(self, mesh_data: Dict[str, Any], mesh_hash: str) -> Path:
        """
        Save mesh to storage.
        
        Args:
            mesh_data: Mesh data with 'mesh_json' and 'material_json' keys
            mesh_hash: SHA-256 hash of the mesh
            
        Returns:
            Path to mesh directory
        """
        mesh_dir = hash_to_path(mesh_hash, self.base_dir, "meshes")
        mesh_dir.mkdir(parents=True, exist_ok=True)
        
        # Save mesh.json
        mesh_json_path = mesh_dir / "mesh.json"
        with open(mesh_json_path, 'w', encoding='utf-8') as f:
            json.dump(mesh_data.get('mesh_json', {}), f, indent=2, ensure_ascii=False)
        
        # Save material.json
        material_json_path = mesh_dir / "material.json"
        with open(material_json_path, 'w', encoding='utf-8') as f:
            json.dump(mesh_data.get('material_json', {}), f, indent=2, ensure_ascii=False)
        
        return mesh_dir
    
    def load_mesh(self, mesh_hash: str) -> Dict[str, Any]:
        """
        Load mesh from storage.
        
        Args:
            mesh_hash: SHA-256 hash of the mesh
            
        Returns:
            Dictionary with 'mesh_json' and 'material_json' keys
            
        Raises:
            FileNotFoundError: If mesh doesn't exist
        """
        mesh_dir = hash_to_path(mesh_hash, self.base_dir, "meshes")
        
        if not mesh_dir.exists():
            raise FileNotFoundError(f"Mesh not found: {mesh_hash}")
        
        # Load mesh.json
        mesh_json_path = mesh_dir / "mesh.json"
        if not mesh_json_path.exists():
            raise FileNotFoundError(f"mesh.json not found for mesh: {mesh_hash}")
        
        with open(mesh_json_path, 'r', encoding='utf-8') as f:
            mesh_json = json.load(f)
        
        # Load material.json
        material_json_path = mesh_dir / "material.json"
        material_json = {}
        if material_json_path.exists():
            with open(material_json_path, 'r', encoding='utf-8') as f:
                material_json = json.load(f)
        
        return {
            'mesh_json': mesh_json,
            'material_json': material_json,
        }
    
    def mesh_exists(self, mesh_hash: str) -> bool:
        """Check if mesh exists in storage."""
        mesh_dir = hash_to_path(mesh_hash, self.base_dir, "meshes")
        return mesh_dir.exists() and (mesh_dir / "mesh.json").exists()
    
    def delete_mesh(self, mesh_hash: str) -> None:
        """Delete mesh from storage."""
        mesh_dir = hash_to_path(mesh_hash, self.base_dir, "meshes")
        if mesh_dir.exists():
            shutil.rmtree(mesh_dir)
            # Try to remove empty parent directories
            try:
                mesh_dir.parent.rmdir()
                mesh_dir.parent.parent.rmdir()
            except OSError:
                pass




