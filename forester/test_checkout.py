#!/usr/bin/env python3
"""
Test script for Forester checkout command.
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
from forester.commands.branch import create_branch
from forester.commands.checkout import checkout, checkout_branch, checkout_commit
from forester.core.refs import get_current_branch, get_current_head_commit


def test_checkout_branch():
    """Test checking out a branch."""
    print("Testing checkout_branch...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Initialize repository
        init_repository(project_path)
        
        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()
        
        # Create files and commit on main
        (working_dir / "file1.txt").write_text("Main content 1")
        (working_dir / "file2.txt").write_text("Main content 2")
        commit1 = create_commit(project_path, "Main commit 1", "Test User")
        
        # Create branch
        create_branch(project_path, "feature1")
        
        # Switch to feature1 and create different files
        checkout_branch(project_path, "feature1", force=True)
        (working_dir / "file1.txt").write_text("Feature content 1")
        (working_dir / "file3.txt").write_text("Feature content 3")
        commit2 = create_commit(project_path, "Feature commit 1", "Test User")
        
        # Verify we're on feature1
        current_branch = get_current_branch(project_path)
        assert current_branch == "feature1", "Should be on feature1"
        print("  ✓ Switched to feature1")
        
        # Verify files
        assert (working_dir / "file1.txt").read_text() == "Feature content 1"
        assert (working_dir / "file3.txt").exists()
        print("  ✓ Files match feature1")
        
        # Checkout back to main
        checkout_branch(project_path, "main", force=True)
        current_branch = get_current_branch(project_path)
        assert current_branch == "main", "Should be on main"
        print("  ✓ Switched back to main")
        
        # Verify files restored from main
        assert (working_dir / "file1.txt").read_text() == "Main content 1"
        assert (working_dir / "file2.txt").read_text() == "Main content 2"
        assert not (working_dir / "file3.txt").exists(), "file3 should not exist on main"
        print("  ✓ Files restored from main")
    
    print("  ✓ All checkout_branch tests passed!\n")


def test_checkout_commit():
    """Test checking out a specific commit."""
    print("Testing checkout_commit...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Initialize repository
        init_repository(project_path)
        
        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()
        
        # Create multiple commits
        (working_dir / "file1.txt").write_text("Version 1")
        commit1 = create_commit(project_path, "Commit 1", "Test User")
        
        (working_dir / "file1.txt").write_text("Version 2")
        (working_dir / "file2.txt").write_text("New file")
        commit2 = create_commit(project_path, "Commit 2", "Test User")
        
        (working_dir / "file1.txt").write_text("Version 3")
        commit3 = create_commit(project_path, "Commit 3", "Test User")
        
        # Checkout commit1
        success, error = checkout_commit(project_path, commit1, force=True)
        assert success is True, "Checkout should succeed"
        print("  ✓ Checked out commit1")
        
        # Verify files
        assert (working_dir / "file1.txt").read_text() == "Version 1"
        assert not (working_dir / "file2.txt").exists(), "file2 should not exist in commit1"
        print("  ✓ Files match commit1")
        
        # Checkout commit2
        checkout_commit(project_path, commit2, force=True)
        assert (working_dir / "file1.txt").read_text() == "Version 2"
        assert (working_dir / "file2.txt").read_text() == "New file"
        print("  ✓ Files match commit2")
        
        # Checkout commit3
        checkout_commit(project_path, commit3, force=True)
        assert (working_dir / "file1.txt").read_text() == "Version 3"
        print("  ✓ Files match commit3")
    
    print("  ✓ All checkout_commit tests passed!\n")


def test_checkout_uncommitted_changes():
    """Test checkout with uncommitted changes."""
    print("Testing checkout with uncommitted changes...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Initialize repository
        init_repository(project_path)
        
        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()
        
        # Create and commit file
        (working_dir / "file1.txt").write_text("Content 1")
        create_commit(project_path, "Initial commit", "Test User")
        
        # Create branch
        create_branch(project_path, "feature1")
        
        # Modify file (uncommitted change)
        (working_dir / "file1.txt").write_text("Modified content")
        
        # Try to checkout without force (should fail)
        success, error = checkout_branch(project_path, "feature1", force=False)
        assert success is False, "Checkout should fail"
        assert error == "uncommitted_changes", "Should return uncommitted_changes error"
        print("  ✓ Uncommitted changes detected")
        
        # Checkout with force (should succeed)
        success, error = checkout_branch(project_path, "feature1", force=True)
        assert success is True, "Checkout with force should succeed"
        print("  ✓ Force checkout works")
    
    print("  ✓ All uncommitted changes tests passed!\n")


def test_checkout_with_meshes():
    """Test checkout with meshes."""
    print("Testing checkout with meshes...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Initialize repository
        init_repository(project_path)
        
        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()
        
        # Create file
        (working_dir / "file.txt").write_text("Test")
        
        # Create meshes
        meshes_dir = working_dir / "meshes"
        meshes_dir.mkdir()
        
        mesh1_dir = meshes_dir / "mesh1"
        mesh1_dir.mkdir()
        mesh1_json = {"vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]]}
        (mesh1_dir / "mesh.json").write_text(json.dumps(mesh1_json))
        (mesh1_dir / "material.json").write_text(json.dumps({"color": [1, 0, 0]}))
        
        mesh2_dir = meshes_dir / "mesh2"
        mesh2_dir.mkdir()
        mesh2_json = {"vertices": [[0, 0, 0], [2, 0, 0], [0, 2, 0]]}
        (mesh2_dir / "mesh.json").write_text(json.dumps(mesh2_json))
        (mesh2_dir / "material.json").write_text(json.dumps({"color": [0, 1, 0]}))
        
        # Create commit
        commit1 = create_commit(project_path, "Commit with meshes", "Test User")
        
        # Create branch and commit without meshes
        create_branch(project_path, "no_meshes")
        checkout_branch(project_path, "no_meshes", force=True)
        
        # Remove meshes
        shutil.rmtree(meshes_dir)
        commit2 = create_commit(project_path, "Commit without meshes", "Test User")
        
        # Checkout back to commit1
        checkout_commit(project_path, commit1, force=True)
        
        # Verify meshes restored
        assert meshes_dir.exists(), "meshes directory should exist"
        restored_meshes = list(meshes_dir.iterdir())
        assert len(restored_meshes) >= 1, "Should have restored meshes"
        print("  ✓ Meshes restored")
        
        # Verify mesh files
        for mesh_dir in restored_meshes:
            if mesh_dir.is_dir():
                assert (mesh_dir / "mesh.json").exists(), "mesh.json should exist"
                assert (mesh_dir / "material.json").exists(), "material.json should exist"
        print("  ✓ Mesh files restored")
    
    print("  ✓ All mesh checkout tests passed!\n")


def test_checkout_clears_directory():
    """Test that checkout clears directory completely."""
    print("Testing checkout clears directory...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Initialize repository
        init_repository(project_path)
        
        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()
        
        # Create commit with files
        (working_dir / "file1.txt").write_text("Content 1")
        (working_dir / "subdir").mkdir()
        (working_dir / "subdir" / "file2.txt").write_text("Content 2")
        commit1 = create_commit(project_path, "Commit 1", "Test User")
        
        # Create branch with different files
        create_branch(project_path, "feature1")
        checkout_branch(project_path, "feature1", force=True)
        
        # Add extra files
        (working_dir / "extra.txt").write_text("Extra")
        (working_dir / "extra_dir").mkdir()
        (working_dir / "extra_dir" / "file.txt").write_text("Extra file")
        
        # Checkout back to main
        checkout_branch(project_path, "main", force=True)
        
        # Verify extra files are gone
        assert not (working_dir / "extra.txt").exists(), "Extra file should be removed"
        assert not (working_dir / "extra_dir").exists(), "Extra directory should be removed"
        print("  ✓ Extra files removed")
        
        # Verify original files restored
        assert (working_dir / "file1.txt").exists(), "Original file should exist"
        assert (working_dir / "subdir" / "file2.txt").exists(), "Original subdir file should exist"
        print("  ✓ Original files restored")
    
    print("  ✓ All directory clearing tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Forester Checkout Command Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_checkout_branch()
        test_checkout_commit()
        test_checkout_uncommitted_changes()
        test_checkout_with_meshes()
        test_checkout_clears_directory()
        
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


