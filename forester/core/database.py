"""
Database module for Forester.
Manages SQLite database operations.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .storage import ObjectStorage


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
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Enable dict-like access
            # ВАЖНО: Настраиваем режим WAL для лучшей поддержки конкурентного доступа
            # и гарантии чтения актуальных данных
            try:
                self.conn.execute("PRAGMA journal_mode = WAL")
                self.conn.execute("PRAGMA synchronous = NORMAL")
            except Exception:
                pass  # Игнорируем ошибки, если WAL не поддерживается
    
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
    
    def initialize_schema(self) -> None:
        """
        Create database schema with all required tables.
        """
        if self.conn is None:
            self.connect()
        
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
                tag TEXT
            )
        """)
        
        # Migrate existing tables (add new columns if they don't exist)
        try:
            cursor.execute("ALTER TABLE commits ADD COLUMN commit_type TEXT DEFAULT 'project'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE commits ADD COLUMN selected_mesh_names TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE commits ADD COLUMN export_options TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE commits ADD COLUMN tag TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
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
        
        # Initialize repository_state if it doesn't exist
        cursor.execute("""
            INSERT OR IGNORE INTO repository_state (id, current_branch, head)
            VALUES (1, 'main', NULL)
        """)
        
        self.conn.commit()
        self.create_indexes()
    
    def create_indexes(self) -> None:
        """Create database indexes for performance."""
        if self.conn is None:
            self.connect()
        
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
        
        self.conn.commit()
    
    # ========== Commits operations ==========
    
    def add_commit(self, commit_hash: str, branch: str, parent_hash: Optional[str],
                   timestamp: int, message: str, tree_hash: str, author: str,
                   commit_type: str = "project", selected_mesh_names: Optional[List[str]] = None,
                   export_options: Optional[Dict[str, Any]] = None) -> None:
        """Add commit to database."""
        if self.conn is None:
            self.connect()
        
        cursor = self.conn.cursor()
        selected_mesh_names_json = json.dumps(selected_mesh_names) if selected_mesh_names else None
        export_options_json = json.dumps(export_options) if export_options else None
        
        cursor.execute("""
            INSERT INTO commits (hash, branch, parent_hash, timestamp, message, tree_hash, author,
                                commit_type, selected_mesh_names, export_options, tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (commit_hash, branch, parent_hash, timestamp, message, tree_hash, author,
              commit_type, selected_mesh_names_json, export_options_json, None))
        self.conn.commit()
    
    def _ensure_tag_column(self) -> None:
        """Ensure tag column exists in commits table."""
        if self.conn is None:
            self.connect()
        
        cursor = self.conn.cursor()
        # Check if tag column exists
        cursor.execute("PRAGMA table_info(commits)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'tag' not in columns:
            try:
                cursor.execute("ALTER TABLE commits ADD COLUMN tag TEXT")
                self.conn.commit()
            except sqlite3.OperationalError:
                pass  # Column might have been added by another process
    
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
        except Exception:
            pass  # Игнорируем ошибки checkpoint


