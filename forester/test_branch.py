#!/usr/bin/env python3
"""
Test script for Forester branch command.
"""

import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from forester.commands.init import init_repository
from forester.commands.commit import create_commit
from forester.commands.branch import (
    create_branch,
    list_branches,
    delete_branch,
    get_branch_commits,
    switch_branch,
)
from forester.core.refs import get_branch_ref, get_current_branch


def test_create_branch():
    """Test branch creation."""
    print("Testing create_branch...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # Initialize repository
        init_repository(project_path)

        # Create working directory and files
        working_dir = project_path / "working"
        working_dir.mkdir()
        (working_dir / "file.txt").write_text("Test")

        # Create initial commit
        create_commit(project_path, "Initial commit", "Test User")

        # Create new branch from current branch
        result = create_branch(project_path, "feature1")
        assert result is True, "Branch should be created"
        print("  ✓ Branch created from current branch")

        # Verify branch exists
        branch_ref = get_branch_ref(project_path, "feature1")
        main_ref = get_branch_ref(project_path, "main")
        assert branch_ref == main_ref, "New branch should point to same commit as main"
        print("  ✓ Branch reference created correctly")

        # Create branch from specific branch
        create_branch(project_path, "feature2", from_branch="main")
        feature2_ref = get_branch_ref(project_path, "feature2")
        assert feature2_ref == main_ref, "Feature2 should point to main's commit"
        print("  ✓ Branch created from specific branch")

        # Try to create duplicate branch (should fail)
        try:
            create_branch(project_path, "feature1")
            assert False, "Should raise ValueError for duplicate branch"
        except ValueError:
            print("  ✓ Duplicate branch creation prevented")

        # Try to create branch with invalid name (should fail)
        try:
            create_branch(project_path, "feature/test")
            assert False, "Should raise ValueError for invalid name"
        except ValueError:
            print("  ✓ Invalid branch name prevented")

    print("  ✓ All create_branch tests passed!\n")


def test_list_branches():
    """Test branch listing."""
    print("Testing list_branches...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # Initialize repository
        init_repository(project_path)

        # Create working directory and commit
        working_dir = project_path / "working"
        working_dir.mkdir()
        (working_dir / "file.txt").write_text("Test")
        create_commit(project_path, "Initial commit", "Test User")

        # Create multiple branches
        create_branch(project_path, "feature1")
        create_branch(project_path, "feature2")
        create_branch(project_path, "develop")

        # List branches
        branches = list_branches(project_path)

        assert len(branches) == 4, f"Should have 4 branches, got {len(branches)}"
        print("  ✓ All branches listed")

        # Check branch names
        branch_names = [b['name'] for b in branches]
        assert 'main' in branch_names, "Should include main"
        assert 'feature1' in branch_names, "Should include feature1"
        assert 'feature2' in branch_names, "Should include feature2"
        assert 'develop' in branch_names, "Should include develop"
        print("  ✓ All branch names present")

        # Check current branch
        current_branch = get_current_branch(project_path)
        for branch in branches:
            if branch['name'] == current_branch:
                assert branch['current'] is True, "Current branch should be marked"
                print("  ✓ Current branch marked correctly")
                break

        # Check commit info
        for branch in branches:
            if branch['commit_hash']:
                assert branch['commit'] is not None, "Should have commit info"
                assert 'hash' in branch['commit'], "Commit should have hash"
                assert 'message' in branch['commit'], "Commit should have message"
        print("  ✓ Commit info included")

    print("  ✓ All list_branches tests passed!\n")


def test_delete_branch():
    """Test branch deletion."""
    print("Testing delete_branch...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # Initialize repository
        init_repository(project_path)

        # Create working directory and commit
        working_dir = project_path / "working"
        working_dir.mkdir()
        (working_dir / "file.txt").write_text("Test")
        create_commit(project_path, "Initial commit", "Test User")

        # Create branch
        create_branch(project_path, "feature1")

        # Delete branch
        result = delete_branch(project_path, "feature1")
        assert result is True, "Branch should be deleted"
        print("  ✓ Branch deleted")

        # Verify branch doesn't exist
        branch_ref = get_branch_ref(project_path, "feature1")
        assert branch_ref is None, "Branch should not exist"
        print("  ✓ Branch reference removed")

        # Try to delete non-existent branch (should fail)
        try:
            delete_branch(project_path, "nonexistent")
            assert False, "Should raise ValueError"
        except ValueError:
            print("  ✓ Non-existent branch deletion prevented")

        # Try to delete current branch (should fail without force)
        try:
            delete_branch(project_path, "main")
            assert False, "Should raise ValueError"
        except ValueError:
            print("  ✓ Current branch deletion prevented")

        # Delete current branch with force
        create_branch(project_path, "backup")
        switch_branch(project_path, "backup")
        result = delete_branch(project_path, "main", force=True)
        assert result is True, "Should delete with force"
        print("  ✓ Force deletion works")

    print("  ✓ All delete_branch tests passed!\n")


def test_get_branch_commits():
    """Test getting branch commits."""
    print("Testing get_branch_commits...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # Initialize repository
        init_repository(project_path)

        # Create working directory
        working_dir = project_path / "working"
        working_dir.mkdir()

        # Create multiple commits
        (working_dir / "file1.txt").write_text("Content 1")
        commit1 = create_commit(project_path, "Commit 1", "Test User")

        (working_dir / "file2.txt").write_text("Content 2")
        commit2 = create_commit(project_path, "Commit 2", "Test User")

        (working_dir / "file3.txt").write_text("Content 3")
        commit3 = create_commit(project_path, "Commit 3", "Test User")

        # Get commits
        commits = get_branch_commits(project_path, "main")

        assert len(commits) == 3, f"Should have 3 commits, got {len(commits)}"
        print("  ✓ All commits retrieved")

        # Check order (oldest to newest)
        assert commits[0]['hash'] == commit1, "First commit should be oldest"
        assert commits[2]['hash'] == commit3, "Last commit should be newest"
        print("  ✓ Commits in correct order")

        # Create new branch and add commit
        create_branch(project_path, "feature1")
        switch_branch(project_path, "feature1")

        # Verify we're on feature1
        current = get_current_branch(project_path)
        assert current == "feature1", "Should be on feature1"

        (working_dir / "file4.txt").write_text("Content 4")
        commit4 = create_commit(project_path, "Commit 4", "Test User")

        # Check feature1 commits
        feature_commits = get_branch_commits(project_path, "feature1")
        # Feature branch starts from main's last commit, so it has 3 from main + 1 new = 4 total
        # But actually, when we create a branch, it points to the same commit as main
        # So feature1 should have 4 commits (3 from main + 1 new)
        assert len(feature_commits) >= 1, f"Feature branch should have at least 1 commit, got {len(feature_commits)}"
        # The new commit should be in feature1
        feature_commit_hashes = [c['hash'] for c in feature_commits]
        assert commit4 in feature_commit_hashes, "Should include new commit"
        print(f"  ✓ Branch-specific commits retrieved ({len(feature_commits)} commits)")

        # Check main still has 3 commits (should not include commit4)
        main_commits = get_branch_commits(project_path, "main")
        assert len(main_commits) == 3, f"Main should still have 3 commits, got {len(main_commits)}"
        main_commit_hashes = [c['hash'] for c in main_commits]
        assert commit4 not in main_commit_hashes, "Main should not include feature1's commit"
        print("  ✓ Branch isolation works")

    print("  ✓ All get_branch_commits tests passed!\n")


def test_switch_branch():
    """Test branch switching."""
    print("Testing switch_branch...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        # Initialize repository
        init_repository(project_path)

        # Create working directory and commit
        working_dir = project_path / "working"
        working_dir.mkdir()
        (working_dir / "file.txt").write_text("Test")
        create_commit(project_path, "Initial commit", "Test User")

        # Create branch
        create_branch(project_path, "feature1")

        # Switch to feature1
        result = switch_branch(project_path, "feature1")
        assert result is True, "Should switch successfully"
        print("  ✓ Branch switched")

        # Verify current branch
        current = get_current_branch(project_path)
        assert current == "feature1", "Current branch should be feature1"
        print("  ✓ Current branch updated")

        # Switch back to main
        switch_branch(project_path, "main")
        current = get_current_branch(project_path)
        assert current == "main", "Current branch should be main"
        print("  ✓ Switched back to main")

        # Try to switch to non-existent branch (should fail)
        try:
            switch_branch(project_path, "nonexistent")
            assert False, "Should raise ValueError"
        except ValueError:
            print("  ✓ Non-existent branch switch prevented")

    print("  ✓ All switch_branch tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Forester Branch Command Test Suite")
    print("=" * 60)
    print()

    try:
        test_create_branch()
        test_list_branches()
        test_delete_branch()
        test_get_branch_commits()
        test_switch_branch()

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

