#!/usr/bin/env python3
"""
Test script for Forester commit command.
"""

import tempfile
import shutil
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from forester.commands.init import init_repository
from forester.commands.commit import create_commit, has_uncommitted_changes
from forester.core.database import ForesterDB
from forester.core.refs import get_branch_ref, get_current_branch
from forester.models.commit import Commit


def test_create_commit():
    """Test commit creation."""
    print("Testing create_commit...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Initialize repository
        init_repository(project_path)
        
        # Create working directory structure
        working_dir = project_path / "working"
        working_dir.mkdir()
        
        # Create test files
        (working_dir / "file1.txt").write_text("Content 1")
        (working_dir / "file2.txt").write_text("Content 2")
        (working_dir / "subdir").mkdir()
        (working_dir / "subdir" / "file3.txt").write_text("Content 3")
        
        # Create first commit
        commit_hash1 = create_commit(
            repo_path=project_path,
            message="Initial commit",
            author="Test User"
        )
        
        assert commit_hash1 is not None, "Commit should be created"
        print(f"  ✓ First commit created: {commit_hash1[:16]}...")
        
        # Verify commit in database
        dfm_dir = project_path / ".DFM"
        from forester.core.storage import ObjectStorage
        storage = ObjectStorage(dfm_dir)
        
        with ForesterDB(dfm_dir / "forester.db") as db:
            commit = Commit.from_storage(commit_hash1, db, storage)
            assert commit is not None, "Commit should exist in database"
            assert commit.message == "Initial commit", "Message should match"
            assert commit.author == "Test User", "Author should match"
            assert commit.parent_hash is None, "First commit should have no parent"
            print("  ✓ Commit saved to database")
        
        # Verify branch reference updated
        branch_ref = get_branch_ref(project_path, "main")
        assert branch_ref == commit_hash1, "Branch ref should point to commit"
        print("  ✓ Branch reference updated")
        
        # Modify files
        (working_dir / "file1.txt").write_text("Modified content 1")
        (working_dir / "new_file.txt").write_text("New content")
        
        # Create second commit
        commit_hash2 = create_commit(
            repo_path=project_path,
            message="Second commit",
            author="Test User"
        )
        
        assert commit_hash2 is not None, "Second commit should be created"
        assert commit_hash2 != commit_hash1, "Commits should be different"
        print(f"  ✓ Second commit created: {commit_hash2[:16]}...")
        
        # Verify parent relationship
        from forester.core.storage import ObjectStorage
        storage = ObjectStorage(dfm_dir)
        
        with ForesterDB(dfm_dir / "forester.db") as db:
            commit2 = Commit.from_storage(commit_hash2, db, storage)
            assert commit2.parent_hash == commit_hash1, "Parent should be first commit"
            print("  ✓ Parent relationship correct")
        
        # Verify branch reference updated
        branch_ref = get_branch_ref(project_path, "main")
        assert branch_ref == commit_hash2, "Branch ref should point to new commit"
        print("  ✓ Branch reference updated")
    
    print("  ✓ All commit creation tests passed!\n")


def test_commit_with_meshes():
    """Test commit with meshes."""
    print("Testing commit with meshes...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Initialize repository
        init_repository(project_path)
        
        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()
        
        # Create test file
        (working_dir / "file.txt").write_text("Test content")
        
        # Create meshes directory
        meshes_dir = working_dir / "meshes"
        meshes_dir.mkdir()
        
        # Create mesh 1
        mesh1_dir = meshes_dir / "mesh1"
        mesh1_dir.mkdir()
        mesh1_json = {
            "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            "faces": [[0, 1, 2]]
        }
        (mesh1_dir / "mesh.json").write_text(json.dumps(mesh1_json))
        (mesh1_dir / "material.json").write_text(json.dumps({"color": [1, 0, 0]}))
        
        # Create mesh 2
        mesh2_dir = meshes_dir / "mesh2"
        mesh2_dir.mkdir()
        mesh2_json = {
            "vertices": [[0, 0, 0], [2, 0, 0], [0, 2, 0]],
            "faces": [[0, 1, 2]]
        }
        (mesh2_dir / "mesh.json").write_text(json.dumps(mesh2_json))
        (mesh2_dir / "material.json").write_text(json.dumps({"color": [0, 1, 0]}))
        
        # Create commit
        commit_hash = create_commit(
            repo_path=project_path,
            message="Commit with meshes",
            author="Test User"
        )
        
        assert commit_hash is not None, "Commit should be created"
        print(f"  ✓ Commit with meshes created: {commit_hash[:16]}...")
        
        # Verify meshes in commit
        dfm_dir = project_path / ".DFM"
        with ForesterDB(dfm_dir / "forester.db") as db:
            from forester.core.storage import ObjectStorage
            storage = ObjectStorage(dfm_dir)
            
            commit = Commit.from_storage(commit_hash, db, storage)
            assert commit is not None, "Commit should exist"
            assert len(commit.mesh_hashes) == 2, "Should have 2 meshes"
            print("  ✓ Meshes included in commit")
    
    print("  ✓ All mesh commit tests passed!\n")


def test_no_changes():
    """Test commit with no changes."""
    print("Testing commit with no changes...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Initialize repository
        init_repository(project_path)
        
        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()
        
        # Create test file
        (working_dir / "file.txt").write_text("Test content")
        
        # Create first commit
        commit_hash1 = create_commit(
            repo_path=project_path,
            message="Initial commit",
            author="Test User"
        )
        assert commit_hash1 is not None, "First commit should be created"
        
        # Try to commit again with no changes
        commit_hash2 = create_commit(
            repo_path=project_path,
            message="No changes commit",
            author="Test User"
        )
        
        assert commit_hash2 is None, "Should return None when no changes"
        print("  ✓ No changes detected correctly")
        
        # Verify branch ref still points to first commit
        branch_ref = get_branch_ref(project_path, "main")
        assert branch_ref == commit_hash1, "Branch ref should not change"
        print("  ✓ Branch reference unchanged")
    
    print("  ✓ All no-changes tests passed!\n")


def test_has_uncommitted_changes():
    """Test has_uncommitted_changes function."""
    print("Testing has_uncommitted_changes...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Initialize repository
        init_repository(project_path)
        
        # Should return True when no commits and files exist
        working_dir = project_path / "working"
        working_dir.mkdir()
        (working_dir / "file.txt").write_text("Test")
        
        assert has_uncommitted_changes(project_path), "Should detect uncommitted changes"
        print("  ✓ Detects changes before first commit")
        
        # Create commit
        create_commit(project_path, "Initial commit", "Test User")
        
        # Should return False when no changes
        assert not has_uncommitted_changes(project_path), "Should detect no changes"
        print("  ✓ Detects no changes after commit")
        
        # Modify file
        (working_dir / "file.txt").write_text("Modified")
        
        # Should return True when changes exist
        assert has_uncommitted_changes(project_path), "Should detect changes"
        print("  ✓ Detects changes after modification")
        
        # Create commit
        create_commit(project_path, "Second commit", "Test User")
        
        # Should return False again
        assert not has_uncommitted_changes(project_path), "Should detect no changes"
        print("  ✓ Detects no changes after second commit")
    
    print("  ✓ All uncommitted changes tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Forester Commit Command Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_create_commit()
        test_commit_with_meshes()
        test_no_changes()
        test_has_uncommitted_changes()
        
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

