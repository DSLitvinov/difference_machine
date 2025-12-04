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
        for obj_type in ["blobs", "trees", "commits", "meshes", "textures"]:
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

        # Check if blob already exists on disk to avoid unnecessary write
        if blob_path.exists():
            return blob_path

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
        Save mesh to storage - новый формат (.blend + metadata).

        Args:
            mesh_data: Dict with keys:
                - 'blend_path': Path to .blend file
                - 'metadata': Dict with mesh_json, material_json
            mesh_hash: SHA-256 hash of the mesh

        Returns:
            Path to mesh directory
        """
        mesh_dir = hash_to_path(mesh_hash, self.base_dir, "meshes")
        mesh_dir.mkdir(parents=True, exist_ok=True)

        # Копируем .blend файл
        blend_path = Path(mesh_data['blend_path'])
        if blend_path.exists():
            shutil.copy2(blend_path, mesh_dir / "mesh.blend")
        else:
            raise FileNotFoundError(f"Blend file not found: {blend_path}")

        # Сохраняем метаданные
        metadata_path = mesh_dir / "mesh_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(mesh_data['metadata'], f, indent=2, ensure_ascii=False)

        return mesh_dir

    def load_mesh(self, mesh_hash: str) -> Dict[str, Any]:
        """
        Load mesh metadata from storage.

        Args:
            mesh_hash: SHA-256 hash of the mesh

        Returns:
            Dict with 'blend_path' and 'metadata' keys

        Raises:
            FileNotFoundError: If mesh doesn't exist
        """
        mesh_dir = hash_to_path(mesh_hash, self.base_dir, "meshes")

        if not mesh_dir.exists():
            raise FileNotFoundError(f"Mesh not found: {mesh_hash}")

        blend_path = mesh_dir / "mesh.blend"
        metadata_path = mesh_dir / "mesh_metadata.json"

        if not blend_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(f"Mesh files not found for: {mesh_hash}")

        # Загружаем метаданные
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        return {
            'blend_path': str(blend_path),
            'metadata': metadata
        }

    def mesh_exists(self, mesh_hash: str) -> bool:
        """Check if mesh exists in storage."""
        mesh_dir = hash_to_path(mesh_hash, self.base_dir, "meshes")
        return (mesh_dir.exists() and 
                (mesh_dir / "mesh.blend").exists() and 
                (mesh_dir / "mesh_metadata.json").exists())

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

    # ========== Texture operations ==========

    def save_texture(
        self,
        texture_data: bytes,
        texture_hash: str,
        format: Optional[str] = None
    ) -> Path:
        """
        Save texture to storage.

        Args:
            texture_data: Binary texture data
            texture_hash: SHA-256 hash of the texture
            format: Texture format (PNG, JPEG, etc.) for file extension

        Returns:
            Path where texture was saved
        """
        # Determine file extension
        ext = '.png'  # default
        if format:
            format_lower = format.lower()
            if format_lower in ['jpeg', 'jpg']:
                ext = '.jpg'
            elif format_lower == 'exr':
                ext = '.exr'
            elif format_lower == 'tga':
                ext = '.tga'
            elif format_lower == 'webp':
                ext = '.webp'
            elif format_lower == 'png':
                ext = '.png'

        texture_path = hash_to_path(texture_hash, self.base_dir, "textures")
        texture_path = texture_path.with_suffix(ext)
        texture_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if texture already exists
        if texture_path.exists():
            return texture_path

        with open(texture_path, 'wb') as f:
            f.write(texture_data)

        return texture_path

    def load_texture(self, texture_hash: str) -> Optional[bytes]:
        """
        Load texture from storage.

        Args:
            texture_hash: SHA-256 hash of the texture

        Returns:
            Binary texture data or None if not found
        """
        # Try different extensions
        base_path = hash_to_path(texture_hash, self.base_dir, "textures")
        for ext in ['.png', '.jpg', '.jpeg', '.exr', '.tga', '.webp']:
            texture_path = base_path.with_suffix(ext)
            if texture_path.exists():
                with open(texture_path, 'rb') as f:
                    return f.read()
        return None

    def texture_exists(self, texture_hash: str) -> bool:
        """Check if texture exists in storage."""
        base_path = hash_to_path(texture_hash, self.base_dir, "textures")
        for ext in ['.png', '.jpg', '.jpeg', '.exr', '.tga', '.webp']:
            if base_path.with_suffix(ext).exists():
                return True
        return False




