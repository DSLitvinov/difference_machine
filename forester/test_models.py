#!/usr/bin/env python3
"""
Test script for Forester models.
Tests all data models: Blob, Tree, Commit, Mesh.
"""

import tempfile
import shutil
import json
import time
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from forester.models.blob import Blob
from forester.models.tree import Tree, TreeEntry
from forester.models.commit import Commit
from forester.models.mesh import Mesh
from forester.core.database import ForesterDB
from forester.core.storage import ObjectStorage
from forester.core.ignore import IgnoreRules
from forester.core.hashing import compute_hash


def test_blob():
    """Test Blob model."""
    print("Testing Blob model...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / ".DFM"
        base_dir.mkdir()
        
        # Initialize database and storage
        db_path = base_dir / "forester.db"
        with ForesterDB(db_path) as db:
            db.initialize_schema()
        
        storage = ObjectStorage(base_dir)
        
        # Create test file
        test_file = Path(tmpdir) / "test.txt"
        test_content = b"Hello, Forester!"
        test_file.write_bytes(test_content)
        
        # Create blob from file
        blob1 = Blob.from_file(test_file, base_dir, db, storage)
        assert blob1.hash is not None, "Blob should have hash"
        assert blob1.size == len(test_content), "Blob size should match"
        print("  ✓ Blob created from file")
        
        # Create blob from same file (should reuse existing)
        blob2 = Blob.from_file(test_file, base_dir, db, storage)
        assert blob1.hash == blob2.hash, "Same file should produce same hash"
        print("  ✓ Blob deduplication works")
        
        # Load blob from storage
        blob3 = Blob.from_storage(blob1.hash, db, storage)
        assert blob3 is not None, "Blob should be loadable"
        assert blob3.hash == blob1.hash, "Loaded blob should match"
        print("  ✓ Blob loaded from storage")
        
        # Test data loading
        loaded_data = blob1.load_data(storage)
        assert loaded_data == test_content, "Loaded data should match"
        print("  ✓ Blob data loading works")
    
    print("  ✓ All Blob tests passed!\n")


def test_tree():
    """Test Tree model."""
    print("Testing Tree model...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / ".DFM"
        base_dir.mkdir()
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        
        # Initialize database and storage
        db_path = base_dir / "forester.db"
        with ForesterDB(db_path) as db:
            db.initialize_schema()
        
        storage = ObjectStorage(base_dir)
        
        # Create test files
        (project_dir / "file1.txt").write_text("Content 1")
        (project_dir / "file2.txt").write_text("Content 2")
        (project_dir / "subdir").mkdir()
        (project_dir / "subdir" / "file3.txt").write_text("Content 3")
        
        # Create ignore rules
        ignore_file = base_dir / ".dfmignore"
        ignore_rules = IgnoreRules(ignore_file)
        
        # Create tree from directory
        tree = Tree.from_directory(project_dir, project_dir, ignore_rules, db, storage)
        assert tree.hash is not None, "Tree should have hash"
        assert len(tree.entries) == 3, "Tree should have 3 entries"
        print("  ✓ Tree created from directory")
        
        # Save tree
        tree.save_to_storage(db, storage)
        assert db.tree_exists(tree.hash), "Tree should exist in database"
        print("  ✓ Tree saved to storage")
        
        # Load tree from storage
        loaded_tree = Tree.from_storage(tree.hash, db, storage)
        assert loaded_tree is not None, "Tree should be loadable"
        assert loaded_tree.hash == tree.hash, "Loaded tree should match"
        assert len(loaded_tree.entries) == len(tree.entries), "Entries should match"
        print("  ✓ Tree loaded from storage")
        
        # Test TreeEntry
        entry = TreeEntry(path="test.txt", type="blob", hash="abc123", size=100)
        assert entry.path == "test.txt", "Entry path should match"
        entry_dict = entry.to_dict()
        entry2 = TreeEntry.from_dict(entry_dict)
        assert entry2.path == entry.path, "Entry serialization should work"
        print("  ✓ TreeEntry works")
    
    print("  ✓ All Tree tests passed!\n")


def test_commit():
    """Test Commit model."""
    print("Testing Commit model...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / ".DFM"
        base_dir.mkdir()
        
        # Initialize database and storage
        db_path = base_dir / "forester.db"
        with ForesterDB(db_path) as db:
            db.initialize_schema()
        
        storage = ObjectStorage(base_dir)
        
        # Create a tree first
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        (project_dir / "file.txt").write_text("Test content")
        
        ignore_file = base_dir / ".dfmignore"
        ignore_rules = IgnoreRules(ignore_file)
        
        tree = Tree.from_directory(project_dir, project_dir, ignore_rules, db, storage)
        tree.save_to_storage(db, storage)
        
        # Create commit
        commit1 = Commit.create(
            tree=tree,
            branch="main",
            message="Initial commit",
            author="Test User"
        )
        assert commit1.hash is not None, "Commit should have hash"
        assert commit1.parent_hash is None, "First commit should have no parent"
        assert commit1.tree_hash == tree.hash, "Tree hash should match"
        print("  ✓ Commit created")
        
        # Save commit
        commit1.save_to_storage(db, storage)
        assert db.get_commit(commit1.hash) is not None, "Commit should exist in database"
        print("  ✓ Commit saved to storage")
        
        # Load commit from storage
        loaded_commit = Commit.from_storage(commit1.hash, db, storage)
        assert loaded_commit is not None, "Commit should be loadable"
        assert loaded_commit.hash == commit1.hash, "Loaded commit should match"
        assert loaded_commit.message == commit1.message, "Message should match"
        print("  ✓ Commit loaded from storage")
        
        # Create second commit with parent
        commit2 = Commit.create(
            tree=tree,
            branch="main",
            message="Second commit",
            author="Test User",
            parent_hash=commit1.hash
        )
        assert commit2.parent_hash == commit1.hash, "Parent hash should match"
        print("  ✓ Commit with parent created")
        
        # Test get_tree
        loaded_tree = commit1.get_tree(db, storage)
        assert loaded_tree is not None, "Should be able to get tree from commit"
        assert loaded_tree.hash == tree.hash, "Tree hash should match"
        print("  ✓ Commit.get_tree() works")
    
    print("  ✓ All Commit tests passed!\n")


def test_mesh():
    """Test Mesh model."""
    print("Testing Mesh model...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / ".DFM"
        base_dir.mkdir()
        
        # Initialize database and storage
        db_path = base_dir / "forester.db"
        with ForesterDB(db_path) as db:
            db.initialize_schema()
        
        storage = ObjectStorage(base_dir)
        
        # Create test mesh JSON files
        mesh_dir = Path(tmpdir) / "mesh1"
        mesh_dir.mkdir()
        
        mesh_json = {
            "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            "faces": [[0, 1, 2]],
            "uv": [[0, 0], [1, 0], [0, 1]]
        }
        
        material_json = {
            "color": [1.0, 0.0, 0.0],
            "metallic": 0.5
        }
        
        (mesh_dir / "mesh.json").write_text(json.dumps(mesh_json))
        (mesh_dir / "material.json").write_text(json.dumps(material_json))
        
        # Create mesh from directory
        mesh1 = Mesh.from_directory(mesh_dir, base_dir, db, storage)
        assert mesh1 is not None, "Mesh should be created"
        assert mesh1.hash is not None, "Mesh should have hash"
        assert mesh1.mesh_json == mesh_json, "Mesh JSON should match"
        assert mesh1.material_json == material_json, "Material JSON should match"
        print("  ✓ Mesh created from directory")
        
        # Create mesh from same directory (should reuse)
        mesh2 = Mesh.from_directory(mesh_dir, base_dir, db, storage)
        assert mesh1.hash == mesh2.hash, "Same mesh should produce same hash"
        print("  ✓ Mesh deduplication works")
        
        # Load mesh from storage
        loaded_mesh = Mesh.from_storage(mesh1.hash, db, storage)
        assert loaded_mesh is not None, "Mesh should be loadable"
        assert loaded_mesh.hash == mesh1.hash, "Loaded mesh should match"
        assert loaded_mesh.mesh_json == mesh_json, "Mesh JSON should match"
        print("  ✓ Mesh loaded from storage")
        
        # Test compute_hash
        mesh3 = Mesh(hash="", mesh_json=mesh_json, material_json=material_json)
        computed_hash = mesh3.compute_hash()
        assert computed_hash == mesh1.hash, "Computed hash should match"
        print("  ✓ Mesh hash computation works")
    
    print("  ✓ All Mesh tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Forester Models Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_blob()
        test_tree()
        test_commit()
        test_mesh()
        
        print("=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())




