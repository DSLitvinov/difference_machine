"""
Blob model for Forester.
Represents a file stored in the repository.
"""

from pathlib import Path
from typing import Optional
from ..core.hashing import compute_hash, compute_file_hash
from ..core.database import ForesterDB
from ..core.storage import ObjectStorage


class Blob:
    """
    Represents a blob (file) in Forester repository.
    """

    def __init__(self, hash: str, path: Path, size: int, created_at: int = None):
        """
        Initialize blob.

        Args:
            hash: SHA-256 hash of the blob content
            path: Path in objects/blobs/ storage
            size: Size of the blob in bytes
            created_at: Creation timestamp (optional)
        """
        self.hash = hash
        self.path = path
        self.size = size
        self.created_at = created_at

    @classmethod
    def from_file(cls, file_path: Path, base_dir: Path, db: ForesterDB,
                  storage: ObjectStorage) -> 'Blob':
        """
        Create blob from file.

        Args:
            file_path: Path to the file
            base_dir: Base directory of repository (.DFM/)
            db: Database connection
            storage: Object storage

        Returns:
            Blob instance
        """
        # Compute hash
        blob_hash = compute_file_hash(file_path)

        # Check if blob already exists
        if db.blob_exists(blob_hash):
            blob_info = db.get_blob(blob_hash)
            return cls(
                hash=blob_info['hash'],
                path=Path(blob_info['path']),
                size=blob_info['size'],
                created_at=blob_info.get('created_at')
            )

        # Read file data
        with open(file_path, 'rb') as f:
            data = f.read()

        # Save to storage
        storage_path = storage.save_blob(data, blob_hash)

        # Add to database
        import time
        created_at = int(time.time())
        db.add_blob(blob_hash, str(storage_path), len(data), created_at)

        return cls(
            hash=blob_hash,
            path=storage_path,
            size=len(data),
            created_at=created_at
        )

    @classmethod
    def from_file_data(cls, data: bytes, blob_hash: str, base_dir: Path,
                      db: ForesterDB, storage: ObjectStorage) -> 'Blob':
        """
        Create blob from data in memory.

        Args:
            data: Binary data
            blob_hash: SHA-256 hash of the data
            base_dir: Base directory of repository (.DFM/)
            db: Database connection
            storage: Object storage

        Returns:
            Blob instance
        """
        # Check if blob already exists
        if db.blob_exists(blob_hash):
            blob_info = db.get_blob(blob_hash)
            return cls(
                hash=blob_info['hash'],
                path=Path(blob_info['path']),
                size=blob_info['size'],
                created_at=blob_info.get('created_at')
            )

        # Save to storage
        storage_path = storage.save_blob(data, blob_hash)

        # Add to database
        import time
        created_at = int(time.time())
        db.add_blob(blob_hash, str(storage_path), len(data), created_at)

        return cls(
            hash=blob_hash,
            path=storage_path,
            size=len(data),
            created_at=created_at
        )

    @classmethod
    def from_storage(cls, blob_hash: str, db: ForesterDB,
                     storage: ObjectStorage) -> Optional['Blob']:
        """
        Load blob from storage.

        Args:
            blob_hash: SHA-256 hash of the blob
            db: Database connection
            storage: Object storage

        Returns:
            Blob instance or None if not found
        """
        blob_info = db.get_blob(blob_hash)
        if not blob_info:
            return None

        return cls(
            hash=blob_info['hash'],
            path=Path(blob_info['path']),
            size=blob_info['size'],
            created_at=blob_info.get('created_at')
        )

    def to_dict(self) -> dict:
        """
        Convert blob to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "hash": self.hash,
            "path": str(self.path),
            "size": self.size,
            "created_at": self.created_at
        }

    def load_data(self, storage: ObjectStorage) -> bytes:
        """
        Load blob data from storage.

        Args:
            storage: Object storage

        Returns:
            Binary data
        """
        return storage.load_blob(self.hash)


