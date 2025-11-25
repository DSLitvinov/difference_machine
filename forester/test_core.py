#!/usr/bin/env python3
"""
Test script for Forester core modules.
Tests basic functionality of all core components.
"""

import tempfile
import shutil
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from forester.core.hashing import compute_hash, compute_file_hash, hash_to_path
from forester.core.database import ForesterDB
from forester.core.ignore import IgnoreRules
from forester.core.storage import ObjectStorage
from forester.utils.filesystem import scan_directory, copy_file, ensure_directory


def test_hashing():
    """Test hashing functions."""
    print("Testing hashing...")
    
    # Test compute_hash
    data = b"Hello, Forester!"
    hash1 = compute_hash(data)
    hash2 = compute_hash(data)
    assert hash1 == hash2, "Same data should produce same hash"
    assert len(hash1) == 64, "SHA-256 hash should be 64 characters"
    print(f"  ✓ compute_hash: {hash1[:16]}...")
    
    # Test compute_file_hash
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
        f.write(b"Test file content")
        temp_path = Path(f.name)
    
    try:
        file_hash = compute_file_hash(temp_path)
        assert len(file_hash) == 64, "File hash should be 64 characters"
        print(f"  ✓ compute_file_hash: {file_hash[:16]}...")
    finally:
        temp_path.unlink()
    
    # Test hash_to_path
    test_hash = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
    base_dir = Path("/tmp/test")
    blob_path = hash_to_path(test_hash, base_dir, "blobs")
    expected = base_dir / "objects" / "blobs" / "aa" / "bb" / "ccddeeff00112233445566778899aabbccddeeff00112233445566778899"
    assert blob_path == expected, f"Path mismatch: {blob_path} != {expected}"
    print(f"  ✓ hash_to_path: {blob_path}")
    
    print("  ✓ All hashing tests passed!\n")


def test_database():
    """Test database operations."""
    print("Testing database...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "forester.db"
        
        # Test initialization
        with ForesterDB(db_path) as db:
            db.initialize_schema()
            print("  ✓ Database schema created")
        
        # Test commit operations
        with ForesterDB(db_path) as db:
            db.add_commit(
                commit_hash="abc123",
                branch="main",
                parent_hash=None,
                timestamp=1234567890,
                message="Test commit",
                tree_hash="tree123",
                author="Test User"
            )
            
            commit = db.get_commit("abc123")
            assert commit is not None, "Commit should exist"
            assert commit['branch'] == "main", "Branch should match"
            assert commit['message'] == "Test commit", "Message should match"
            print("  ✓ Commit operations work")
            
            # Test tree operations
            tree_entries = [
                {"path": "file1.txt", "type": "blob", "hash": "hash1", "size": 100},
                {"path": "file2.txt", "type": "blob", "hash": "hash2", "size": 200}
            ]
            db.add_tree("tree123", tree_entries)
            
            tree = db.get_tree("tree123")
            assert tree is not None, "Tree should exist"
            assert len(tree) == 2, "Tree should have 2 entries"
            print("  ✓ Tree operations work")
            
            # Test blob operations
            db.add_blob("hash1", "/path/to/blob", 100, 1234567890)
            assert db.blob_exists("hash1"), "Blob should exist"
            print("  ✓ Blob operations work")
            
            # Test mesh operations
            db.add_mesh("mesh1", "/path/to/mesh", "mesh.json", "material.json", 1234567890)
            assert db.mesh_exists("mesh1"), "Mesh should exist"
            print("  ✓ Mesh operations work")
            
            # Test stash operations
            db.add_stash("stash1", 1234567890, "Test stash", "tree123", "main")
            stashes = db.list_stashes()
            assert len(stashes) == 1, "Should have 1 stash"
            print("  ✓ Stash operations work")
    
    print("  ✓ All database tests passed!\n")


def test_ignore():
    """Test ignore rules."""
    print("Testing ignore rules...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        ignore_file = Path(tmpdir) / ".dfmignore"
        base_path = Path(tmpdir)
        
        # Create ignore file
        with open(ignore_file, 'w') as f:
            f.write("*.tmp\n")
            f.write("test_dir/\n")
        
        rules = IgnoreRules(ignore_file)
        
        # Test should_ignore
        assert rules.should_ignore(base_path / "file.tmp", base_path), "Should ignore .tmp files"
        assert not rules.should_ignore(base_path / "file.txt", base_path), "Should not ignore .txt files"
        print("  ✓ Ignore rules work")
        
        # Test default rules
        default_rules = IgnoreRules.get_default_rules()
        assert ".DFM/" in default_rules, "Default rules should include .DFM/"
        assert "meshes/" in default_rules, "Default rules should include meshes/"
        print("  ✓ Default rules loaded")
        
        # Test create_default_file
        new_ignore_file = Path(tmpdir) / ".dfmignore2"
        rules2 = IgnoreRules(new_ignore_file)
        rules2.create_default_file()
        assert new_ignore_file.exists(), "Default file should be created"
        print("  ✓ Default file creation works")
    
    print("  ✓ All ignore tests passed!\n")


def test_storage():
    """Test object storage."""
    print("Testing object storage...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / ".DFM"
        storage = ObjectStorage(base_dir)
        
        # Test blob storage
        blob_data = b"Test blob data"
        blob_hash = compute_hash(blob_data)
        blob_path = storage.save_blob(blob_data, blob_hash)
        assert blob_path.exists(), "Blob file should exist"
        
        loaded_data = storage.load_blob(blob_hash)
        assert loaded_data == blob_data, "Loaded data should match"
        print("  ✓ Blob storage works")
        
        # Test tree storage
        tree_data = {"entries": [{"path": "file.txt", "type": "blob", "hash": "abc123"}]}
        tree_hash = compute_hash(json.dumps(tree_data, sort_keys=True).encode())
        tree_path = storage.save_tree(tree_data, tree_hash)
        assert tree_path.exists(), "Tree file should exist"
        
        loaded_tree = storage.load_tree(tree_hash)
        assert loaded_tree == tree_data, "Loaded tree should match"
        print("  ✓ Tree storage works")
        
        # Test commit storage
        commit_data = {
            "hash": "commit123",
            "branch": "main",
            "tree_hash": tree_hash,
            "message": "Test commit"
        }
        commit_path = storage.save_commit(commit_data, "commit123")
        assert commit_path.exists(), "Commit file should exist"
        
        loaded_commit = storage.load_commit("commit123")
        assert loaded_commit == commit_data, "Loaded commit should match"
        print("  ✓ Commit storage works")
        
        # Test mesh storage
        mesh_data = {
            "mesh_json": {"vertices": [1, 2, 3]},
            "material_json": {"color": "red"}
        }
        mesh_hash = compute_hash(json.dumps(mesh_data, sort_keys=True).encode())
        mesh_dir = storage.save_mesh(mesh_data, mesh_hash)
        assert mesh_dir.exists(), "Mesh directory should exist"
        assert (mesh_dir / "mesh.json").exists(), "mesh.json should exist"
        assert (mesh_dir / "material.json").exists(), "material.json should exist"
        
        loaded_mesh = storage.load_mesh(mesh_hash)
        assert loaded_mesh['mesh_json'] == mesh_data['mesh_json'], "Loaded mesh should match"
        print("  ✓ Mesh storage works")
    
    print("  ✓ All storage tests passed!\n")


def test_filesystem():
    """Test filesystem utilities."""
    print("Testing filesystem utilities...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        
        # Create test files
        (base_path / "file1.txt").write_text("Content 1")
        (base_path / "file2.txt").write_text("Content 2")
        (base_path / "ignored.tmp").write_text("Ignored")
        (base_path / "test_dir").mkdir()
        (base_path / "test_dir" / "file3.txt").write_text("Content 3")
        
        # Create ignore file
        ignore_file = base_path / ".dfmignore"
        with open(ignore_file, 'w') as f:
            f.write("*.tmp\n")
            f.write("test_dir/\n")
        
        rules = IgnoreRules(ignore_file)
        
        # Test scan_directory
        files = scan_directory(base_path, rules, base_path)
        file_names = [f.name for f in files]
        assert "file1.txt" in file_names, "Should include file1.txt"
        assert "file2.txt" in file_names, "Should include file2.txt"
        assert "ignored.tmp" not in file_names, "Should not include ignored.tmp"
        assert "file3.txt" not in file_names, "Should not include files in ignored directory"
        print("  ✓ scan_directory works")
        
        # Test copy_file
        src = base_path / "file1.txt"
        dst = base_path / "file1_copy.txt"
        copy_file(src, dst)
        assert dst.exists(), "Copied file should exist"
        assert dst.read_text() == src.read_text(), "Copied content should match"
        print("  ✓ copy_file works")
        
        # Test ensure_directory
        new_dir = base_path / "new_dir" / "sub_dir"
        ensure_directory(new_dir)
        assert new_dir.exists() and new_dir.is_dir(), "Directory should be created"
        print("  ✓ ensure_directory works")
    
    print("  ✓ All filesystem tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Forester Core Modules Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_hashing()
        test_database()
        test_ignore()
        test_storage()
        test_filesystem()
        
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

