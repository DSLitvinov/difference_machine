"""
Database module for Forester.
Manages SQLite database operations.
"""

import logging
import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .storage import ObjectStorage

logger = logging.getLogger(__name__)


class ForesterDB:
    """
    SQLite database manager for Forester repository.
    """

    def __init__(self, db_path: Path):
        """
        Initialize database connection.

        Args:
            db_path: Path to forester.db file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Open database connection."""
        if self.conn is None:
            db_exists = self.db_path.exists()
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Enable dict-like access
            # ВАЖНО: Настраиваем режим WAL для лучшей поддержки конкурентного доступа
            # и гарантии чтения актуальных данных
            try:
                self.conn.execute("PRAGMA journal_mode = WAL")
                self.conn.execute("PRAGMA synchronous = NORMAL")
            except Exception as e:
                logger.debug(
                    f"Failed to set WAL mode or synchronous: {e}",
                    exc_info=True
                )
                # Continue without WAL mode if not supported
            
            # Ensure schema is up to date for existing databases
            # Call ensure_schema_unsafe to avoid recursion (conn is already set)
            if db_exists:
                self._ensure_schema_unsafe()

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def ensure_schema(self) -> None:
        """
        Ensure database schema is up to date.
        Creates missing tables and migrates columns if needed.
        Safe to call multiple times.
        """
        if self.conn is None:
            self.connect()
        self._ensure_schema_unsafe()

    def _ensure_schema_unsafe(self) -> None:
        """
        Internal method to ensure schema.
        Assumes connection is already established.
        """
        # First create all tables
        self._initialize_schema_unsafe()

        # Then migrate columns in existing tables
        cursor = self.conn.cursor()
        self._migrate_commit_columns(cursor)
        self.conn.commit()

    def initialize_schema(self) -> None:
        """
        Create database schema with all required tables.
        """
        if self.conn is None:
            self.connect()
        self._initialize_schema_unsafe()

    def _initialize_schema_unsafe(self) -> None:
        """
        Internal method to initialize schema.
        Assumes connection is already established.
        """
        cursor = self.conn.cursor()

        # Commits table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                branch TEXT NOT NULL,
                parent_hash TEXT,
                timestamp INTEGER NOT NULL,
                message TEXT,
                tree_hash TEXT NOT NULL,
                author TEXT,
                commit_type TEXT DEFAULT 'project',
                selected_mesh_names TEXT,
                export_options TEXT,
                tag TEXT,
                screenshot_hash TEXT
            )
        """)

        # Trees table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trees (
                hash TEXT PRIMARY KEY,
                entries TEXT NOT NULL
            )
        """)

        # Blobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blobs (
                hash TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                size INTEGER NOT NULL,
                created_at INTEGER
            )
        """)

        # Meshes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meshes (
                hash TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                mesh_json_path TEXT,
                material_json_path TEXT,
                created_at INTEGER
            )
        """)

        # Stash table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stash (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                timestamp INTEGER NOT NULL,
                message TEXT,
                tree_hash TEXT NOT NULL,
                branch TEXT
            )
        """)

        # Repository state table (for current branch and HEAD)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repository_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_branch TEXT NOT NULL DEFAULT 'main',
                head TEXT
            )
        """)

        # File locks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                lock_type TEXT NOT NULL,
                locked_by TEXT NOT NULL,
                locked_at INTEGER NOT NULL,
                expires_at INTEGER,
                branch TEXT,
                UNIQUE(file_path, branch)
            )
        """)

        # Comments table for review tools
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_hash TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                author TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                x REAL,
                y REAL,
                resolved INTEGER DEFAULT 0
            )
        """)

        # Approvals table for review workflow
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_hash TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                status TEXT NOT NULL,
                approver TEXT NOT NULL,
                comment TEXT,
                created_at INTEGER NOT NULL,
                UNIQUE(asset_hash, asset_type, approver)
            )
        """)

        # Initialize repository_state if it doesn't exist
        cursor.execute("""
            INSERT OR IGNORE INTO repository_state (id, current_branch, head)
            VALUES (1, 'main', NULL)
        """)

        self.conn.commit()
        self._create_indexes_unsafe()

    def create_indexes(self) -> None:
        """Create database indexes for performance."""
        if self.conn is None:
            self.connect()
        self._create_indexes_unsafe()

    def _create_indexes_unsafe(self) -> None:
        """
        Internal method to create indexes.
        Assumes connection is already established.
        """
        cursor = self.conn.cursor()

        # Indexes for commits
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_commits_branch
            ON commits(branch)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_commits_parent
            ON commits(parent_hash)
        """)

        # Index for stash
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stash_timestamp
            ON stash(timestamp)
        """)

        # Indexes for locks
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locks_file_path
            ON locks(file_path)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locks_branch
            ON locks(branch)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locks_expires_at
            ON locks(expires_at)
        """)

        # Indexes for comments
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_comments_asset
            ON comments(asset_hash, asset_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_comments_created_at
            ON comments(created_at)
        """)

        # Indexes for approvals
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_approvals_asset
            ON approvals(asset_hash, asset_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_approvals_status
            ON approvals(status)
        """)

        self.conn.commit()

    # ========== Commits operations ==========

    def add_commit(self, commit_hash: str, branch: str, parent_hash: Optional[str],
                   timestamp: int, message: str, tree_hash: str, author: str,
                   commit_type: str = "project", selected_mesh_names: Optional[List[str]] = None,
                   export_options: Optional[Dict[str, Any]] = None,
                   screenshot_hash: Optional[str] = None) -> None:
        """Add commit to database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        selected_mesh_names_json = json.dumps(selected_mesh_names) if selected_mesh_names else None
        export_options_json = json.dumps(export_options) if export_options else None

        cursor.execute("""
            INSERT INTO commits (hash, branch, parent_hash, timestamp, message, tree_hash, author,
                                commit_type, selected_mesh_names, export_options, tag, screenshot_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (commit_hash, branch, parent_hash, timestamp, message, tree_hash, author,
              commit_type, selected_mesh_names_json, export_options_json, None, screenshot_hash))
        self.conn.commit()


    def get_commit(self, commit_hash: str) -> Optional[Dict[str, Any]]:
        """Get commit by hash."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM commits WHERE hash = ?", (commit_hash,))
        row = cursor.fetchone()

        if row:
            result = dict(row)
            # Parse JSON fields
            if result.get('selected_mesh_names'):
                try:
                    result['selected_mesh_names'] = json.loads(result['selected_mesh_names'])
                except (json.JSONDecodeError, TypeError):
                    result['selected_mesh_names'] = []
            else:
                result['selected_mesh_names'] = []

            if result.get('export_options'):
                try:
                    result['export_options'] = json.loads(result['export_options'])
                except (json.JSONDecodeError, TypeError):
                    result['export_options'] = {}
            else:
                result['export_options'] = {}

            # Set default commit_type if not present
            if 'commit_type' not in result or not result['commit_type']:
                result['commit_type'] = 'project'

            return result
        return None

    def get_last_commit(self, branch: str) -> Optional[Dict[str, Any]]:
        """Get last commit in branch."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM commits
            WHERE branch = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (branch,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_commits_by_branch(self, branch: str) -> List[Dict[str, Any]]:
        """Get all commits in branch."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM commits
            WHERE branch = ?
            ORDER BY timestamp ASC
        """, (branch,))

        return [dict(row) for row in cursor.fetchall()]

    def delete_commit(self, commit_hash: str) -> None:
        """Delete commit from database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM commits WHERE hash = ?", (commit_hash,))
        self.conn.commit()

    # ========== Trees operations ==========

    def add_tree(self, tree_hash: str, entries: List[Dict[str, Any]]) -> None:
        """Add tree to database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        entries_json = json.dumps(entries)
        cursor.execute("""
            INSERT OR REPLACE INTO trees (hash, entries)
            VALUES (?, ?)
        """, (tree_hash, entries_json))
        self.conn.commit()

    def get_tree(self, tree_hash: str) -> Optional[List[Dict[str, Any]]]:
        """Get tree by hash."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT entries FROM trees WHERE hash = ?", (tree_hash,))
        row = cursor.fetchone()

        if row:
            return json.loads(row['entries'])
        return None

    def tree_exists(self, tree_hash: str) -> bool:
        """Check if tree exists."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM trees WHERE hash = ?", (tree_hash,))
        return cursor.fetchone() is not None

    def get_commits_using_tree(self, tree_hash: str) -> List[str]:
        """Get all commits using this tree."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT hash FROM commits WHERE tree_hash = ?", (tree_hash,))
        return [row['hash'] for row in cursor.fetchall()]

    def get_trees_using_hash(self, tree_hash: str) -> List[str]:
        """Get all commits using this tree (deprecated, use get_commits_using_tree)."""
        return self.get_commits_using_tree(tree_hash)

    def delete_tree(self, tree_hash: str) -> None:
        """Delete tree from database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM trees WHERE hash = ?", (tree_hash,))
        self.conn.commit()

    # ========== Blobs operations ==========

    def add_blob(self, blob_hash: str, path: str, size: int, created_at: int) -> None:
        """Add blob to database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO blobs (hash, path, size, created_at)
            VALUES (?, ?, ?, ?)
        """, (blob_hash, path, size, created_at))
        self.conn.commit()

    def get_blob(self, blob_hash: str) -> Optional[Dict[str, Any]]:
        """Get blob by hash."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM blobs WHERE hash = ?", (blob_hash,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def blob_exists(self, blob_hash: str) -> bool:
        """Check if blob exists."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM blobs WHERE hash = ?", (blob_hash,))
        return cursor.fetchone() is not None

    def get_blobs_in_tree(self, tree_hash: str) -> List[str]:
        """Get all blob hashes in a tree (recursively)."""
        tree = self.get_tree(tree_hash)
        if not tree:
            return []

        blob_hashes = []
        for entry in tree:
            if entry.get('type') == 'blob':
                blob_hashes.append(entry['hash'])
            elif entry.get('type') == 'tree':
                # Recursively get blobs from subtrees
                blob_hashes.extend(self.get_blobs_in_tree(entry['hash']))

        return blob_hashes

    def get_all_blobs_in_tree(self, tree_hash: str) -> List[str]:
        """
        Get all blob hashes in a tree recursively.
        Alias for get_blobs_in_tree for clarity.
        """
        return self.get_blobs_in_tree(tree_hash)

    def get_commits_using_blob(self, blob_hash: str) -> List[str]:
        """
        Get all commits using this blob (through trees).

        Optimized version that uses recursive CTE for better performance.
        """
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()

        # More efficient approach: check each tree directly
        # Get all unique tree hashes from commits
        cursor.execute("SELECT DISTINCT tree_hash FROM commits")
        tree_hashes = [row['tree_hash'] for row in cursor.fetchall()]

        using_commits = []
        for tree_hash in tree_hashes:
            # Check if blob is in this tree
            blobs = self.get_blobs_in_tree(tree_hash)
            if blob_hash in blobs:
                # Get all commits using this tree
                cursor.execute("SELECT hash FROM commits WHERE tree_hash = ?", (tree_hash,))
                for row in cursor.fetchall():
                    using_commits.append(row['hash'])

        return using_commits

    def delete_blob(self, blob_hash: str) -> None:
        """Delete blob from database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM blobs WHERE hash = ?", (blob_hash,))
        self.conn.commit()

    # ========== Meshes operations ==========

    def add_mesh(self, mesh_hash: str, path: str, mesh_json_path: str,
                 material_json_path: str, created_at: int) -> None:
        """Add mesh to database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO meshes (hash, path, mesh_json_path, material_json_path, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (mesh_hash, path, mesh_json_path, material_json_path, created_at))
        self.conn.commit()

    def get_mesh(self, mesh_hash: str) -> Optional[Dict[str, Any]]:
        """Get mesh by hash."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM meshes WHERE hash = ?", (mesh_hash,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def mesh_exists(self, mesh_hash: str) -> bool:
        """Check if mesh exists."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM meshes WHERE hash = ?", (mesh_hash,))
        return cursor.fetchone() is not None

    def get_commits_using_mesh(self, mesh_hash: str, storage: Optional['ObjectStorage'] = None) -> List[str]:
        """
        Get all commits using this mesh.

        Args:
            mesh_hash: Hash of the mesh
            storage: ObjectStorage instance (required to read commit files)

        Returns:
            List of commit hashes using this mesh
        """
        if self.conn is None:
            self.connect()

        if storage is None:
            # Cannot check without storage, return empty list
            return []

        cursor = self.conn.cursor()
        # Get all commit hashes from database
        cursor.execute("SELECT hash FROM commits")
        all_commits = [row['hash'] for row in cursor.fetchall()]

        using_commits = []
        for commit_hash in all_commits:
            try:
                # Load commit data from storage
                commit_data = storage.load_commit(commit_hash)
                mesh_hashes = commit_data.get('mesh_hashes', [])
                if mesh_hash in mesh_hashes:
                    using_commits.append(commit_hash)
            except (FileNotFoundError, KeyError, json.JSONDecodeError):
                # Commit file doesn't exist or is corrupted, skip
                continue

        return using_commits

    def delete_mesh(self, mesh_hash: str) -> None:
        """Delete mesh from database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM meshes WHERE hash = ?", (mesh_hash,))
        self.conn.commit()

    # ========== Stash operations ==========

    def add_stash(self, stash_hash: str, timestamp: int, message: str,
                  tree_hash: str, branch: str) -> None:
        """Add stash to database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO stash (hash, timestamp, message, tree_hash, branch)
            VALUES (?, ?, ?, ?, ?)
        """, (stash_hash, timestamp, message, tree_hash, branch))
        self.conn.commit()

    def get_stash(self, stash_hash: str) -> Optional[Dict[str, Any]]:
        """Get stash by hash."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM stash WHERE hash = ?", (stash_hash,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def list_stashes(self) -> List[Dict[str, Any]]:
        """Get all stashes, sorted by timestamp (newest first)."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM stash
            ORDER BY timestamp DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_all_stashes(self) -> List[Dict[str, Any]]:
        """Get all stashes (alias for list_stashes)."""
        return self.list_stashes()

    def delete_stash(self, stash_hash: str) -> None:
        """Delete stash from database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM stash WHERE hash = ?", (stash_hash,))
        self.conn.commit()

    # ========== Repository state operations ==========

    def get_current_branch(self) -> str:
        """Get current branch from database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT current_branch FROM repository_state WHERE id = 1")
        row = cursor.fetchone()

        if row:
            return row['current_branch'] or 'main'
        return 'main'

    def set_current_branch(self, branch_name: str) -> None:
        """Set current branch in database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO repository_state (id, current_branch, head)
            VALUES (1, ?, (SELECT head FROM repository_state WHERE id = 1))
        """, (branch_name,))
        self.conn.commit()

    def get_head(self) -> Optional[str]:
        """Get HEAD commit hash from database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT head FROM repository_state WHERE id = 1")
        row = cursor.fetchone()

        if row:
            return row['head']
        return None

    def set_head(self, commit_hash: Optional[str]) -> None:
        """Set HEAD commit hash in database."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO repository_state (id, current_branch, head)
            VALUES (1, (SELECT current_branch FROM repository_state WHERE id = 1), ?)
        """, (commit_hash,))
        self.conn.commit()

    def set_branch_and_head(self, branch_name: str, commit_hash: Optional[str]) -> None:
        """Set both current branch and HEAD in one operation."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO repository_state (id, current_branch, head)
            VALUES (1, ?, ?)
        """, (branch_name, commit_hash))
        self.conn.commit()

        # ВАЖНО: Принудительно синхронизируем изменения с диском
        # Это гарантирует, что следующее чтение получит актуальные данные
        try:
            self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception as e:
            logger.debug(
                f"Failed to checkpoint database: {e}",
                exc_info=True
            )
            # Continue without checkpoint

    # ========== File locking operations ==========

    def lock_file(self, file_path: str, lock_type: str, locked_by: str,
                  branch: Optional[str] = None, expires_after_seconds: Optional[int] = None) -> bool:
        """
        Lock a file to prevent concurrent modifications.

        Args:
            file_path: Path to file (relative to repo root)
            lock_type: Type of lock ('exclusive', 'shared')
            locked_by: Username/identifier of person locking
            branch: Branch name (optional, locks are per-branch)
            expires_after_seconds: Lock expiration time in seconds (None = never expires)

        Returns:
            True if lock acquired, False if already locked
        """
        if self.conn is None:
            self.connect()

        locked_at = int(time.time())
        expires_at = None
        if expires_after_seconds:
            expires_at = locked_at + expires_after_seconds

        cursor = self.conn.cursor()

        # Clean up expired locks first
        if expires_at is None:
            cursor.execute(
                "DELETE FROM locks WHERE file_path = ? AND branch = ? "
                "AND expires_at IS NOT NULL AND expires_at < ?",
                (file_path, branch, locked_at)
            )
        else:
            cursor.execute(
                "DELETE FROM locks WHERE file_path = ? AND branch = ? "
                "AND expires_at < ?",
                (file_path, branch, locked_at)
            )

        # Use INSERT OR IGNORE to prevent race condition
        # This is atomic - if lock exists, no row is inserted
        cursor.execute("""
            INSERT OR IGNORE INTO locks
            (file_path, lock_type, locked_by, locked_at, expires_at, branch)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (file_path, lock_type, locked_by, locked_at, expires_at, branch))

        self.conn.commit()

        # Check if lock was actually acquired
        if cursor.rowcount == 0:
            # Lock already exists - verify it's still active
            cursor.execute("""
                SELECT locked_by FROM locks
                WHERE file_path = ? AND branch = ?
                AND (expires_at IS NULL OR expires_at > ?)
            """, (file_path, branch, locked_at))

            if cursor.fetchone():
                return False  # Still locked

        return True

    def unlock_file(self, file_path: str, locked_by: str, branch: Optional[str] = None) -> bool:
        """
        Unlock a file.

        Args:
            file_path: Path to file
            locked_by: Username/identifier (must match lock owner)
            branch: Branch name (optional)

        Returns:
            True if unlocked, False if not locked or not owned by user
        """
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM locks
            WHERE file_path = ? AND locked_by = ? AND branch = ?
        """, (file_path, locked_by, branch))

        self.conn.commit()
        return cursor.rowcount > 0

    def is_file_locked(self, file_path: str, branch: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Check if file is locked.

        Args:
            file_path: Path to file
            branch: Branch name (optional)

        Returns:
            Lock information dict or None if not locked
        """
        if self.conn is None:
            self.connect()

        current_time = int(time.time())

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM locks
            WHERE file_path = ? AND branch = ?
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY locked_at DESC
            LIMIT 1
        """, (file_path, branch, current_time))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def list_locks(self, branch: Optional[str] = None, locked_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all active locks.

        Args:
            branch: Filter by branch (optional)
            locked_by: Filter by user (optional)

        Returns:
            List of lock dictionaries
        """
        if self.conn is None:
            self.connect()

        current_time = int(time.time())

        cursor = self.conn.cursor()

        if branch and locked_by:
            cursor.execute("""
                SELECT * FROM locks
                WHERE branch = ? AND locked_by = ?
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY locked_at DESC
            """, (branch, locked_by, current_time))
        elif branch:
            cursor.execute("""
                SELECT * FROM locks
                WHERE branch = ?
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY locked_at DESC
            """, (branch, current_time))
        elif locked_by:
            cursor.execute("""
                SELECT * FROM locks
                WHERE locked_by = ?
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY locked_at DESC
            """, (locked_by, current_time))
        else:
            cursor.execute("""
                SELECT * FROM locks
                WHERE (expires_at IS NULL OR expires_at > ?)
                ORDER BY locked_at DESC
            """, (current_time,))

        return [dict(row) for row in cursor.fetchall()]

    def cleanup_expired_locks(self) -> int:
        """
        Remove expired locks from database.

        Returns:
            Number of locks removed
        """
        if self.conn is None:
            self.connect()

        current_time = int(time.time())

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM locks WHERE expires_at IS NOT NULL AND expires_at <= ?", (current_time,))
        self.conn.commit()

        return cursor.rowcount

    # ========== Comments operations (Review tools) ==========

    def add_comment(self, asset_hash: str, asset_type: str, author: str, text: str,
                    x: Optional[float] = None, y: Optional[float] = None) -> int:
        """
        Add comment to asset (mesh, blob, commit).

        Args:
            asset_hash: Hash of the asset
            asset_type: Type ('mesh', 'blob', 'commit')
            author: Author name
            text: Comment text
            x: X coordinate for annotation (optional)
            y: Y coordinate for annotation (optional)

        Returns:
            Comment ID
        """
        if self.conn is None:
            self.connect()

        created_at = int(time.time())

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO comments (asset_hash, asset_type, author, text, created_at, x, y)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (asset_hash, asset_type, author, text, created_at, x, y))

        self.conn.commit()
        return cursor.lastrowid

    def get_comments(self, asset_hash: str, asset_type: str, include_resolved: bool = False) -> List[Dict[str, Any]]:
        """
        Get comments for asset.

        Args:
            asset_hash: Hash of the asset
            asset_type: Type ('mesh', 'blob', 'commit')
            include_resolved: Include resolved comments

        Returns:
            List of comment dictionaries
        """
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()

        if include_resolved:
            cursor.execute("""
                SELECT * FROM comments
                WHERE asset_hash = ? AND asset_type = ?
                ORDER BY created_at ASC
            """, (asset_hash, asset_type))
        else:
            cursor.execute("""
                SELECT * FROM comments
                WHERE asset_hash = ? AND asset_type = ? AND resolved = 0
                ORDER BY created_at ASC
            """, (asset_hash, asset_type))

        return [dict(row) for row in cursor.fetchall()]

    def resolve_comment(self, comment_id: int) -> bool:
        """Mark comment as resolved."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("UPDATE comments SET resolved = 1 WHERE id = ?", (comment_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_comment(self, comment_id: int) -> bool:
        """Delete comment."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ========== Approvals operations (Review tools) ==========

    def set_approval(self, asset_hash: str, asset_type: str, approver: str,
                     status: str, comment: Optional[str] = None) -> bool:
        """
        Set approval status for asset.

        Args:
            asset_hash: Hash of the asset
            asset_type: Type ('mesh', 'blob', 'commit')
            approver: Approver name
            status: Status ('pending', 'approved', 'rejected')
            comment: Optional comment

        Returns:
            True if successful
        """
        if self.conn is None:
            self.connect()

        created_at = int(time.time())

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO approvals (asset_hash, asset_type, status, approver, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (asset_hash, asset_type, status, approver, comment, created_at))

        self.conn.commit()
        return True

    def get_approval(self, asset_hash: str, asset_type: str, approver: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get approval status for asset.

        Args:
            asset_hash: Hash of the asset
            asset_type: Type ('mesh', 'blob', 'commit')
            approver: Filter by approver (optional)

        Returns:
            Approval dictionary or None
        """
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()

        if approver:
            cursor.execute("""
                SELECT * FROM approvals
                WHERE asset_hash = ? AND asset_type = ? AND approver = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (asset_hash, asset_type, approver))
        else:
            cursor.execute("""
                SELECT * FROM approvals
                WHERE asset_hash = ? AND asset_type = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (asset_hash, asset_type))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_all_approvals(self, asset_hash: str, asset_type: str) -> List[Dict[str, Any]]:
        """Get all approvals for asset."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM approvals
            WHERE asset_hash = ? AND asset_type = ?
            ORDER BY created_at DESC
        """, (asset_hash, asset_type))

        return [dict(row) for row in cursor.fetchall()]

    def delete_approval(self, asset_hash: str, asset_type: str, approver: str) -> bool:
        """Delete approval."""
        if self.conn is None:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM approvals
            WHERE asset_hash = ? AND asset_type = ? AND approver = ?
        """, (asset_hash, asset_type, approver))

        self.conn.commit()
        return cursor.rowcount > 0

