"""
Texture model for Forester.
Represents a texture versioned independently from meshes.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from ..core.hashing import compute_hash, compute_file_hash
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage

logger = logging.getLogger(__name__)


class Texture:
    """
    Represents a texture in Forester repository.
    Textures are versioned independently from meshes.
    """

    def __init__(
        self,
        hash: str,
        original_name: str,
        file_path: Path,
        width: Optional[int] = None,
        height: Optional[int] = None,
        format: Optional[str] = None,
        file_size: Optional[int] = None,
        created_at: Optional[int] = None
    ):
        """
        Initialize texture.

        Args:
            hash: SHA-256 hash of the texture file
            original_name: Original filename
            file_path: Path to texture file in storage
            width: Texture width in pixels
            height: Texture height in pixels
            format: Texture format (PNG, JPEG, EXR, etc.)
            file_size: File size in bytes
            created_at: Creation timestamp
        """
        self.hash = hash
        self.original_name = original_name
        self.file_path = file_path
        self.width = width
        self.height = height
        self.format = format
        self.file_size = file_size
        self.created_at = created_at or int(time.time())

    @classmethod
    def from_file(
        cls,
        texture_path: Path,
        base_dir: Path,
        db: ForesterDB,
        storage: ObjectStorage
    ) -> 'Texture':
        """
        Create texture from file.

        Args:
            texture_path: Path to texture file
            base_dir: Base directory of repository (.DFM/)
            db: Database connection
            storage: Object storage

        Returns:
            Texture instance
        """
        if not texture_path.exists():
            raise FileNotFoundError(f"Texture file not found: {texture_path}")

        # Compute hash
        texture_hash = compute_file_hash(texture_path)

        # Check if texture already exists
        if db.texture_exists(texture_hash):
            texture_info = db.get_texture(texture_hash)
            return cls(
                hash=texture_info['hash'],
                original_name=texture_info['original_name'],
                file_path=Path(texture_info['file_path']),
                width=texture_info.get('width'),
                height=texture_info.get('height'),
                format=texture_info.get('format'),
                file_size=texture_info.get('file_size'),
                created_at=texture_info.get('created_at')
            )

        # Get texture metadata
        width = height = None
        format_name = texture_path.suffix[1:].upper() if texture_path.suffix else None
        
        try:
            from PIL import Image
            with Image.open(texture_path) as img:
                width, height = img.size
                if img.format:
                    format_name = img.format
        except ImportError:
            # PIL not available, use fallback (already set above)
            logger.debug("PIL/Pillow not available, using file extension for format")
        except Exception as e:
            logger.warning(f"Could not read texture metadata: {e}", exc_info=True)
            # Keep fallback values

        file_size = texture_path.stat().st_size

        # Save to storage
        storage_path = storage.save_texture(texture_path.read_bytes(), texture_hash, format_name)

        # Add to database
        created_at = int(time.time())
        db.add_texture(
            texture_hash=texture_hash,
            original_name=texture_path.name,
            file_path=str(storage_path),
            width=width,
            height=height,
            format=format_name,
            file_size=file_size,
            created_at=created_at
        )

        return cls(
            hash=texture_hash,
            original_name=texture_path.name,
            file_path=storage_path,
            width=width,
            height=height,
            format=format_name,
            file_size=file_size,
            created_at=created_at
        )

    @classmethod
    def from_storage(
        cls,
        texture_hash: str,
        db: ForesterDB,
        storage: ObjectStorage
    ) -> Optional['Texture']:
        """
        Load texture from storage.

        Args:
            texture_hash: SHA-256 hash of the texture
            db: Database connection
            storage: Object storage

        Returns:
            Texture instance or None if not found
        """
        texture_info = db.get_texture(texture_hash)
        if not texture_info:
            return None

        return cls(
            hash=texture_info['hash'],
            original_name=texture_info['original_name'],
            file_path=Path(texture_info['file_path']),
            width=texture_info.get('width'),
            height=texture_info.get('height'),
            format=texture_info.get('format'),
            file_size=texture_info.get('file_size'),
            created_at=texture_info.get('created_at')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert texture to dictionary."""
        return {
            'hash': self.hash,
            'original_name': self.original_name,
            'file_path': str(self.file_path),
            'width': self.width,
            'height': self.height,
            'format': self.format,
            'file_size': self.file_size,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Texture':
        """Create texture from dictionary."""
        return cls(
            hash=data['hash'],
            original_name=data['original_name'],
            file_path=Path(data['file_path']),
            width=data.get('width'),
            height=data.get('height'),
            format=data.get('format'),
            file_size=data.get('file_size'),
            created_at=data.get('created_at')
        )

