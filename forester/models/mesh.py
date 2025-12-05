"""
Mesh model for Forester.
Represents a 3D mesh stored in the repository.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from ..core.hashing import compute_hash, compute_file_hash
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage


class Mesh:
    """
    Represents a mesh in Forester repository.
    """

    def __init__(self, hash: str, blend_path: Path, metadata: Dict[str, Any], created_at: int = None):
        """
        Initialize mesh.

        Args:
            hash: SHA-256 hash of the mesh
            blend_path: Path to .blend file
            metadata: Metadata dict with mesh_json, material_json
            created_at: Creation timestamp (optional)
        """
        self.hash = hash
        self.blend_path = blend_path
        self.metadata = metadata
        self.created_at = created_at

    @property
    def mesh_json(self) -> Dict[str, Any]:
        """Get mesh JSON from metadata."""
        mesh_json_raw = self.metadata.get('mesh_json', {})
        # Normalize - ensure it's a dict, not a string
        if isinstance(mesh_json_raw, str):
            try:
                return json.loads(mesh_json_raw)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(mesh_json_raw, dict):
            return mesh_json_raw
        else:
            return {}

    @property
    def material_json(self) -> Dict[str, Any]:
        """Get material JSON from metadata."""
        material_json_raw = self.metadata.get('material_json', {})
        # Normalize - ensure it's a dict, not a string
        if isinstance(material_json_raw, str):
            try:
                return json.loads(material_json_raw)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(material_json_raw, dict):
            return material_json_raw
        else:
            return {}

    def compute_hash(self) -> str:
        """
        Compute hash from .blend file + metadata.

        Returns:
            SHA-256 hash string
        """
        # Читаем .blend файл
        if not self.blend_path.exists():
            raise FileNotFoundError(f"Blend file not found: {self.blend_path}")
        
        blend_hash = compute_file_hash(self.blend_path)
        
        # Комбинируем с метаданными
        metadata_json = json.dumps(self.metadata, sort_keys=True)
        combined = blend_hash + metadata_json
        return compute_hash(combined.encode('utf-8'))

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
        Create mesh from directory containing mesh.blend and mesh_metadata.json.

        Args:
            mesh_dir: Directory containing mesh files
            base_dir: Base directory of repository
            db: Database connection
            storage: Object storage

        Returns:
            Mesh instance or None if files not found
        """
        blend_path = mesh_dir / "mesh.blend"
        metadata_path = mesh_dir / "mesh_metadata.json"

        if not blend_path.exists() or not metadata_path.exists():
            return None

        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata_raw = json.load(f)
        
        # Normalize metadata - ensure nested dicts are not strings
        if isinstance(metadata_raw, dict):
            metadata = metadata_raw
            # Check if material_json is a string
            if 'material_json' in metadata and isinstance(metadata['material_json'], str):
                try:
                    metadata['material_json'] = json.loads(metadata['material_json'])
                except (json.JSONDecodeError, TypeError):
                    metadata['material_json'] = {}
        else:
            metadata = {}

        return cls.from_blend_file(blend_path, metadata, base_dir, db, storage)

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
        
        # Normalize metadata - ensure it's a dict, not a string
        metadata_raw = mesh_data.get('metadata', {})
        if isinstance(metadata_raw, str):
            try:
                metadata = json.loads(metadata_raw)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        elif isinstance(metadata_raw, dict):
            metadata = metadata_raw
        else:
            metadata = {}

        return cls(
            hash=mesh_info['hash'],
            blend_path=Path(mesh_data['blend_path']),
            metadata=metadata,
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
            "blend_path": str(self.blend_path),
            "metadata": self.metadata,
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
        metadata_raw = data.get('metadata', {})
        # Normalize metadata - ensure it's a dict, not a string
        if isinstance(metadata_raw, str):
            try:
                metadata = json.loads(metadata_raw)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        elif isinstance(metadata_raw, dict):
            metadata = metadata_raw
            # Check if material_json is a string
            if 'material_json' in metadata and isinstance(metadata['material_json'], str):
                try:
                    metadata['material_json'] = json.loads(metadata['material_json'])
                except (json.JSONDecodeError, TypeError):
                    metadata['material_json'] = {}
        else:
            metadata = {}
        
        return cls(
            hash=data.get('hash', ''),
            blend_path=Path(data.get('blend_path', '')),
            metadata=metadata,
            created_at=data.get('created_at')
        )




