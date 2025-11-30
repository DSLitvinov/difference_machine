#!/usr/bin/env python3
"""
Test script for Forester stash command.
"""

import tempfile
import shutil
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from forester.commands.init import init_repository
from forester.commands.commit import create_commit
from forester.commands.stash import create_stash, list_stashes, apply_stash, delete_stash
from forester.core.database import ForesterDB


def test_create_stash():
    """Test stash creation."""
    print("Testing create_stash...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # Initialize repository
        init_repository(project_path)

        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()

        # Create and commit file
        (working_dir / "file1.txt").write_text("Committed content")
        create_commit(project_path, "Initial commit", "Test User")

        # Modify file (uncommitted change)
        (working_dir / "file1.txt").write_text("Modified content")
        (working_dir / "file2.txt").write_text("New file")

        # Create stash
        stash_hash = create_stash(project_path, "Test stash")

        assert stash_hash is not None, "Stash should be created"
        print(f"  ✓ Stash created: {stash_hash[:16]}...")

        # Verify stash in database
        dfm_dir = project_path / ".DFM"
        with ForesterDB(dfm_dir / "forester.db") as db:
            stash_data = db.get_stash(stash_hash)
            assert stash_data is not None, "Stash should exist in database"
            assert stash_data['message'] == "Test stash", "Message should match"
            print("  ✓ Stash saved to database")

        # Restore files from last commit (simulate checkout)
        from forester.commands.checkout import checkout
        checkout(project_path, "main", force=True)

        # Now try to create stash with no changes (should return None)
        stash_hash2 = create_stash(project_path, "Empty stash")
        assert stash_hash2 is None, "Should return None when no changes"
        print("  ✓ No stash created when no changes")

    print("  ✓ All create_stash tests passed!\n")


def test_list_stashes():
    """Test listing stashes."""
    print("Testing list_stashes...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # Initialize repository
        init_repository(project_path)

        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()

        # Create and commit file
        (working_dir / "file.txt").write_text("Content")
        create_commit(project_path, "Initial commit", "Test User")

        # Create multiple stashes
        (working_dir / "file.txt").write_text("Modified 1")
        stash1 = create_stash(project_path, "Stash 1")

        (working_dir / "file.txt").write_text("Modified 2")
        stash2 = create_stash(project_path, "Stash 2")

        (working_dir / "file.txt").write_text("Modified 3")
        stash3 = create_stash(project_path, "Stash 3")

        # List stashes
        stashes = list_stashes(project_path)

        assert len(stashes) == 3, f"Should have 3 stashes, got {len(stashes)}"
        print("  ✓ All stashes listed")

        # Check order (newest first)
        assert stashes[0]['hash'] == stash3, "First should be newest"
        assert stashes[2]['hash'] == stash1, "Last should be oldest"
        print("  ✓ Stashes in correct order")

        # Check stash info
        for stash in stashes:
            assert 'hash' in stash, "Should have hash"
            assert 'timestamp' in stash, "Should have timestamp"
            assert 'message' in stash, "Should have message"
            assert 'branch' in stash, "Should have branch"
        print("  ✓ Stash info complete")

    print("  ✓ All list_stashes tests passed!\n")


def test_apply_stash():
    """Test applying stash."""
    print("Testing apply_stash...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # Initialize repository
        init_repository(project_path)

        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()

        # Create and commit file
        (working_dir / "file1.txt").write_text("Committed")
        create_commit(project_path, "Initial commit", "Test User")

        # Modify and create stash
        (working_dir / "file1.txt").write_text("Stashed content")
        (working_dir / "file2.txt").write_text("New stashed file")
        stash_hash = create_stash(project_path, "Test stash")

        # Modify files again
        (working_dir / "file1.txt").write_text("Current content")
        (working_dir / "file3.txt").write_text("Current file")

        # Apply stash
        success, error = apply_stash(project_path, stash_hash, force=True)
        assert success is True, "Stash should be applied"
        print("  ✓ Stash applied")

        # Verify files restored
        assert (working_dir / "file1.txt").read_text() == "Stashed content"
        assert (working_dir / "file2.txt").read_text() == "New stashed file"
        assert not (working_dir / "file3.txt").exists(), "Current file should be removed"
        print("  ✓ Files restored from stash")

        # Test with uncommitted changes (should auto-stash)
        (working_dir / "file1.txt").write_text("New changes")
        success, error = apply_stash(project_path, stash_hash, force=False)
        assert success is True, "Should apply even with changes (auto-stashes)"
        print("  ✓ Auto-stash before apply works")

    print("  ✓ All apply_stash tests passed!\n")


def test_delete_stash():
    """Test deleting stash."""
    print("Testing delete_stash...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # Initialize repository
        init_repository(project_path)

        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()

        # Create and commit file
        (working_dir / "file.txt").write_text("Content")
        create_commit(project_path, "Initial commit", "Test User")

        # Create stashes
        (working_dir / "file.txt").write_text("Modified 1")
        stash1 = create_stash(project_path, "Stash 1")

        (working_dir / "file.txt").write_text("Modified 2")
        stash2 = create_stash(project_path, "Stash 2")

        # Delete stash
        result = delete_stash(project_path, stash1)
        assert result is True, "Stash should be deleted"
        print("  ✓ Stash deleted")

        # Verify stash removed
        stashes = list_stashes(project_path)
        stash_hashes = [s['hash'] for s in stashes]
        assert stash1 not in stash_hashes, "Stash should be removed"
        assert stash2 in stash_hashes, "Other stash should remain"
        print("  ✓ Stash removed from list")

        # Try to delete non-existent stash (should fail)
        try:
            delete_stash(project_path, "nonexistent")
            assert False, "Should raise ValueError"
        except ValueError:
            print("  ✓ Non-existent stash deletion prevented")

    print("  ✓ All delete_stash tests passed!\n")


def test_stash_with_meshes():
    """Test stash with meshes."""
    print("Testing stash with meshes...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # Initialize repository
        init_repository(project_path)

        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()

        # Create file and commit
        (working_dir / "file.txt").write_text("Test")
        create_commit(project_path, "Initial commit", "Test User")

        # Modify file to ensure there are changes
        (working_dir / "file.txt").write_text("Modified")

        # Create meshes
        meshes_dir = working_dir / "meshes"
        meshes_dir.mkdir()

        mesh1_dir = meshes_dir / "mesh1"
        mesh1_dir.mkdir()
        mesh1_json = {"vertices": [[0, 0, 0], [1, 0, 0]]}
        (mesh1_dir / "mesh.json").write_text(json.dumps(mesh1_json))
        (mesh1_dir / "material.json").write_text(json.dumps({"color": [1, 0, 0]}))

        # Create stash
        stash_hash = create_stash(project_path, "Stash with meshes")
        assert stash_hash is not None, "Stash should be created"
        print("  ✓ Stash with meshes created")

        # Note: Meshes are stored in stash, but currently not restored on apply
        # This is a known limitation

    print("  ✓ All mesh stash tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Forester Stash Command Test Suite")
    print("=" * 60)
    print()

    try:
        test_create_stash()
        test_list_stashes()
        test_apply_stash()
        test_delete_stash()
        test_stash_with_meshes()

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

