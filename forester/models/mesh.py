"""
Mesh model for Forester.
Represents a 3D mesh stored in the repository.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from ..core.hashing import compute_hash
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage


class Mesh:
    """
    Represents a mesh in Forester repository.
    """
    
    def __init__(self, hash: str, mesh_json: Dict[str, Any], 
                 material_json: Dict[str, Any], created_at: int = None):
        """
        Initialize mesh.
        
        Args:
            hash: SHA-256 hash of the mesh
            mesh_json: Mesh data (vertices, faces, UV, normals, etc.)
            material_json: Material data
            created_at: Creation timestamp (optional)
        """
        self.hash = hash
        self.mesh_json = mesh_json
        self.material_json = material_json
        self.created_at = created_at
    
    def compute_hash(self) -> str:
        """
        Compute hash of the mesh based on its JSON data.
        
        Returns:
            SHA-256 hash string
        """
        # Combine mesh and material JSON
        combined = {
            "mesh": self.mesh_json,
            "material": self.material_json
        }
        combined_json = json.dumps(combined, sort_keys=True)
        return compute_hash(combined_json.encode('utf-8'))
    
    @classmethod
    def from_json_files(cls, mesh_json_path: Path, material_json_path: Path,
                       base_dir: Path, db: ForesterDB, storage: ObjectStorage) -> 'Mesh':
        """
        Create mesh from JSON files.
        
        Args:
            mesh_json_path: Path to mesh.json file
            material_json_path: Path to material.json file
            base_dir: Base directory of repository (.DFM/)
            db: Database connection
            storage: Object storage
            
        Returns:
            Mesh instance
        """
        # Load JSON files
        with open(mesh_json_path, 'r', encoding='utf-8') as f:
            mesh_json = json.load(f)
        
        material_json = {}
        if material_json_path.exists():
            with open(material_json_path, 'r', encoding='utf-8') as f:
                material_json = json.load(f)
        
        # Compute hash
        combined = {
            "mesh": mesh_json,
            "material": material_json
        }
        combined_json = json.dumps(combined, sort_keys=True)
        mesh_hash = compute_hash(combined_json.encode('utf-8'))
        
        # Check if mesh already exists
        if db.mesh_exists(mesh_hash):
            mesh_info = db.get_mesh(mesh_hash)
            loaded_mesh = storage.load_mesh(mesh_hash)
            return cls(
                hash=mesh_info['hash'],
                mesh_json=loaded_mesh['mesh_json'],
                material_json=loaded_mesh['material_json'],
                created_at=mesh_info.get('created_at')
            )
        
        # Save to storage
        mesh_data = {
            "mesh_json": mesh_json,
            "material_json": material_json
        }
        storage_path = storage.save_mesh(mesh_data, mesh_hash)
        
        # Add to database
        import time
        created_at = int(time.time())
        db.add_mesh(
            mesh_hash=mesh_hash,
            path=str(storage_path),
            mesh_json_path=str(storage_path / "mesh.json"),
            material_json_path=str(storage_path / "material.json"),
            created_at=created_at
        )
        
        return cls(
            hash=mesh_hash,
            mesh_json=mesh_json,
            material_json=material_json,
            created_at=created_at
        )
    
    @classmethod
    def from_directory(cls, mesh_dir: Path, base_dir: Path, db: ForesterDB,
                       storage: ObjectStorage) -> Optional['Mesh']:
        """
        Create mesh from directory containing mesh.json and material.json.
        
        Args:
            mesh_dir: Directory containing mesh files
            base_dir: Base directory of repository
            db: Database connection
            storage: Object storage
            
        Returns:
            Mesh instance or None if files not found
        """
        mesh_json_path = mesh_dir / "mesh.json"
        material_json_path = mesh_dir / "material.json"
        
        if not mesh_json_path.exists():
            return None
        
        return cls.from_json_files(mesh_json_path, material_json_path, base_dir, db, storage)
    
    @classmethod
    def from_storage(cls, mesh_hash: str, db: ForesterDB,
                     storage: ObjectStorage) -> Optional['Mesh']:
        """
        Load mesh from storage.
        
        Args:
            mesh_hash: SHA-256 hash of the mesh
            db: Database connection
            storage: Object storage
            
        Returns:
            Mesh instance or None if not found
        """
        mesh_info = db.get_mesh(mesh_hash)
        if not mesh_info:
            return None
        
        mesh_data = storage.load_mesh(mesh_hash)
        
        return cls(
            hash=mesh_info['hash'],
            mesh_json=mesh_data['mesh_json'],
            material_json=mesh_data['material_json'],
            created_at=mesh_info.get('created_at')
        )
    
    def to_dict(self) -> dict:
        """
        Convert mesh to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "hash": self.hash,
            "mesh_json": self.mesh_json,
            "material_json": self.material_json,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Mesh':
        """
        Create mesh from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Mesh instance
        """
        return cls(
            hash=data.get('hash', ''),
            mesh_json=data.get('mesh_json', {}),
            material_json=data.get('material_json', {}),
            created_at=data.get('created_at')
        )


